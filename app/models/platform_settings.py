from ..extensions import db


class PlatformSettings(db.Model):
    """
    A single row of platform-wide settings — currently just your own bank
    details, shown to tenants who want to upgrade their plan by transfer.
    Always uses id=1; there's only ever one row. Editable from the Admin
    panel rather than an env var, so it can change without a redeploy.
    """
    __tablename__ = "platform_settings"

    id                 = db.Column(db.Integer, primary_key=True, default=1)
    bank_name          = db.Column(db.String, nullable=True)
    account_name       = db.Column(db.String, nullable=True)
    account_number     = db.Column(db.String, nullable=True)
    routing_number     = db.Column(db.String, nullable=True)
    swift_code         = db.Column(db.String, nullable=True)

    def to_dict(self):
        return {
            "bank_name": self.bank_name,
            "account_name": self.account_name,
            "account_number": self.account_number,
            "routing_number": self.routing_number,
            "swift_code": self.swift_code,
        }

    def formatted(self):
        lines = []
        if self.bank_name:
            lines.append(f"Bank: {self.bank_name}")
        if self.account_name:
            lines.append(f"Account name: {self.account_name}")
        if self.account_number:
            lines.append(f"Account number: {self.account_number}")
        if self.routing_number:
            lines.append(f"Routing/IBAN: {self.routing_number}")
        if self.swift_code:
            lines.append(f"SWIFT/BIC: {self.swift_code}")
        return "\n".join(lines) if lines else None

    @classmethod
    def get(cls):
        """Fetches the single row, creating it (empty) if it doesn't exist yet."""
        row = cls.query.get(1)
        if not row:
            row = cls(id=1)
            db.session.add(row)
            db.session.commit()
        return row
