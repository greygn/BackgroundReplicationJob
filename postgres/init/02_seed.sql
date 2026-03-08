-- Populate customers with random names and emails
INSERT INTO customers (name, email, created_at)
SELECT
    'Customer ' || g,
    'customer' || g || '@mail.com',
    NOW() - (random() * interval '365 days')
FROM generate_series(1, 500000) g
ON CONFLICT (email) DO NOTHING;

-- Populate products with random names and prices
INSERT INTO products (name, price, created_at)
SELECT
    'Product ' || g,
    round((random() * 1000)::numeric, 2),
    NOW() - (random() * interval '365 days')
FROM generate_series(1, 500000) g;

-- Populate orders with random customer_id and status
INSERT INTO orders (customer_id, status, created_at, updated_at)
SELECT
    (1 + (random() * 499999)::int),
    (ARRAY['pending', 'paid', 'shipped', 'cancelled'])[floor(random() * 4) + 1]::order_status_enum,
    NOW() - (random() * interval '180 days'),
    NOW() - (random() * interval '180 days')
FROM generate_series(1, 1000000);

-- Populate order_products with random order_id, product_id, and quantity
INSERT INTO order_products (order_id, product_id, quantity)
WITH valid_orders AS (
    SELECT id FROM orders ORDER BY RANDOM() LIMIT 1000000
),
valid_products AS (
    SELECT id FROM products ORDER BY RANDOM() LIMIT 500000
)
SELECT
    (SELECT id FROM valid_orders ORDER BY RANDOM() LIMIT 1),
    (SELECT id FROM valid_products ORDER BY RANDOM() LIMIT 1),
    1 + (random() * 10)::int
FROM generate_series(1, 500000)
ON CONFLICT DO NOTHING;