from flask import Blueprint, request, jsonify, g
from ..extensions import db
from ..models import BusinessProfile
from ..middleware.auth import require_auth, attach_tenant

business_profiles_bp = Blueprint("business_profiles", __name__)

ALLOWED_FIELDS = (
    "label",
    "business_name",
    "business_logo",
    "business_address",
    "primary_color",
    "bank_name",
    "account_name",
    "account_number",
    "routing_number",
    "swift_code",
    "payment_notes",
)


@business_profiles_bp.get("/")
@require_auth
@attach_tenant
def list_business_profiles():
    profiles = BusinessProfile.query.filter_by(tenant_id=g.tenant.id).order_by(BusinessProfile.created_at.asc()).all()
    return jsonify({"data": [p.to_dict() for p in profiles]}), 200


@business_profiles_bp.post("/")
@require_auth
@attach_tenant
def create_business_profile():
    data = request.get_json() or {}
    if not (data.get("label") or "").strip():
        return jsonify({"error": "Give this profile a label, e.g. 'Brand A'."}), 422

    profile = BusinessProfile(tenant_id=g.tenant.id)
    for key in ALLOWED_FIELDS:
        if key in data:
            setattr(profile, key, data[key])

    # First profile a tenant creates becomes the default automatically.
    existing_count = BusinessProfile.query.filter_by(tenant_id=g.tenant.id).count()
    if existing_count == 0:
        profile.is_default = True

    db.session.add(profile)
    db.session.commit()
    return jsonify({"data": profile.to_dict()}), 201


@business_profiles_bp.put("/<profile_id>")
@require_auth
@attach_tenant
def update_business_profile(profile_id):
    profile = BusinessProfile.query.filter_by(id=profile_id, tenant_id=g.tenant.id).first()
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    data = request.get_json() or {}
    for key in ALLOWED_FIELDS:
        if key in data:
            setattr(profile, key, data[key])
    db.session.commit()
    return jsonify({"data": profile.to_dict()}), 200


@business_profiles_bp.post("/<profile_id>/set-default")
@require_auth
@attach_tenant
def set_default_business_profile(profile_id):
    profile = BusinessProfile.query.filter_by(id=profile_id, tenant_id=g.tenant.id).first()
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    BusinessProfile.query.filter_by(tenant_id=g.tenant.id).update({"is_default": False})
    profile.is_default = True
    db.session.commit()
    return jsonify({"data": profile.to_dict()}), 200


@business_profiles_bp.delete("/<profile_id>")
@require_auth
@attach_tenant
def delete_business_profile(profile_id):
    profile = BusinessProfile.query.filter_by(id=profile_id, tenant_id=g.tenant.id).first()
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    was_default = profile.is_default
    db.session.delete(profile)
    db.session.flush()

    # If we just deleted the default, promote whichever profile is left (if any).
    if was_default:
        remaining = BusinessProfile.query.filter_by(tenant_id=g.tenant.id).order_by(BusinessProfile.created_at.asc()).first()
        if remaining:
            remaining.is_default = True

    db.session.commit()
    return "", 204
