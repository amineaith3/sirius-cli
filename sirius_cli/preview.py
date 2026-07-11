import os
import uvicorn
import webbrowser
from typing import Optional, List, Dict, Any, Type
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, create_model
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    select,
    insert,
    update,
    delete,
    event,
)
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.engine import Engine
from sqlite3 import Connection as SQLite3Connection
from sqlalchemy.exc import IntegrityError
from datetime import datetime

# Build SQLAlchemy and Pydantic types dynamically
TYPE_MAPPING = {
    "Integer": Integer,
    "String": String,
    "Float": Float,
    "Boolean": Boolean,
    "DateTime": DateTime,
}

PYDANTIC_MAPPING = {
    "Integer": int,
    "String": str,
    "Float": float,
    "Boolean": bool,
    "DateTime": datetime,
}


def run_preview(
    schemas: Dict[str, List[Dict[str, Any]]],
    port: int = 8765,
    db_path: Optional[str] = None,
    csv_paths: Optional[List[str]] = None,
    excel_paths: Optional[List[str]] = None,
):
    app = FastAPI(title="Sirius Preview API")

    @app.exception_handler(IntegrityError)
    def integrity_exception_handler(request: Request, exc: IntegrityError):
        return JSONResponse(
            status_code=400,
            content={"detail": f"Database integrity error: {str(exc.orig)}"},
        )

    # Configure database
    if db_path:
        database_url = f"sqlite:///{os.path.abspath(db_path)}"
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
    else:
        database_url = "sqlite:///:memory:"
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    @event.listens_for(Engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, SQLite3Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()

    metadata = MetaData()

    tables = {}
    pydantic_create_models = {}
    pydantic_update_models = {}

    for table_name, columns in schemas.items():
        # Build SQLAlchemy Table
        sa_columns = []
        for col in columns:
            col_name = str(col["name"])
            col_type_str = str(col.get("type", "String"))
            sa_type = TYPE_MAPPING.get(col_type_str, String)
            is_pk = bool(col.get("is_pk", False))
            fk = col.get("foreign_key")

            kwargs = {"primary_key": is_pk}
            from typing import cast

            # Use Any cast because SQLAlchemy's overloaded Column stubs struggle with Unions of types
            resolved_type = cast(Any, sa_type)

            if fk:
                sa_columns.append(
                    Column(col_name, resolved_type, ForeignKey(str(fk)), **kwargs)  # type: ignore
                )
            else:
                sa_columns.append(Column(col_name, resolved_type, **kwargs))  # type: ignore

        table = Table(table_name, metadata, *sa_columns)
        tables[table_name] = table

        # Build Pydantic Create Model
        create_fields: Dict[str, Any] = {}
        for col in columns:
            if col.get("is_pk", False):
                continue
            col_name = str(col["name"])
            py_type = PYDANTIC_MAPPING.get(str(col.get("type", "String")), str)
            create_fields[col_name] = (Optional[py_type], None)

        pydantic_create_models[table_name] = create_model(
            f"{table_name.capitalize()}Create", **create_fields
        )
        pydantic_update_models[table_name] = create_model(
            f"{table_name.capitalize()}Update", **create_fields
        )

    # Create tables in DB
    metadata.create_all(bind=engine)

    # Seed data if using in-memory DB and files provided
    if not db_path:
        import pandas as pd
        from sirius_cli.parser import sanitize_table_name, sanitize_column_name

        # Helper to seed data safely
        def _seed_df(df: pd.DataFrame, t_name: str):
            df.columns = [sanitize_column_name(c) for c in df.columns]
            valid_cols = [c.name for c in tables[t_name].columns]
            df = df[[c for c in df.columns if c in valid_cols]]
            if not df.empty:
                df.to_sql(t_name, con=engine, if_exists="append", index=False)

        if csv_paths:
            for path in csv_paths:
                t_name = sanitize_table_name(path)
                if t_name not in tables:
                    continue
                try:
                    df = pd.read_csv(path, encoding="utf-8")
                except UnicodeDecodeError:
                    try:
                        df = pd.read_csv(path, encoding="utf-16")
                    except UnicodeDecodeError:
                        df = pd.read_csv(path, encoding="cp1252")
                _seed_df(df, t_name)

        if excel_paths:
            for path in excel_paths:
                t_name = sanitize_table_name(path)
                if t_name not in tables:
                    continue
                try:
                    df = pd.read_excel(path)
                    _seed_df(df, t_name)
                except Exception as e:
                    print(f"[WARNING] Failed to seed Excel file {path}: {e}")

    # Dependency
    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Route builder
    def add_crud_routes(
        table_name: str,
        table: Table,
        pydantic_create: Type[BaseModel],
        pydantic_update: Type[BaseModel],
    ):

        @app.get(f"/api/{table_name}")
        def read_all(db: Session = Depends(get_db)):
            stmt = select(table)
            results = db.execute(stmt).mappings().all()
            return [dict(r) for r in results]

        @app.get(f"/api/{table_name}/{{item_id}}")
        def read_one(item_id: int, db: Session = Depends(get_db)):
            stmt = select(table).where(table.c.id == item_id)
            result = db.execute(stmt).mappings().first()
            if not result:
                raise HTTPException(status_code=404, detail="Item not found")
            return dict(result)

        @app.post(f"/api/{table_name}")
        def create_item(item: Any, db: Session = Depends(get_db)):
            stmt = insert(table).values(**item.model_dump(exclude_unset=True))
            from typing import cast, Any

            result = cast(Any, db.execute(stmt))
            db.commit()
            return {"id": result.inserted_primary_key[0], **item.model_dump()}

        @app.put(f"/api/{table_name}/{{item_id}}")
        def update_item(item_id: int, item: Any, db: Session = Depends(get_db)):
            update_data = item.model_dump(exclude_unset=True)
            if not update_data:
                return {"message": "No data provided"}
            stmt = update(table).where(table.c.id == item_id).values(**update_data)
            from typing import cast, Any

            result = cast(Any, db.execute(stmt))
            db.commit()
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Item not found")
            return {"id": item_id, **update_data}

        @app.delete(f"/api/{table_name}/{{item_id}}")
        def delete_item(item_id: int, db: Session = Depends(get_db)):
            stmt = delete(table).where(table.c.id == item_id)
            from typing import cast, Any

            result = cast(Any, db.execute(stmt))
            db.commit()
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Item not found")
            return {"detail": "Item deleted"}

    for t_name, t_obj in tables.items():
        add_crud_routes(
            t_name,
            t_obj,
            pydantic_create_models[t_name],
            pydantic_update_models[t_name],
        )

    @app.get("/api/schema")
    def get_schema():
        return schemas

    @app.get("/")
    def serve_ui():
        # Load the HTML file from templates
        template_path = os.path.join(
            os.path.dirname(__file__), "templates", "preview_ui.html"
        )
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)

    print(f"\n[SIRIUS PREVIEW] Starting API and UI at http://localhost:{port}")
    print(f"[SIRIUS PREVIEW] Database: {db_path if db_path else 'In-Memory Ephemeral'}")

    # Open browser automatically
    webbrowser.open(f"http://localhost:{port}")

    # Start server
    uvicorn.run(app, host="127.0.0.1", port=port)
