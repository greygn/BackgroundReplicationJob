from decimal import Decimal
import os
import time
import logging
from datetime import datetime
import sys
import psycopg2
from psycopg2.extras import DictCursor
from pymongo import MongoClient, UpdateOne

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 5000))
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", 60))

# Replication configuration mapping table_name -> SQL query
REPLICATION_TABLES = [
    (
        "customers",
        """
        SELECT id, name, email, deleted_at, created_at
        FROM customers
        WHERE created_at > %s OR deleted_at > %s
        """,
    ),
    (
        "products",
        """
        SELECT id, name, price, deleted_at, created_at
        FROM products
        WHERE created_at > %s OR deleted_at > %s
        """,
    ),
    (
        "orders",
        """
        SELECT id, customer_id, status, deleted_at, created_at, updated_at
        FROM orders
        WHERE updated_at > %s OR deleted_at > %s
        """,
    ),
    (
        "order_products",
        """
        SELECT order_id, product_id, quantity
        FROM order_products
        """,
    ),
]

# Required environment variables
REQUIRED_ENV_VARS = [
    "POSTGRES_HOST",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "MONGO_HOST",
    "MONGO_DB",
]


def validate_environment():
    """Validate all required environment variables are set."""
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)
    logger.info("Environment variables validation passed")


def get_postgres_params():
    """Extract and return PostgreSQL connection parameters."""
    return {
        "host": os.getenv("POSTGRES_HOST"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "database": os.getenv("POSTGRES_DB"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
    }


def get_mongo_uri():
    """Build MongoDB connection URI."""
    host = os.getenv("MONGO_HOST")
    port = os.getenv("MONGO_PORT", 27017)
    return f"mongodb://{host}:{port}"

def wait_for_postgres():
    """Wait for PostgreSQL to become available."""
    logger.info("Waiting for Postgres...")
    while True:
        try:
            conn = psycopg2.connect(**get_postgres_params())
            conn.close()
            logger.info("Postgres is ready.")
            break
        except psycopg2.OperationalError:
            logger.info("Postgres not ready, retrying in 10 seconds...")
            time.sleep(10)

def create_connections():
    """Create PostgreSQL and MongoDB connections."""
    pg_conn = psycopg2.connect(**get_postgres_params())
    mongo_client = MongoClient(get_mongo_uri())
    mongo_db = mongo_client[os.getenv("MONGO_DB")]
    return pg_conn, mongo_db

def last_sync(mongo_db):
    """Get the timestamp of the last synchronization."""
    state = mongo_db.sync_state.find_one({"_id": "replication"})
    if state:
        return state["time"]
    return datetime(1970, 1, 1)

def save_sync(mongo_db, timestamp):
    """Save the synchronization timestamp."""
    mongo_db.sync_state.update_one(
        {"_id": "replication"},
        {"$set": {"time": timestamp}},
        upsert=True
    )

def replicate_table_bulk(cursor, table_name, query, mongo_collection, params):
    """Replicate table data from PostgreSQL to MongoDB in batches."""
    logger.info(f"Starting replication for table {table_name}...")

    cursor.execute(query, params)
    total = 0

    while True:
        rows = cursor.fetchmany(BATCH_SIZE)
        if not rows:
            break

        ops = []
        for row in rows:
            doc = dict(row)

            # Convert Decimal to float for MongoDB compatibility
            for k, v in doc.items():
                if isinstance(v, Decimal):
                    doc[k] = float(v)

            # Use 'id' field as MongoDB _id or create composite key
            if "id" in doc:
                doc["_id"] = doc.pop("id")
            else:
                # Composite _id for tables without id field
                doc["_id"] = f"{doc['order_id']}_{doc['product_id']}"

            ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": doc}, upsert=True))
            total += 1

        if ops:
            mongo_collection.bulk_write(ops)

    logger.info(f"Replicated {total} rows for {table_name}")

def replicate(pg_conn, mongo_db):
    """Execute replication cycle for all configured tables."""
    cur = None
    try:
        cur = pg_conn.cursor(cursor_factory=DictCursor)
        sync_time = last_sync(mongo_db)
        logger.info(f"Last sync time: {sync_time}")

        for name, query in REPLICATION_TABLES:
            params = (sync_time, sync_time) if "WHERE" in query else ()
            collection = mongo_db[name]
            replicate_table_bulk(cur, name, query, collection, params)

        save_sync(mongo_db, datetime.utcnow())
        logger.info("Replication complete.")

    except Exception as e:
        logger.exception(f"Replication failed: {e}")

    finally:
        if cur:
            cur.close()


def run_worker():
    """Main worker loop running sync at regular intervals."""
    logger.info("Sync worker started")
    pg_conn, mongo_db = create_connections()

    while True:
        replicate(pg_conn, mongo_db)
        logger.info(f"Sleeping {SYNC_INTERVAL} seconds before next sync...")
        time.sleep(SYNC_INTERVAL)


if __name__ == "__main__":
    validate_environment()
    wait_for_postgres()
    run_worker()