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
    return result if result else word + 's'

def _singularize(word: str) -> str:
    """Returns the singular of a word using the inflect library."""
    result = _inflect.singular_noun(word)
    return result if result else word

def sanitize_table_name(name: str) -> str:
    """Sanitizes file path/table name to a valid SQL identifier."""
    base = os.path.splitext(os.path.basename(name))[0]
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', base).lower()
    if sanitized and sanitized[0].isdigit():
        sanitized = "_" + sanitized
    return sanitized or "table"

def sanitize_column_name(name: str) -> str:
    """Sanitizes column name to a valid SQL/python attribute name."""
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name).lower()
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
                    if len(val) >= 8 and any(char in val for char in ['-', '/', ':']):
                        return "DateTime"
                except (ValueError, TypeError):
                    pass
        return "String"

def parse_config_file(config_path: str) -> Tuple[Dict[str, List[Dict[str, Any]]], str, str]:
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
            
            col_dict = {"name": name, "type": c_type, "is_pk": is_pk}
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
            columns.insert(0, {"name": "id", "type": "Integer", "is_pk": True})
            
        schemas[san_table] = columns
        
    return schemas, project_name, theme

def parse_csv_files(csv_paths: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Parses list of CSV paths, extracts schema types and infers relationships."""
    schemas = {}
    for path in csv_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(f"CSV file not found: {path}")
        
        table_name = sanitize_table_name(path)
        try:
            df = pd.read_csv(path, nrows=100, encoding='utf-8')
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(path, nrows=100, encoding='utf-16')
            except UnicodeDecodeError:
                df = pd.read_csv(path, nrows=100, encoding='cp1252')
        
        columns = []
        has_id = False
        
        for col in df.columns:
            san_col = sanitize_column_name(col)
            col_type = map_pandas_type(df[col].dtype, df[col].dropna().head(5).tolist())
            
            if san_col == "id":
                has_id = True
                columns.append({"name": "id", "type": "Integer", "is_pk": True})
            else:
                columns.append({"name": san_col, "type": col_type, "is_pk": False})
                
        if not has_id:
            columns.insert(0, {"name": "id", "type": "Integer", "is_pk": True})
            
        schemas[table_name] = columns
        
    # Heuristic-based Relationship inference (shared by CSV and Excel parsers)
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
                columns.append({"name": "id", "type": "Integer", "is_pk": True})
            else:
                columns.append({"name": san_col, "type": col_type, "is_pk": False})

        if not has_id:
            columns.insert(0, {"name": "id", "type": "Integer", "is_pk": True})

        schemas[table_name] = columns

    # Run same FK heuristic as CSV parser
    table_names = list(schemas.keys())
    for table_name, columns in schemas.items():
        for col in columns:
            col_name = str(col["name"])
            if col_name.endswith("_id") and col_name != "id":
                prefix = col_name[:-3]
                matched_table = None
                for t in table_names:
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

    return schemas

def map_sqlite_type(sqlite_type: str) -> str:
    """Maps SQLite column type to standard schema types."""
    t = sqlite_type.upper()
    if any(x in t for x in ["INT", "INTEGER", "TINYINT", "SMALLINT", "MEDIUMINT", "BIGINT"]):
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
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
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
            is_pk = bool(info[5])
            
            col_dict = {"name": col_name, "type": col_type, "is_pk": is_pk}
            if col_name in fks:
                col_dict["foreign_key"] = fks[col_name]
                
            if col_name == "id":
                has_id = True
                col_dict["is_pk"] = True
                
            columns.append(col_dict)
            
        if not has_id:
            # Enforce PK id
            for c in columns:
                if c["is_pk"]:
                    c["is_pk"] = False
            columns.insert(0, {"name": "id", "type": "Integer", "is_pk": True})
            
        schemas[san_table] = columns
        
    conn.close()
    return schemas
