import os
import sqlite3
import tempfile
import pytest
from pathlib import Path

@pytest.fixture
def tmp_project_dir(tmp_path):
    """Provides a temporary directory path to scaffold projects into."""
    return str(tmp_path)

@pytest.fixture
def sample_csv_file(tmp_path):
    """Creates a temporary CSV file with sample user data."""
    csv_path = tmp_path / "users.csv"
    csv_content = """id,name,email,is_active,created_at
1,Alice,alice@example.com,true,2023-01-01 10:00:00
2,Bob,bob@example.com,false,2023-01-02 11:30:00
3,Charlie,charlie@example.com,true,2023-01-03 14:15:00
"""
    csv_path.write_text(csv_content, encoding="utf-8")
    return str(csv_path)

@pytest.fixture
def sample_sqlite_db(tmp_path):
    """Creates a temporary SQLite database with a sample schema and data."""
    db_path = tmp_path / "sample.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create products table
    cursor.execute('''
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL,
            in_stock INTEGER
        )
    ''')
    
    # Create orders table with foreign key
    cursor.execute('''
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            order_ref TEXT NOT NULL,
            product_id INTEGER,
            quantity INTEGER,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    # Insert mock data
    cursor.execute("INSERT INTO products (name, price, in_stock) VALUES ('Laptop', 1200.50, 1)")
    cursor.execute("INSERT INTO orders (order_ref, product_id, quantity) VALUES ('ORD-001', 1, 2)")
    
    conn.commit()
    conn.close()
    
    return str(db_path)
