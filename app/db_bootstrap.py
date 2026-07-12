"""
Lightweight schema bootstrap for environments without a proper Flask-Migrate
setup yet. On startup, checks whether newer columns exist on the `invoices`
table and adds any that are missing via a plain ALTER TABLE. This avoids
needing shell access to run migration commands manually.

Safe to leave running indefinitely: once a column exists, it's a no-op.
For a growing schema, replacing this with real Flask-Migrate migrations is
recommended, but this covers the immediate need without extra deploy steps.
"""
from sqlalchemy import inspect, text


NEW_INVOICE_COLUMNS = {
    "payment_proof_note": "TEXT",
    "payment_proof_image": "TEXT",
    "payment_proof_submitted_at": "TIMESTAMP",
}

NEW_TENANT_COLUMNS = {
    "invoice_limit_override": "INTEGER",
}

NEW_USER_COLUMNS = {
    "is_superadmin": "BOOLEAN DEFAULT FALSE NOT NULL",
}


def _add_missing_columns(app, db, table_name, new_columns):
    try:
        inspector = inspect(db.engine)
        if table_name not in inspector.get_table_names():
            return
        existing = {c["name"] for c in inspector.get_columns(table_name)}
        missing = {col: coltype for col, coltype in new_columns.items() if col not in existing}
        if not missing:
            return
        with db.engine.connect() as conn:
            for col, coltype in missing.items():
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col} {coltype}"))
            conn.commit()
        app.logger.info(f"Added missing {table_name} columns: {list(missing.keys())}")
    except Exception as e:
        app.logger.error(f"_add_missing_columns({table_name}) failed: {e}")


def ensure_invoice_columns(app, db):
    with app.app_context():
        _add_missing_columns(app, db, "invoices", NEW_INVOICE_COLUMNS)


def ensure_tenant_and_user_columns(app, db):
    with app.app_context():
        _add_missing_columns(app, db, "tenants", NEW_TENANT_COLUMNS)
        _add_missing_columns(app, db, "users", NEW_USER_COLUMNS)
