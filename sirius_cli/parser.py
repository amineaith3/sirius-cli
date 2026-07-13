import os
import re
import sqlite3
import json
import pandas as pd
import inflect
from typing import List, Dict, Any, Tuple

_inflect = inflect.engine()


def _pluralize(word: str) -> str:
    """Returns the plural of a word using the inflect library."""
    result = _inflect.plural(word)
    return result if result else word + "s"


def _singularize(word: str) -> str:
    """Returns the singular of a word using the inflect library."""
    result = _inflect.singular_noun(word)
    return result if result else word


def _is_phone_column(name: str, sample_values: List[Any]) -> bool:
    """Detects if a column is likely a phone number based on name or value patterns."""
    n = name.lower()
    if any(x in n for x in ["phone", "mobile", "tel", "telephone"]):
        return True
    phone_pat = re.compile(r"^\+?[\d\s\-\(\)\.]{7,20}$")
    vals = [v for v in sample_values if v is not None and str(v).strip() != ""]
    if not vals:
        return False
    # Require at least one digit or a + sign to avoid matching plain words
    has_digit_or_plus = any(
        any(char.isdigit() or char == "+" for char in str(v)) for v in vals
    )
    if not has_digit_or_plus:
        return False
    return all(
        isinstance(v, (str, int)) and phone_pat.match(str(v).strip()) for v in vals
    )


def _is_zip_column(name: str, sample_values: List[Any]) -> bool:
    """Detects if a column is likely a zip/postal code based on name or value patterns."""
    n = name.lower()
    if any(x in n for x in ["zip", "postal", "postcode"]):
        return True
    zip_pat = re.compile(r"^(\d{5}(-\d{4})?|[a-zA-Z0-9\s\-]{3,10})$")
    vals = [v for v in sample_values if v is not None and str(v).strip() != ""]
    if not vals:
        return False
    # Ensure there is at least one digit in the values to avoid matching plain words
    has_digit = any(any(char.isdigit() for char in str(v)) for v in vals)
    if not has_digit:
        return False
    return all(
        isinstance(v, (str, int)) and zip_pat.match(str(v).strip()) for v in vals
    )


def _detect_enum_values(
    name: str, col_type: str, sample_values: List[Any]
) -> List[str]:
    """Detects if a column represents a low-cardinality enum and returns its values."""
    if col_type != "String":
        return []
    n = name.lower()
    if (
        n in ["id", "email", "name", "notes", "comment", "description", "desc"]
        or n.endswith("_id")
        or any(
            x in n
            for x in [
                "phone",
                "mobile",
                "tel",
                "telephone",
                "zip",
                "postal",
                "postcode",
            ]
        )
    ):
        return []
    vals = [
        str(v).strip() for v in sample_values if v is not None and str(v).strip() != ""
    ]
    if len(vals) < 3:
        return []
    unique_vals = set(vals)
    if len(unique_vals) < 2 or len(unique_vals) > 10:
        return []
    # If all values are unique and we have few rows, it's likely just text
    if len(unique_vals) == len(vals) and len(vals) < 8:
        enum_names = [
            "status",
            "role",
            "type",
            "category",
            "stage",
            "gender",
            "priority",
            "rating",
            "size",
            "color",
            "level",
        ]
        if not any(x in n for x in enum_names):
            return []
    # Enforce a maximum length for enum values (most enums are short words)
    if any(len(v) > 20 for v in unique_vals):
        return []
    return sorted(list(unique_vals))


def sanitize_table_name(name: str) -> str:
    """Sanitizes file path/table name to a valid SQL identifier."""
    base = os.path.splitext(os.path.basename(name))[0]
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", base).lower()
    if sanitized and sanitized[0].isdigit():
        sanitized = "_" + sanitized
    return sanitized or "table"


def sanitize_column_name(name: str) -> str:
    """Sanitizes column name to a valid SQL/python attribute name."""
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()
    if sanitized and sanitized[0].isdigit():
        sanitized = "_" + sanitized
    return sanitized or "column"


def map_pandas_type(dtype: Any, sample_values: List[Any]) -> str:
    """Maps Pandas dtype to standard string types: Integer, Float, Boolean, DateTime, String."""
    if pd.api.types.is_integer_dtype(dtype):
        return "Integer"
    elif pd.api.types.is_float_dtype(dtype):
        return "Float"
    elif pd.api.types.is_bool_dtype(dtype):
        return "Boolean"
    elif pd.api.types.is_datetime64_any_dtype(dtype):
        return "DateTime"
    else:
        # Check string samples to see if they look like ISO dates or timestamps
        for val in sample_values:
            if isinstance(val, str):
                try:
                    pd.to_datetime(val)
                    if len(val) >= 8 and any(char in val for char in ["-", "/", ":"]):
                        return "DateTime"
                except (ValueError, TypeError):
                    pass
        return "String"


def parse_config_file(
    config_path: str,
) -> Tuple[Dict[str, List[Dict[str, Any]]], str, str]:
    """Loads entities and schemas directly from a JSON configuration file."""
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    project_name = config.get("project_name", "generated_project")
    theme = config.get("theme", "blue")
    entities = config.get("entities", {})

    schemas = {}
    for table_name, table_info in entities.items():
        san_table = sanitize_table_name(table_name)
        columns = []
        has_id = False

        for col in table_info.get("columns", []):
            name = sanitize_column_name(col.get("name"))
            c_type = col.get("type", "String")
            is_pk = col.get("is_pk", False)
            fk = col.get("foreign_key")
            is_required = col.get("is_required", False)

            col_dict: Dict[str, Any] = {
                "name": name,
                "type": c_type,
                "is_pk": is_pk,
                "is_required": is_required,
            }
            if "min_val" in col:
                col_dict["min_val"] = col["min_val"]
            if "max_val" in col:
                col_dict["max_val"] = col["max_val"]
            if "pattern" in col:
                col_dict["pattern"] = col["pattern"]
            if "placeholder" in col:
                col_dict["placeholder"] = col["placeholder"]
            if "enum_values" in col:
                col_dict["enum_values"] = col["enum_values"]

            if fk:
                col_dict["foreign_key"] = fk

            if name == "id":
                has_id = True
                col_dict["is_pk"] = True

            columns.append(col_dict)

        if not has_id:
            # Enforce an autoincrementing primary key
            for c in columns:
                if c["is_pk"]:
                    c["is_pk"] = False
            columns.insert(
                0, {"name": "id", "type": "Integer", "is_pk": True, "is_required": True}
            )

        schemas[san_table] = columns

    return schemas, project_name, theme


def _infer_relationships(schemas: Dict[str, List[Dict[str, Any]]]) -> None:
    """Heuristic-based Relationship inference to link foreign keys."""
    table_names = list(schemas.keys())
    for table_name, columns in schemas.items():
        for col in columns:
            col_name = str(col["name"])
            if col_name.endswith("_id") and col_name != "id":
                prefix = col_name[:-3]  # strip '_id'
                matched_table = None
                for t in table_names:
                    # Try exact match, then common plural/singular variants
                    candidates = {
                        prefix,
                        _pluralize(prefix),
                        _singularize(prefix),
                        prefix + "s",
                        prefix[:-1] if prefix.endswith("s") else prefix,
                    }
                    if t in candidates:
                        matched_table = t
                        break
                if matched_table:
                    col["foreign_key"] = f"{matched_table}.id"


def parse_csv_files(csv_paths: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Parses list of CSV paths, extracts schema types and infers relationships."""
    schemas = {}
    for path in csv_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(f"CSV file not found: {path}")

        table_name = sanitize_table_name(path)
        try:
            df = pd.read_csv(path, nrows=100, encoding="utf-8")
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(path, nrows=100, encoding="utf-16")
            except UnicodeDecodeError:
                df = pd.read_csv(path, nrows=100, encoding="cp1252")

        columns = []
        has_id = False

        for col in df.columns:
            san_col = sanitize_column_name(col)
            col_type = map_pandas_type(df[col].dtype, df[col].dropna().head(5).tolist())

            if san_col == "id":
                has_id = True
                columns.append(
                    {
                        "name": "id",
                        "type": "Integer",
                        "is_pk": True,
                        "is_required": True,
                    }
                )
            else:
                col_dict: Dict[str, Any] = {
                    "name": san_col,
                    "type": col_type,
                    "is_pk": False,
                }
                col_dict["is_required"] = not df[col].isnull().any()
                if col_type in ("Integer", "Float"):
                    min_val = df[col].min()
                    max_val = df[col].max()
                    if pd.notna(min_val):
                        col_dict["min_val"] = (
                            float(min_val) if col_type == "Float" else int(min_val)
                        )
                    if pd.notna(max_val):
                        col_dict["max_val"] = (
                            float(max_val) if col_type == "Float" else int(max_val)
                        )
                columns.append(col_dict)
                samples = df[col].dropna().tolist()
                if _is_phone_column(san_col, samples):
                    col_dict["pattern"] = r"\+?[0-9\s\-()]{7,20}"
                    col_dict["placeholder"] = "e.g., +1 (555) 000-0000"
                elif _is_zip_column(san_col, samples):
                    col_dict["pattern"] = r"[a-zA-Z0-9\s\-]{3,10}"
                    col_dict["placeholder"] = "e.g., 90210"
                else:
                    enum_vals = _detect_enum_values(san_col, col_type, samples)
                    if enum_vals:
                        col_dict["enum_values"] = enum_vals

        if not has_id:
            columns.insert(
                0, {"name": "id", "type": "Integer", "is_pk": True, "is_required": True}
            )

        schemas[table_name] = columns

    _infer_relationships(schemas)

    return schemas


def parse_excel_files(excel_paths: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Parses list of Excel (.xlsx/.xls) paths, extracts schema types and infers relationships."""
    schemas = {}
    for path in excel_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Excel file not found: {path}")

        table_name = sanitize_table_name(path)
        df = pd.read_excel(path, nrows=100)

        columns = []
        has_id = False

        for col in df.columns:
            san_col = sanitize_column_name(col)
            col_type = map_pandas_type(df[col].dtype, df[col].dropna().head(5).tolist())

            if san_col == "id":
                has_id = True
                columns.append(
                    {
                        "name": "id",
                        "type": "Integer",
                        "is_pk": True,
                        "is_required": True,
                    }
                )
            else:
                col_dict = {"name": san_col, "type": col_type, "is_pk": False}
                col_dict["is_required"] = not df[col].isnull().any()
                if col_type in ("Integer", "Float"):
                    min_val = df[col].min()
                    max_val = df[col].max()
                    if pd.notna(min_val):
                        col_dict["min_val"] = (
                            # pyrefly: ignore [bad-assignment]
                            float(min_val)
                            if col_type == "Float"
                            else int(min_val)
                        )
                    if pd.notna(max_val):
                        col_dict["max_val"] = (
                            # pyrefly: ignore [bad-assignment]
                            float(max_val)
                            if col_type == "Float"
                            else int(max_val)
                        )
                columns.append(col_dict)
                samples = df[col].dropna().tolist()
                if _is_phone_column(san_col, samples):
                    col_dict["pattern"] = r"\+?[0-9\s\-()]{7,20}"
                    col_dict["placeholder"] = "e.g., +1 (555) 000-0000"
                elif _is_zip_column(san_col, samples):
                    col_dict["pattern"] = r"[a-zA-Z0-9\s\-]{3,10}"
                    col_dict["placeholder"] = "e.g., 90210"
                else:
                    enum_vals = _detect_enum_values(san_col, col_type, samples)
                    if enum_vals:
                        col_dict["enum_values"] = enum_vals

        if not has_id:
            columns.insert(
                0, {"name": "id", "type": "Integer", "is_pk": True, "is_required": True}
            )

        schemas[table_name] = columns

    _infer_relationships(schemas)

    return schemas


def map_sqlite_type(sqlite_type: str) -> str:
    """Maps SQLite column type to standard schema types."""
    t = sqlite_type.upper()
    if any(
        x in t for x in ["INT", "INTEGER", "TINYINT", "SMALLINT", "MEDIUMINT", "BIGINT"]
    ):
        return "Integer"
    elif any(x in t for x in ["REAL", "DOUBLE", "FLOAT"]):
        return "Float"
    elif any(x in t for x in ["BOOL", "BOOLEAN"]):
        return "Boolean"
    elif any(x in t for x in ["DATE", "DATETIME", "TIMESTAMP"]):
        return "DateTime"
    else:
        return "String"


def parse_sqlite_db(db_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """Parses SQLite database extracting user tables and foreign key constraints."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"SQLite database file not found: {db_path}")

    schemas = {}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query user tables
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    )
    tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        san_table = sanitize_table_name(table)

        # Query SQLite foreign key relationships for the table
        # row structure: (id, seq, table, from, to, on_update, on_delete, match)
        cursor.execute(f"PRAGMA foreign_key_list({table});")
        fks = {}
        for row in cursor.fetchall():
            local_col = sanitize_column_name(row[3])
            ref_table = sanitize_table_name(row[2])
            ref_col = sanitize_column_name(row[4])
            fks[local_col] = f"{ref_table}.{ref_col}"

        cursor.execute(f"PRAGMA table_info({table});")
        columns_info = cursor.fetchall()

        columns = []
        has_id = False

        for info in columns_info:
            col_name = sanitize_column_name(info[1])
            col_type = map_sqlite_type(info[2])
            is_required = bool(info[3])
            is_pk = bool(info[5])

            col_dict: Dict[str, Any] = {
                "name": col_name,
                "type": col_type,
                "is_pk": is_pk,
                "is_required": is_required,
            }
            if col_name in fks:
                col_dict["foreign_key"] = fks[col_name]

            if col_name == "id":
                has_id = True
                col_dict["is_pk"] = True

            if not is_pk:
                samples = []
                try:
                    cursor2 = conn.cursor()
                    cursor2.execute(
                        f'SELECT "{info[1]}" FROM "{table}" WHERE "{info[1]}" IS NOT NULL LIMIT 50;'
                    )
                    samples = [r[0] for r in cursor2.fetchall()]
                    cursor2.close()
                except Exception:
                    pass

                if _is_phone_column(col_name, samples):
                    col_dict["pattern"] = r"\+?[0-9\s\-()]{7,20}"
                    col_dict["placeholder"] = "e.g., +1 (555) 000-0000"
                elif _is_zip_column(col_name, samples):
                    col_dict["pattern"] = r"[a-zA-Z0-9\s\-]{3,10}"
                    col_dict["placeholder"] = "e.g., 90210"
                else:
                    enum_vals = _detect_enum_values(col_name, col_type, samples)
                    if enum_vals:
                        col_dict["enum_values"] = enum_vals

            columns.append(col_dict)

        if not has_id:
            # Enforce PK id
            for c in columns:
                if c["is_pk"]:
                    c["is_pk"] = False
            columns.insert(
                0, {"name": "id", "type": "Integer", "is_pk": True, "is_required": True}
            )

        schemas[san_table] = columns

    conn.close()
    return schemas
