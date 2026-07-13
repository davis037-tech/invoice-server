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
    "paid_at": "TIMESTAMP",
    "last_reminder_sent_at": "TIMESTAMP",
}

NEW_TENANT_COLUMNS = {
    "invoice_limit_override": "INTEGER",
}

NEW_USER_COLUMNS = {
    "is_superadmin": "BOOLEAN DEFAULT FALSE NOT NULL",
}

NEW_SETTINGS_COLUMNS = {
    "bank_name": "VARCHAR",
    "account_name": "VARCHAR",
    "account_number": "VARCHAR",
    "routing_number": "VARCHAR",
    "swift_code": "VARCHAR",
    "payment_notes": "TEXT",
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


def ensure_settings_columns(app, db):
    with app.app_context():
        _add_missing_columns(app, db, "settings", NEW_SETTINGS_COLUMNS)


def ensure_plan_limits_seeded(app, db):
    """
    Creates the plan_limits table if it doesn't exist yet (it's a brand
    new model, so plain db.create_all() handles new tables — this only
    needs to run once) and seeds it with default weekly quotas so the
    app has sensible values before an admin ever visits the Admin panel.
    """
    from .models import PlanLimit

    with app.app_context():
        try:
            db.create_all()  # only creates tables that don't exist yet — safe no-op otherwise
            defaults = {"FREE": 5, "PRO": 25, "TEAM": 100}
            existing = {row.plan for row in PlanLimit.query.all()}
            for plan, limit in defaults.items():
                if plan not in existing:
                    db.session.add(PlanLimit(plan=plan, weekly_limit=limit))
            db.session.commit()
        except Exception as e:
            app.logger.error(f"ensure_plan_limits_seeded failed: {e}")
