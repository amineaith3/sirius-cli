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


def test_validation_helpers():
    from sirius_cli.parser import _is_phone_column, _is_zip_column, _detect_enum_values

    # Test phone number detection
    assert _is_phone_column("phone_number", []) is True
    assert _is_phone_column("tel", []) is True
    assert _is_phone_column("notes", ["+1 555-0199", "555-0100", "(555) 0122"]) is True
    assert _is_phone_column("notes", ["not-a-phone", "123"]) is False

    # Test zip code detection
    assert _is_zip_column("zip_code", []) is True
    assert _is_zip_column("postal_code", []) is True
    assert _is_zip_column("address", ["90210", "10001-1234", "SW1A 1AA"]) is True
    assert _is_zip_column("address", ["long-address-street", "city"]) is False

    # Test enum detection
    assert _detect_enum_values(
        "status", "String", ["active", "inactive", "active", "active"]
    ) == ["active", "inactive"]
    assert _detect_enum_values(
        "category", "String", ["A", "B", "C", "A", "B", "C"]
    ) == ["A", "B", "C"]
    assert (
        _detect_enum_values(
            "notes",
            "String",
            [
                "unique1",
                "unique2",
                "unique3",
                "unique4",
                "unique5",
                "unique6",
                "unique7",
                "unique8",
                "unique9",
                "unique10",
                "unique11",
            ],
        )
        == []
    )  # too many
    assert _detect_enum_values("quantity", "Integer", [1, 2, 3]) == []  # wrong type
    assert _detect_enum_values("id", "String", ["1", "2", "3"]) == []  # is id


def test_parse_csv_with_validation(tmp_path):
    csv_path = tmp_path / "orders.csv"
    csv_content = """id,customer_phone,postal_code,status,notes
1,+1-555-123-4567,90210,pending,deliver in afternoon
2,555 987 6543,10001,shipped,ring bell
3,(555) 555-1234,30301,delivered,leave at door
"""
    csv_path.write_text(csv_content, encoding="utf-8")

    from sirius_cli.parser import parse_csv_files

    schemas = parse_csv_files([str(csv_path)])

    assert "orders" in schemas
    columns = schemas["orders"]

    phone_col = next(c for c in columns if c["name"] == "customer_phone")
    assert "pattern" in phone_col
    assert phone_col["placeholder"] == "e.g., +1 (555) 000-0000"

    zip_col = next(c for c in columns if c["name"] == "postal_code")
    assert "pattern" in zip_col
    assert zip_col["placeholder"] == "e.g., 90210"

    status_col = next(c for c in columns if c["name"] == "status")
    assert status_col["enum_values"] == ["delivered", "pending", "shipped"]

    notes_col = next(c for c in columns if c["name"] == "notes")
    assert "enum_values" not in notes_col
    assert "pattern" not in notes_col


def test_parse_sqlite_with_validation(tmp_path):
    import sqlite3

    db_path = tmp_path / "test_val.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            phone TEXT,
            zip TEXT,
            role TEXT
        )
    """)
    cursor.execute(
        "INSERT INTO users (phone, zip, role) VALUES ('+1-555-1234', '90210', 'admin')"
    )
    cursor.execute(
        "INSERT INTO users (phone, zip, role) VALUES ('555-6789', '10001', 'user')"
    )
    cursor.execute(
        "INSERT INTO users (phone, zip, role) VALUES ('(555) 0000', '30301', 'user')"
    )
    conn.commit()
    conn.close()

    from sirius_cli.parser import parse_sqlite_db

    schemas = parse_sqlite_db(str(db_path))

    assert "users" in schemas
    columns = schemas["users"]

    phone_col = next(c for c in columns if c["name"] == "phone")
    assert "pattern" in phone_col
    assert phone_col["placeholder"] == "e.g., +1 (555) 000-0000"

    zip_col = next(c for c in columns if c["name"] == "zip")
    assert "pattern" in zip_col
    assert zip_col["placeholder"] == "e.g., 90210"

    role_col = next(c for c in columns if c["name"] == "role")
    assert role_col["enum_values"] == ["admin", "user"]
