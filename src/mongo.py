from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.config import MongoSetting


def create_mongo_client(config: MongoSetting):
    client = AsyncIOMotorClient(
        config.host,
        config.port,
        username=config.username,
        password=config.password,
    )

    return client


def get_mongodb(
    mongo: AsyncIOMotorClient, config: MongoSetting
) -> AsyncIOMotorDatabase:
    return mongo.get_database(config.database)
