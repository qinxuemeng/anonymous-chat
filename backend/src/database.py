import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from src.config import settings
import redis.asyncio as redis


# MongoDB 连接
class MongoDB:
    client: Optional[AsyncIOMotorClient] = None


mongodb = MongoDB()


async def connect_to_mongodb():
    mongodb.client = AsyncIOMotorClient(settings.mongodb_uri)
    print(f"Connected to MongoDB: {settings.mongodb_uri}")


async def close_mongodb_connection():
    if mongodb.client:
        mongodb.client.close()
        print("Disconnected from MongoDB")


def get_mongodb():
    return mongodb.client[settings.mongodb_db_name]


# Redis 连接
redis_client: Optional[redis.Redis] = None


async def connect_to_redis():
    global redis_client
    redis_client = redis.from_url(settings.redis_uri, db=settings.redis_db)
    try:
        await redis_client.ping()
        print(f"Connected to Redis: {settings.redis_uri}")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        raise


async def close_redis_connection():
    global redis_client
    if redis_client:
        await redis_client.close()
        print("Disconnected from Redis")


def get_redis() -> redis.Redis:
    if not redis_client:
        raise Exception("Redis client not connected")
    return redis_client