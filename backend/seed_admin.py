"""
seed_admin.py — Run once to create the first admin account.
Run from backend/ directory:
    python seed_admin.py

Change the email and password before running.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.crud.admin import get_admin_by_email, create_admin

ADMIN_EMAIL    = "abc@gmail.com"
ADMIN_PASSWORD = "12345678"   # Change this before running


def main():
    db = SessionLocal()
    try:
        existing = get_admin_by_email(db, ADMIN_EMAIL)
        if existing:
            print(f"[SKIP] Admin already exists: {ADMIN_EMAIL}")
            return
        admin = create_admin(db, ADMIN_EMAIL, ADMIN_PASSWORD)
        print(f"[OK] Admin created: {admin.email} (id={admin.id})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
