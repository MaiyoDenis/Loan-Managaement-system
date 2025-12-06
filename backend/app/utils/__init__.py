"""
Database initialization utilities
"""

import asyncio
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.base import Base
from app.models.user import User
from app.models.branch import Branch
from app.core.security import get_password_hash
from app.core.config import settings
from app.core.permissions import UserRole


async def create_default_admin():
    """Create default admin user if not exists"""
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin_user = db.query(User).filter(
            User.role == UserRole.ADMIN
        ).first()
        
        if not admin_user:
            # Create default admin
            admin = User(
                username="admin",
                phone_number="+254700000000",
                email=settings.DEFAULT_ADMIN_EMAIL,
                first_name="System",
                last_name="Administrator",
                password_hash=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True,
                must_change_password=False
            )
            
            db.add(admin)
            db.commit()
            
            print("✅ Default admin user created")
            print(f"   Username: admin")
            print(f"   Password: {settings.DEFAULT_ADMIN_PASSWORD}")
            print(f"   Email: {settings.DEFAULT_ADMIN_EMAIL}")
        else:
            print("ℹ️  Admin user already exists")
            
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()


def init_database():
    """Initialize database with tables"""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created")
        
        # Run async initialization
        asyncio.run(create_default_admin())
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")


if __name__ == "__main__":
    init_database()