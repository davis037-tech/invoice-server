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
    CORS_ORIGINS                    = [os.getenv("FRONTEND_URL"), "http://localhost:5173"]
    


















