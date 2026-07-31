from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g, current_app
from ..extensions import db
from ..models import Tenant, User, Invoice, PlanLimit, PdfPlanLimit, LoginEvent, UpgradeRequest, PlatformSettings
from ..middleware.auth import require_auth, require_superadmin
from ..services.quota import quota_status, all_plan_limits, DEFAULT_PLAN_WEEKLY_LIMITS
from ..services.pdf_quota import pdf_quota_status, all_pdf_plan_limits, DEFAULT_PDF_WEEKLY_LIMITS
from ..services.email_service import upgrade_approved_email, EmailError

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


@admin_bp.get("/plan-limits")
@require_auth
@require_superadmin
def get_plan_limits():
    return jsonify({"data": all_plan_limits()}), 200


@admin_bp.put("/plan-limits")
@require_auth
@require_superadmin
def update_plan_limits():
    """
    Body: { "FREE": 5, "PRO": 25, "TEAM": 100 } — any subset of plans.
    These are the defaults every tenant on that plan gets, unless that
    specific tenant has an invoice_limit_override set.
    """
    data = request.get_json() or {}
    valid_plans = set(DEFAULT_PLAN_WEEKLY_LIMITS.keys())
    for plan, limit in data.items():
        if plan not in valid_plans:
            return jsonify({"error": f"Invalid plan '{plan}'. Choose from {list(valid_plans)}"}), 422
        if not isinstance(limit, int) or limit < 0:
            return jsonify({"error": f"weekly_limit for {plan} must be a non-negative integer"}), 422
        row = PlanLimit.query.get(plan)
        if row:
            row.weekly_limit = limit
        else:
            db.session.add(PlanLimit(plan=plan, weekly_limit=limit))
    db.session.commit()
    return jsonify({"data": all_plan_limits()}), 200


@admin_bp.get("/pdf-plan-limits")
@require_auth
@require_superadmin
def get_pdf_plan_limits():
    return jsonify({"data": all_pdf_plan_limits()}), 200


@admin_bp.put("/pdf-plan-limits")
@require_auth
@require_superadmin
def update_pdf_plan_limits():
    data = request.get_json() or {}
    valid_plans = set(DEFAULT_PDF_WEEKLY_LIMITS.keys())
    for plan, limit in data.items():
        if plan not in valid_plans:
            return jsonify({"error": f"Invalid plan '{plan}'. Choose from {list(valid_plans)}"}), 422
        if not isinstance(limit, int) or limit < 0:
            return jsonify({"error": f"weekly_limit for {plan} must be a non-negative integer"}), 422
        row = PdfPlanLimit.query.get(plan)
        if row:
            row.weekly_limit = limit
        else:
            db.session.add(PdfPlanLimit(plan=plan, weekly_limit=limit))
    db.session.commit()
    return jsonify({"data": all_pdf_plan_limits()}), 200


@admin_bp.get("/login-activity")
@require_auth
@require_superadmin
def login_activity():
    """
    Returns a 7-day daily breakdown (login count + unique users per day)
    plus the most recent individual login events, so the admin panel can
    show both "who's logging in daily/weekly" and the raw list.
    """
    now = datetime.utcnow()
    since_week = now - timedelta(days=7)

    events = LoginEvent.query.filter(LoginEvent.created_at >= since_week) \
        .order_by(LoginEvent.created_at.desc()).all()

    daily = {}
    for i in range(7):
        day = (now - timedelta(days=i)).date()
        daily[day.isoformat()] = {"date": day.isoformat(), "count": 0, "users": set()}

    for e in events:
        day_key = e.created_at.date().isoformat()
        if day_key in daily:
            daily[day_key]["count"] += 1
            daily[day_key]["users"].add(e.email)

    daily_list = sorted(daily.values(), key=lambda d: d["date"])
    daily_list = [{"date": d["date"], "count": d["count"], "unique_users": len(d["users"])} for d in daily_list]

    recent = [{
        "email": e.email,
        "tenant_name": e.tenant_name,
        "created_at": e.created_at.isoformat(),
    } for e in events[:200]]

    today_key = now.date().isoformat()
    return jsonify({
        "data": {
            "daily": daily_list,
            "recent": recent,
            "unique_today": len({e.email for e in events if e.created_at.date().isoformat() == today_key}),
            "unique_this_week": len({e.email for e in events}),
        }
    }), 200


@admin_bp.get("/platform-settings")
@require_auth
@require_superadmin
def get_platform_settings():
    return jsonify({"data": PlatformSettings.get().to_dict()}), 200


@admin_bp.put("/platform-settings")
@require_auth
@require_superadmin
def update_platform_settings():
    settings = PlatformSettings.get()
    data = request.get_json() or {}
    for key in ("bank_name", "account_name", "account_number", "routing_number", "swift_code"):
        if key in data:
            setattr(settings, key, data[key])
    db.session.commit()
    return jsonify({"data": settings.to_dict()}), 200


@admin_bp.get("/upgrade-requests")
@require_auth
@require_superadmin
def list_upgrade_requests():
    status_filter = request.args.get("status", "PENDING")
    query = UpgradeRequest.query
    if status_filter != "all":
        query = query.filter_by(status=status_filter)
    requests_ = query.order_by(UpgradeRequest.created_at.desc()).all()

    data = []
    for r in requests_:
        tenant = Tenant.query.get(r.tenant_id)
        owner = User.query.filter_by(tenant_id=r.tenant_id).order_by(User.created_at.asc()).first()
        d = r.to_dict()
        d["tenant_name"] = tenant.name if tenant else None
        d["owner_email"] = owner.email if owner else None
        d["current_plan"] = tenant.plan.value if tenant else None
        data.append(d)

    return jsonify({"data": data, "meta": {"total": len(data)}}), 200


@admin_bp.post("/upgrade-requests/<request_id>/approve")
@require_auth
@require_superadmin
def approve_upgrade_request(request_id):
    req = UpgradeRequest.query.get(request_id)
    if not req:
        return jsonify({"error": "Request not found"}), 404
    if req.status != "PENDING":
        return jsonify({"error": f"This request is already {req.status.lower()}."}), 400

    tenant = Tenant.query.get(req.tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404

    tenant.plan = req.requested_plan
    req.status = "APPROVED"
    req.reviewed_at = datetime.utcnow()
    db.session.commit()

    try:
        owner = User.query.filter_by(tenant_id=tenant.id).order_by(User.created_at.asc()).first()
        if owner and current_app.config.get("RESEND_API_KEY"):
            upgrade_approved_email(owner.email, tenant, req.requested_plan)
    except EmailError as e:
        current_app.logger.error(f"upgrade_approved_email failed: {e}")

    return jsonify({"data": req.to_dict()}), 200


@admin_bp.post("/upgrade-requests/<request_id>/reject")
@require_auth
@require_superadmin
def reject_upgrade_request(request_id):
    req = UpgradeRequest.query.get(request_id)
    if not req:
        return jsonify({"error": "Request not found"}), 404
    if req.status != "PENDING":
        return jsonify({"error": f"This request is already {req.status.lower()}."}), 400

    req.status = "REJECTED"
    req.reviewed_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"data": req.to_dict()}), 200


@admin_bp.get("/tenants")
@require_auth
@require_superadmin
def list_tenants():
    tenants = Tenant.query.order_by(Tenant.created_at.desc()).all()
    data = []
    for t in tenants:
        owner = User.query.filter_by(tenant_id=t.id).order_by(User.created_at.asc()).first()
        status = quota_status(t)
        pdf_status = pdf_quota_status(t)
        data.append({
            "id": t.id,
            "name": t.name,
            "owner_email": owner.email if owner else None,
            "plan": t.plan.value,
            "invoice_limit_override": t.invoice_limit_override,
            "weekly_limit": status["limit"],
            "weekly_used": status["used"],
            "pdf_limit_override": t.pdf_limit_override,
            "pdf_weekly_limit": pdf_status["limit"],
            "pdf_weekly_used": pdf_status["used"],
            "total_invoices": Invoice.query.filter_by(tenant_id=t.id).count(),
            "created_at": t.created_at.isoformat(),
        })
    return jsonify({"data": data, "meta": {"total": len(data), "plans": list(DEFAULT_PLAN_WEEKLY_LIMITS.keys())}}), 200


@admin_bp.put("/tenants/<tenant_id>")
@require_auth
@require_superadmin
def update_tenant(tenant_id):
    tenant = Tenant.query.get(tenant_id)
    if not tenant:
        return jsonify({"error": "Tenant not found"}), 404

    data = request.get_json() or {}

    if "plan" in data:
        if data["plan"] not in DEFAULT_PLAN_WEEKLY_LIMITS:
            return jsonify({"error": f"Invalid plan. Choose one of {list(DEFAULT_PLAN_WEEKLY_LIMITS.keys())}"}), 422
        tenant.plan = data["plan"]

    if "invoice_limit_override" in data:
        value = data["invoice_limit_override"]
        if value is not None and (not isinstance(value, int) or value < 0):
            return jsonify({"error": "invoice_limit_override must be a non-negative integer or null"}), 422
        tenant.invoice_limit_override = value

    if "pdf_limit_override" in data:
        value = data["pdf_limit_override"]
        if value is not None and (not isinstance(value, int) or value < 0):
            return jsonify({"error": "pdf_limit_override must be a non-negative integer or null"}), 422
        tenant.pdf_limit_override = value

    db.session.commit()
    status = quota_status(tenant)
    pdf_status = pdf_quota_status(tenant)
    return jsonify({
        "data": {
            "id": tenant.id,
            "name": tenant.name,
            "plan": tenant.plan.value,
            "invoice_limit_override": tenant.invoice_limit_override,
            "weekly_limit": status["limit"],
            "weekly_used": status["used"],
            "pdf_limit_override": tenant.pdf_limit_override,
            "pdf_weekly_limit": pdf_status["limit"],
            "pdf_weekly_used": pdf_status["used"],
        }
    }), 200
