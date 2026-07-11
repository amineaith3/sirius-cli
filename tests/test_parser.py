from sirius_cli.parser import (
    sanitize_table_name,
    sanitize_column_name,
    _pluralize,
    _singularize,
    parse_csv_files,
    parse_sqlite_db,
)


def test_sanitize_table_name():
    assert sanitize_table_name("User-Data 123.csv") == "user_data_123"
    assert sanitize_table_name("123table") == "_123table"
    assert sanitize_table_name("My Table!") == "my_table_"


def test_sanitize_column_name():
    assert sanitize_column_name("First Name") == "first_name"
    assert sanitize_column_name("1st_place") == "_1st_place"
    assert sanitize_column_name("email@address") == "email_address"


def test_pluralize_singularize():
    assert _pluralize("company") == "companies"
    assert _pluralize("user") == "users"

    assert _singularize("companies") == "company"
    assert _singularize("users") == "user"


def test_parse_csv_files(sample_csv_file):
    schemas = parse_csv_files([sample_csv_file])

    assert "users" in schemas
    columns = schemas["users"]

    # Check if id became pk
    id_col = next(c for c in columns if c["name"] == "id")
    assert id_col["is_pk"] is True
    assert id_col["type"] == "Integer"
    assert id_col.get("is_required") is True

    # Check string
    name_col = next(c for c in columns if c["name"] == "name")
    assert name_col["type"] == "String"
    assert name_col.get("is_required") is True

    # Check boolean mapping (from true/false strings)
    is_active_col = next(c for c in columns if c["name"] == "is_active")
    assert is_active_col["type"] == "Boolean"


def test_parse_sqlite_db(sample_sqlite_db):
    schemas = parse_sqlite_db(sample_sqlite_db)

    assert "products" in schemas
    assert "orders" in schemas

    # Products table validation
    products = schemas["products"]
    assert any(c["name"] == "id" and c["is_pk"] is True for c in products)
    assert any(c["name"] == "name" and c.get("is_required") is True for c in products)
    assert any(
        c["name"] == "price" and c["type"] == "Float" and c.get("is_required") is False
        for c in products
    )

    # Orders table foreign key validation
    orders = schemas["orders"]
    product_id_col = next(c for c in orders if c["name"] == "product_id")
    assert product_id_col["foreign_key"] == "products.id"
