from ..extensions import db


class PdfPlanLimit(db.Model):
    """
    Admin-editable default weekly PDF download quota per plan tier.
    Kept as its own table (rather than extending PlanLimit) since that
    table is already live with `plan` as its sole primary key — adding a
    second limit type there would need a real schema migration, not just
    a new column. A tenant's actual limit is this value unless
    Tenant.pdf_limit_override is set, which always wins for that tenant.
    """
    __tablename__ = "pdf_plan_limits"

    plan          = db.Column(db.String, primary_key=True)  # "FREE" / "PRO" / "TEAM"
    weekly_limit  = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {"plan": self.plan, "weekly_limit": self.weekly_limit}
