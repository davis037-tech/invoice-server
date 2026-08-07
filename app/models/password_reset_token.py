import uuid
import secrets
from datetime import datetime, timedelta
from ..extensions import db


class PasswordResetToken(db.Model):
    """
    A one-time token emailed to a user who requests a password reset.
    Expires after 1 hour and is marked used_at once redeemed, so it
    can't be replayed even within that window.
    """
    __tablename__ = "password_reset_tokens"

    id          = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id     = db.Column(db.String, db.ForeignKey("users.id"), nullable=False)
    # 16 random bytes = 128 bits of entropy (same strength as a UUID) —
    # shorter than the original 32 bytes, but still far too many
    # combinations to brute-force. This token grants account takeover if
    # guessed, so don't shorten further than this without good reason.
    token       = db.Column(db.String, unique=True, nullable=False, default=lambda: secrets.token_urlsafe(16))
    created_at  = db.Column(db.DateTime, server_default=db.func.now())
    expires_at  = db.Column(db.DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(hours=1))
    used_at     = db.Column(db.DateTime, nullable=True)

    def is_valid(self):
        return self.used_at is None and self.expires_at > datetime.utcnow()
