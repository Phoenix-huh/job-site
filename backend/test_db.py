import os
from dotenv import load_dotenv
load_dotenv()
from database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1"))
        print(res.fetchall())
except Exception as e:
    print(f"Error: {e}")
