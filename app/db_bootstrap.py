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


def ensure_invoice_columns(app, db):
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            if "invoices" not in inspector.get_table_names():
                # Fresh database — nothing to migrate, models handle it.
                return

            existing = {c["name"] for c in inspector.get_columns("invoices")}
            missing = {col: coltype for col, coltype in NEW_INVOICE_COLUMNS.items() if col not in existing}
            if not missing:
                return

            with db.engine.connect() as conn:
                for col, coltype in missing.items():
                    conn.execute(text(f"ALTER TABLE invoices ADD COLUMN {col} {coltype}"))
                conn.commit()
            app.logger.info(f"Added missing invoice columns: {list(missing.keys())}")
        except Exception as e:
            # Never let a schema-check failure take the whole app down.
            app.logger.error(f"ensure_invoice_columns failed: {e}")
