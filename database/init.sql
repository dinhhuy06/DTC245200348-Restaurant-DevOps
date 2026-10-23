CREATE TABLE dishes (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price NUMERIC(12, 2) NOT NULL CHECK (price >= 0)
);

CREATE TABLE restaurant_tables (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE orders (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    table_id INTEGER NOT NULL REFERENCES restaurant_tables(id),
    status VARCHAR(10) NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'paid')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX one_open_order_per_table
ON orders (table_id)
WHERE status = 'open';

CREATE TABLE order_items (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    dish_id INTEGER NOT NULL REFERENCES dishes(id),
    quantity INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 100),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0)
);

INSERT INTO dishes (name, price) VALUES
('Cơm rang', 45000),
('Phở bò', 50000),
('Trà đào', 25000);

INSERT INTO restaurant_tables (name) VALUES
('Bàn 01'),
('Bàn 02'),
('Bàn 03');