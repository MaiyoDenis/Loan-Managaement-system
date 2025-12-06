#!/usr/bin/env python3
"""
Script to update admin password with working bcrypt hash
"""

from app.database import get_db
from app.models.user import User

def update_admin_password():
    db = next(get_db())
    try:
        user = db.query(User).filter(User.username == 'admin').first()
        if user:
            # Pre-computed pbkdf2_sha256 hash for "admin123"
            user.password_hash = "$pbkdf2-sha256$29000$yRlDiPGec04pxbg3JqSUUg$mq8qqaMPk8hHUqw8ZVSVS4Lf82.VLcjO7DlMfmhWDIo"
            db.commit()
            print("✅ Admin password updated successfully")
        else:
            print("❌ Admin user not found")
    except Exception as e:
        print(f"❌ Error updating password: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_admin_password()
