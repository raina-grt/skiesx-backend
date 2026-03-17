from fastapi import  HTTPException, Header
import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
print("ENV ADMIN KEY:", ADMIN_API_KEY)
def verify_admin(x_admin_key: str = Header(None)):
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized admin access"
        )
