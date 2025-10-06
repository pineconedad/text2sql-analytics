-- Categories
CREATE TABLE IF NOT EXISTS categories (
  category_id   INTEGER PRIMARY KEY,
  category_name VARCHAR(100) NOT NULL,
  description   TEXT
);

-- Customers
CREATE TABLE IF NOT EXISTS customers (
  customer_id   VARCHAR(20) PRIMARY KEY,
  company_name  VARCHAR(100) NOT NULL,
  contact_name  VARCHAR(100),
  contact_title VARCHAR(100),
  city          VARCHAR(100),
  country       VARCHAR(100)
);

-- Employees (self-referencing manager)
CREATE TABLE IF NOT EXISTS employees (
  employee_id   INTEGER PRIMARY KEY,
  employee_name VARCHAR(100) NOT NULL,
  title         VARCHAR(100),
  city          VARCHAR(100),
  country       VARCHAR(100),
  reports_to    INTEGER,
  CONSTRAINT fk_employee_manager
    FOREIGN KEY (reports_to) REFERENCES employees(employee_id)
    ON UPDATE CASCADE ON DELETE SET NULL
);

-- Shippers
CREATE TABLE IF NOT EXISTS shippers (
  shipper_id   INTEGER PRIMARY KEY,
  company_name VARCHAR(100) NOT NULL
);

-- Products
CREATE TABLE IF NOT EXISTS products (
  product_id        INTEGER PRIMARY KEY,
  product_name      VARCHAR(100) NOT NULL,
  quantity_per_unit VARCHAR(50),
  unit_price        NUMERIC(12,2) DEFAULT 0 NOT NULL,
  discontinued      BOOLEAN DEFAULT FALSE NOT NULL,
  category_id       INTEGER REFERENCES categories(category_id)
    ON UPDATE CASCADE ON DELETE SET NULL
);

-- Orders
CREATE TABLE IF NOT EXISTS orders (
  order_id      INTEGER PRIMARY KEY,
  customer_id   VARCHAR(20) REFERENCES customers(customer_id)
                  ON UPDATE CASCADE ON DELETE SET NULL,
  employee_id   INTEGER REFERENCES employees(employee_id)
                  ON UPDATE CASCADE ON DELETE SET NULL,
  order_date    DATE,
  required_date DATE,
  shipped_date  DATE,
  shipper_id    INTEGER REFERENCES shippers(shipper_id)
                  ON UPDATE CASCADE ON DELETE SET NULL,
  freight       NUMERIC(12,2) DEFAULT 0 NOT NULL
);

-- Order Details (line items)
CREATE TABLE IF NOT EXISTS order_details (
  order_id   INTEGER REFERENCES orders(order_id)
               ON UPDATE CASCADE ON DELETE CASCADE,
  product_id INTEGER REFERENCES products(product_id)
               ON UPDATE CASCADE ON DELETE RESTRICT,
  unit_price NUMERIC(12,2) NOT NULL,
  quantity   INTEGER NOT NULL CHECK (quantity > 0),
  discount   NUMERIC(4,2) NOT NULL DEFAULT 0 CHECK (discount >= 0 AND discount <= 1),
  PRIMARY KEY (order_id, product_id)
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_employee_id ON orders(employee_id);
CREATE INDEX IF NOT EXISTS idx_orders_shipper_id  ON orders(shipper_id);
CREATE INDEX IF NOT EXISTS idx_order_details_prod ON order_details(product_id);
