import os
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("PORT", "8000"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")
DB_PATH = os.getenv("DB_PATH", "data/audit.db")
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "90"))
MAX_BODY_SIZE = int(os.getenv("MAX_BODY_SIZE", "102400"))  # 100KB
