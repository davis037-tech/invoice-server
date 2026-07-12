from datetime import datetime, timedelta
from ..models import Invoice

# Default weekly invoice quota per plan tier. A tenant's actual limit is
# this value unless an admin has set invoice_limit_override, which always
# wins (used to grant a one-off bump or a custom deal).
PLAN_WEEKLY_LIMITS = {
    "FREE": 5,
    "PRO": 25,
    "TEAM": 100,
}


def weekly_limit_for(tenant):
    if tenant.invoice_limit_override is not None:
        return tenant.invoice_limit_override
    return PLAN_WEEKLY_LIMITS.get(tenant.plan.value, PLAN_WEEKLY_LIMITS["FREE"])


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
