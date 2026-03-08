-- Create ENUM type for order status
CREATE TYPE order_status_enum AS ENUM ('pending', 'paid', 'shipped', 'cancelled', 'refunded');

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    created_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    status order_status_enum DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE TABLE order_products (
    order_id INT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity INT NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (order_id, product_id)
);

-- Indexes for filtering by timestamps
CREATE INDEX idx_orders_updated ON orders(updated_at);
CREATE INDEX idx_customers_created ON customers(created_at);
CREATE INDEX idx_products_created ON products(created_at);

-- Indexes on foreign keys for join performance
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_order_products_order_id ON order_products(order_id);
CREATE INDEX idx_order_products_product_id ON order_products(product_id);

-- Indexes for soft delete queries
CREATE INDEX idx_customers_deleted ON customers(deleted_at);
CREATE INDEX idx_products_deleted ON products(deleted_at);
CREATE INDEX idx_orders_deleted ON orders(deleted_at);