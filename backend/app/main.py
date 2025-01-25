import os
import logging
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from app.core.database import db
from app.core.security import hash_password
from app.api import auth, users, conversations, deployments, ai

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=LOG_LEVEL,
    format="[%(asctime)s] %(levelname)s in %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# QUIET noisy libraries at or above ERROR:
logging.getLogger("pymongo").setLevel(logging.ERROR)
logging.getLogger("passlib").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)

app = FastAPI(title="AI-Powered App Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your existing routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])
app.include_router(deployments.router, prefix="/deployments", tags=["Deployments"])
app.include_router(ai.router, prefix="/ai", tags=["AI"])

@app.on_event("startup")
async def seed_first_admin():
    # same logic as before
    first_admin_email = os.getenv("FIRST_ADMIN_EMAIL")
    first_admin_username = os.getenv("FIRST_ADMIN_USERNAME")
    first_admin_password = os.getenv("FIRST_ADMIN_PASSWORD")

    if not (first_admin_email and first_admin_username and first_admin_password):
        logger.info("No FIRST_ADMIN_* environment vars set. Skipping admin seed.")
        return

    existing_admin = await db["users"].find_one({"email": first_admin_email})
    if existing_admin:
        logger.info(f"Admin user already exists for {first_admin_email}, skipping seed.")
        return

    hashed_pass = hash_password(first_admin_password)
    new_admin = {
        "username": first_admin_username,
        "email": first_admin_email,
        "role": "admin",
        "hashed_password": hashed_pass
    }
    result = await db["users"].insert_one(new_admin)

    logger.info("=========================================")
    logger.info(" FIRST TIME ADMIN CREATED! ")
    logger.info(f"  ID: {str(result.inserted_id)}")
    logger.info(f"  Username: {first_admin_username}")
    logger.info(f"  Email: {first_admin_email}")
    logger.info(f"  Password: {first_admin_password}")
    logger.info("=========================================")

@app.get("/")
def health_check():
    logger.debug("Health check endpoint called.")
    return {"status": "ok", "message": "Backend is running"}
