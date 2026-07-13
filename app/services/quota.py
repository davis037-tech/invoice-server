from datetime import datetime, timedelta
from ..models import Invoice, PlanLimit

# Fallback defaults if the plan_limits table is somehow empty (shouldn't
# happen — db_bootstrap seeds it on startup). Admins edit the real values
# from the Admin panel; these are just a safety net.
DEFAULT_PLAN_WEEKLY_LIMITS = {
    "FREE": 5,
    "PRO": 25,
    "TEAM": 100,
}


def all_plan_limits():
    rows = {row.plan: row.weekly_limit for row in PlanLimit.query.all()}
    return {plan: rows.get(plan, default) for plan, default in DEFAULT_PLAN_WEEKLY_LIMITS.items()}


def weekly_limit_for(tenant):
    if tenant.invoice_limit_override is not None:
        return tenant.invoice_limit_override
    row = PlanLimit.query.get(tenant.plan.value)
    if row:
        return row.weekly_limit
    return DEFAULT_PLAN_WEEKLY_LIMITS.get(tenant.plan.value, DEFAULT_PLAN_WEEKLY_LIMITS["FREE"])


def invoices_created_this_week(tenant):
    since = datetime.utcnow() - timedelta(days=7)
    return Invoice.query.filter(
        Invoice.tenant_id == tenant.id,
        Invoice.created_at >= since,
    ).count()


def quota_status(tenant):
    limit = weekly_limit_for(tenant)
    used = invoices_created_this_week(tenant)
    return {"limit": limit, "used": used, "remaining": max(limit - used, 0)}


def has_quota_remaining(tenant):
    status = quota_status(tenant)
    return status["remaining"] > 0
