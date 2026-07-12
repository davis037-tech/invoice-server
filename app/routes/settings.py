from flask import Blueprint, request, jsonify, g
from ..extensions import db
from ..middleware.auth import require_auth, attach_tenant

settings_bp = Blueprint("settings", __name__)

ALLOWED_FIELDS = (
    "business_name",
    "business_logo",
    "business_address",
    "primary_color",
    "currency",
    "tax_rate",
    "payment_info",
    "bank_name",
    "account_name",
    "account_number",
    "routing_number",
    "swift_code",
    "payment_notes",
)


@settings_bp.get("/")
@require_auth
@attach_tenant
def get_settings():
    return jsonify({"data": g.tenant.settings.to_dict()}), 200


@settings_bp.put("/")
@require_auth
@attach_tenant
def update_settings():
    data = request.get_json() or {}
    settings = g.tenant.settings
    for key in ALLOWED_FIELDS:
        if key in data:
            setattr(settings, key, data[key])
    db.session.commit()
    return jsonify({"data": settings.to_dict()}), 200
