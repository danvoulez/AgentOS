import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import List

from pydantic import EmailStr
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Add app directory to sys.path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import settings
from app.utils.auth import get_password_hash
from loguru import logger

ADMIN_EMAIL = os.getenv("INITIAL_ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD", "SecureAdminP@ssExcellentw0rd!")
ADMIN_ROLES: List[str] = ["admin", "staff"]

async def seed_initial_user():
    logger.info("Starting user seeding process...")
    if not settings.MONGODB_URI:
        logger.error("MONGODB_URI not set. Cannot seed user.")
        return

    client = None
    try:
        logger.info(f"Connecting to MongoDB at {settings.MONGODB_URI[:settings.MONGODB_URI.find('@')]}...")
        client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
        await client.admin.command('ping')

        uri_path = settings.MONGODB_URI.split('/')[-1]
        db_name = uri_path.split('?')[0] if '?' in uri_path else uri_path or "logline_v2_db"
        db = client[db_name]
        users_collection = db["users"]

        await users_collection.create_index("email", unique=True)
        await users_collection.create_index("username", unique=True)

        existing_admin = await users_collection.find_one({"email": ADMIN_EMAIL.lower()})
        if existing_admin:
            logger.warning(f"Admin user '{ADMIN_EMAIL}' already exists. Skipping seed.")
            return

        hashed_password = get_password_hash(ADMIN_PASSWORD)
        admin_user_doc = {
            "email": ADMIN_EMAIL.lower(),
            "username": ADMIN_EMAIL.lower(),
            "hashed_password": hashed_password,
            "roles": ADMIN_ROLES,
            "is_active": True,
            "profile": {"first_name": "Admin", "last_name": "User"},
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        insert_result = await users_collection.insert_one(admin_user_doc)
        logger.success(f"Admin user '{ADMIN_EMAIL}' created successfully with ID: {insert_result.inserted_id}")

    except Exception as e:
        logger.exception(f"An error occurred during user seeding: {e}")
    finally:
        if client:
            client.close()
            logger.info("MongoDB connection closed after seeding.")

if __name__ == "__main__":
    from loguru import logger as script_logger
    import sys
    script_logger.remove()
    script_logger.add(sys.stderr, level="DEBUG", colorize=True)
    logger = script_logger

    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        logger.info(f"Loaded environment variables from: {dotenv_path}")
    else:
        logger.warning(f".env file not found at {dotenv_path}. Relying on existing environment variables.")

    asyncio.run(seed_initial_user())