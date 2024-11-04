from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.config import AppSettings


async def get_mongo_client() -> AsyncIOMotorClient:
    raise NotImplementedError()


async def get_mongo_db() -> AsyncIOMotorDatabase:
    raise NotImplementedError()


async def get_app_config() -> AppSettings:
    raise NotImplementedError()
