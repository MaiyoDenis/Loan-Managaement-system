"""
Database initialization utilities
"""

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from app.models.role import Role
from app.core.security import get_password_hash
from app.core.config import settings


def create_default_admin():
    """
    Create default admin user if it doesn't exist
    """
    db: Session = SessionLocal()

    try:
        # Check if admin role already exists
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(name="admin", description="Administrator")
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)

        # Check if admin user already exists
        admin_user = db.query(User).filter(User.username == "admin").first()

        if admin_user:
            print("✅ Admin user already exists")
            return

        # Create default admin user
        admin_user = User(
            username="admin",
            email=settings.DEFAULT_ADMIN_EMAIL,
            first_name="System",
            last_name="Administrator",
            phone_number="+254700000000",  # Default phone number
            password_hash=get_password_hash("admin123"),
            role_id=admin_role.id,
            is_active=True,
            must_change_password=False
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print("✅ Default admin user created successfully")
        print(f"   Username: admin")
        print(f"   Email: {settings.DEFAULT_ADMIN_EMAIL}")
        print(f"   Password: admin123")

    except Exception as e:
        print(f"❌ Error creating default admin user: {e}")
        db.rollback()
    finally:
        db.close()


def init_database():
    """
    Initialize database with default data
    """
    from app.database import engine
    from app.models import *  # Import to register models
    from app.models.base import Base

    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


if __name__ == "__main__":
    # Run database initialization
    init_database()
    create_default_admin()
