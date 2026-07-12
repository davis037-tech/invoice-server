from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g
from ..extensions import db
from ..models import Tenant, User, Invoice
from ..middleware.auth import require_auth, require_superadmin
from ..services.quota import quota_status, PLAN_WEEKLY_LIMITS

admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/stats")
@require_auth
@require_superadmin
def platform_stats():
    since_week = datetime.utcnow() - timedelta(days=7)
    return jsonify({
        "data": {
            "total_tenants": Tenant.query.count(),
            "total_users": User.query.count(),
            "signups_this_week": Tenant.query.filter(Tenant.created_at >= since_week).count(),
            "invoices_this_week": Invoice.query.filter(Invoice.created_at >= since_week).count(),
            "total_invoices": Invoice.query.count(),
        }
    }), 200


@admin_bp.get("/tenants")
@require_auth
@require_superadmin
def list_tenants():
    tenants = Tenant.query.order_by(Tenant.created_at.desc()).all()
    data = []
    for t in tenants:
        owner = User.query.filter_by(tenant_id=t.id).order_by(User.created_at.asc()).first()
        status = quota_status(t)
        data.append({
            "id": t.id,
            "name": t.name,
            "owner_email": owner.email if owner else None,
            "plan": t.plan.value,
            "invoice_limit_override": t.invoice_limit_override,
            "weekly_limit": status["limit"],
            "weekly_used": status["used"],
            "total_invoices": Invoice.query.filter_by(tenant_id=t.id).count(),
            "created_at": t.created_at.isoformat(),
        })
    return jsonify({"data": data, "meta": {"total": len(data), "plans": list(PLAN_WEEKLY_LIMITS.keys())}}), 200


@admin_bp.put("/tenants/<tenant_id>")
@require_auth
@require_superadmin
def update_tenant(tenant_id):
    tenant = Tenant.query.get(tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404

    data = request.get_json() or {}

    if "plan" in data:
        if data["plan"] not in PLAN_WEEKLY_LIMITS:
            return jsonify({"error": f"Invalid plan. Choose one of {list(PLAN_WEEKLY_LIMITS.keys())}"}), 422
        tenant.plan = data["plan"]

    if "invoice_limit_override" in data:
        value = data["invoice_limit_override"]
        if value is not None and (not isinstance(value, int) or value < 0):
            return jsonify({"error": "invoice_limit_override must be a non-negative integer or null"}), 422
        tenant.invoice_limit_override = value

    db.session.commit()
    status = quota_status(tenant)
    return jsonify({
        "data": {
            "id": tenant.id,
            "name": tenant.name,
            "plan": tenant.plan.value,
            "invoice_limit_override": tenant.invoice_limit_override,
            "weekly_limit": status["limit"],
            "weekly_used": status["used"],
        }
    }), 200
