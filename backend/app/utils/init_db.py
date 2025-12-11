"""
Database initialization utilities
"""

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from app.models.branch import Branch
from app.core.security import get_password_hash
from app.core.config import settings
from app.core.permissions import UserRole


def create_default_admin():
    """Create default admin user if not exists"""
    db = SessionLocal()
    try:
        # Check if admin user already exists
        admin_user = db.query(User).filter(User.username == "admin").first()

        if not admin_user:
            # Create default branch if not exists
            default_branch = db.query(Branch).filter(Branch.code == "MAIN").first()
            if not default_branch:
                default_branch = Branch(
                    name="Main Branch",
                    code="MAIN",
                    location="Head Office",
                    phone_number="+254700000000"
                )
                db.add(default_branch)
                db.commit()
                db.refresh(default_branch)

            # Create admin user
            admin_user = User(
                username="admin",
                phone_number="+254700000000",
                email=settings.DEFAULT_ADMIN_EMAIL,
                password_hash=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                first_name="System",
                last_name="Administrator",
                role_id=UserRole.ADMIN.value,
                branch_id=default_branch.id,
                unique_account_number="ADMIN001",
                must_change_password=True
            )
            db.add(admin_user)
            db.commit()
            print("✅ Default admin user created successfully")
        else:
            print("ℹ️  Admin user already exists")

    except Exception as e:
        print(f"❌ Error creating default admin: {e}")
        db.rollback()
    finally:
        db.close()


def initialize_database():
    """Initialize database with default data"""
    create_default_admin()
    print("🎯 Database initialization completed")
