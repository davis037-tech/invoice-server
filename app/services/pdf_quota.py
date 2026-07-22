from datetime import datetime, timedelta
from ..models import PdfDownload, PdfPlanLimit

DEFAULT_PDF_WEEKLY_LIMITS = {
    "FREE": 3,
    "PRO": 20,
    "TEAM": 100,
}


def all_pdf_plan_limits():
    rows = {row.plan: row.weekly_limit for row in PdfPlanLimit.query.all()}
    return {plan: rows.get(plan, default) for plan, default in DEFAULT_PDF_WEEKLY_LIMITS.items()}


def pdf_weekly_limit_for(tenant):
    if tenant.pdf_limit_override is not None:
        return tenant.pdf_limit_override
    row = PdfPlanLimit.query.get(tenant.plan.value)
    if row:
        return row.weekly_limit
    return DEFAULT_PDF_WEEKLY_LIMITS.get(tenant.plan.value, DEFAULT_PDF_WEEKLY_LIMITS["FREE"])


def pdf_downloads_this_week(tenant):
    since = datetime.utcnow() - timedelta(days=7)
    return PdfDownload.query.filter(
        PdfDownload.tenant_id == tenant.id,
        PdfDownload.created_at >= since,
    ).count()


def pdf_quota_status(tenant):
    limit = pdf_weekly_limit_for(tenant)
    used = pdf_downloads_this_week(tenant)
    return {"limit": limit, "used": used, "remaining": max(limit - used, 0)}
