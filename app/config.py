import os 
from dotenv import load_dotenv

load_dotenv() 

class Config:
    SQLALCHEMY_DATABASE_URI         = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS  = False
    SECRET_KEY                      = os.getenv("SECRET_KEY")
    MAX_CONTENT_LENGTH              = 5 * 1024 * 1024  # 5MB request cap (covers base64 receipt photos)
    JWT_SECRET_KEY                  = os.getenv("JWT_SECRET")
    FRONTEND_URL                    = os.getenv("FRONTEND_URL", "http://localhost:5173") 
    # Any account logging in/registering with this email is automatically
    # granted platform-admin access. Set this on Render, not committed here.
    SUPERADMIN_EMAIL                = os.getenv("SUPERADMIN_EMAIL")
    # Email — used for automatic overdue payment reminders.
    RESEND_API_KEY                  = os.getenv("RESEND_API_KEY")
    RESEND_FROM_EMAIL               = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    # Secret the external cron trigger must send to run scheduled jobs
    # (there's no built-in scheduler on this host, so an outside service
    # hits our endpoint on a timer — this secret stops randoms from
    # triggering it themselves).
    CRON_SECRET                     = os.getenv("CRON_SECRET")
    CORS_ORIGINS                    = [os.getenv("FRONTEND_URL"), "http://localhost:5173"]
    


















