import os 
from dotenv import load_dotenv

load_dotenv() 

class Config:
    SQLALCHEMY_DATABASE_URI         = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS  = False
    SECRET_KEY                      = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY                  = os.getenv("JWT_SECRET")
    FLW_SECRET_KEY                  = os.getenv("FLW_SECRET_KEY")
    FLW_WEBHOOK_SECRET              = os.getenv("FLW_WEBHOOK_SECRET")
    FLW_PUBLIC_KEY                  = os.getenv("FLW_PUBLIC_KEY")
    FRONTEND_URL                    = os.getenv("FRONTEND_URL", "http://localhost:5173") 
    CORS_ORIGINS                    = [os.getenv("FRONTEND_URL"), "http://localhost:5173"]
    


















