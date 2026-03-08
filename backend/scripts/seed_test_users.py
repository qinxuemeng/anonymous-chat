#!/usr/bin/env python3
"""Seed test users to MongoDB and online status to Redis."""

from __future__ import annotations

import argparse
import random
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


NICKNAME_WORDS = [
    "神秘人", "旅人", "过客", "风铃", "白桃", "木槿", "月光", "星河",
    "海盐", "柚子", "青柠", "晚风", "山雀", "雨滴", "鲸鱼", "云朵",
]

TAG_POOL = [
    "社恐", "夜猫子", "旅行", "看书", "电影", "摄影", "健身", "做饭",
    "二次元", "独处", "散步", "听歌", "咖啡", "发呆", "爬山", "游戏",
]

CITY_POOL = [
    "北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安", "重庆", "南京",
]

GENDER_POOL = ["male", "female", "secret"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="向 MongoDB/Redis 写入测试用户数据")
    parser.add_argument("--count", type=int, default=20, help="创建用户数，默认 20")
    parser.add_argument("--online-count", type=int, default=10, help="写入在线状态的用户数，默认 10")
    parser.add_argument("--start-index", type=int, default=1, help="用户名起始序号，默认 1")
    parser.add_argument("--prefix", type=str, default="testuser", help="测试用户名统一前缀，默认 testuser")
    parser.add_argument("--password", type=str, default="Test123456", help="测试账号统一密码，默认 Test123456")
    parser.add_argument("--with-announcements", type=int, default=0, help="额外生成已审核公告数量，默认 0")
    parser.add_argument("--reset-prefix", action="store_true", help="先删除当前前缀下的历史测试用户")
    return parser.parse_args()


def build_user_doc(username: str, password_hash: str) -> dict:
    now = datetime.now()
    age = random.randint(18, 35)
    nickname = f"{random.choice(NICKNAME_WORDS)}{random.randint(100, 999)}"
    tags = random.sample(TAG_POOL, k=random.randint(2, 5))
    charm_value = random.choice([20, 30, 50, 80, 120, 180, 260, 400])
    show_location = random.choice([True, False])
    allow_discovery = random.choice([True, True, True, False])

    return {
        "id": str(uuid.uuid4()),
        "username": username,
        "password": password_hash,
        "email": None,
        "phone": None,
        "avatar": None,
        "nickname": nickname,
        "gender": random.choice(GENDER_POOL),
        "age": age,
        "location": random.choice(CITY_POOL),
        "tags": tags,
        "charm_value": charm_value,
        "allow_discovery": allow_discovery,
        "green_mode": random.choice([True, False]),
        "night_mode": random.choice([True, False]),
        "notification_sound": True,
        "keep_logged_in": random.choice([True, False]),
        "english_mode": False,
        "show_location": show_location,
        "created_at": now,
        "updated_at": now,
        "last_login_at": now,
        "is_active": True,
    }


def clear_existing_prefix(db, redis_client: Any, prefix: str) -> None:
    users = list(db["users"].find({"username": {"$regex": f"^{prefix}_"}}))
    if not users:
        return

    user_ids = [u["id"] for u in users]
    db["users"].delete_many({"id": {"$in": user_ids}})
    db["matches"].delete_many({"$or": [{"user_id": {"$in": user_ids}}, {"matched_user_id": {"$in": user_ids}}]})
    db["chats"].delete_many({"$or": [{"from_user_id": {"$in": user_ids}}, {"to_user_id": {"$in": user_ids}}]})
    db["blocks"].delete_many({"$or": [{"user_id": {"$in": user_ids}}, {"blocked_user_id": {"$in": user_ids}}]})
    db["announcements"].delete_many({"user_id": {"$in": user_ids}})
    db["announcement_claims"].delete_many({"claimant_user_id": {"$in": user_ids}})

    if user_ids:
        redis_client.zrem("online_users:last_seen", *user_ids)
        redis_client.srem("online_users", *user_ids)


def seed_announcements(db, users: list[dict], count: int) -> int:
    if count <= 0 or not users:
        return 0

    now = datetime.now()
    docs = []
    for i in range(count):
        u = users[i % len(users)]
        docs.append(
            {
                "id": str(uuid.uuid4()),
                "user_id": u["id"],
                "nickname": u["nickname"],
                "content": f"测试公告 {i + 1}：这是 {u['nickname']} 发布的功能联调公告。",
                "tags": random.sample(TAG_POOL, k=2),
                "status": "approved",
                "views": random.randint(0, 80),
                "created_at": now,
                "approved_at": now,
            }
        )
    db["announcements"].insert_many(docs)
    return len(docs)


def main() -> int:
    args = parse_args()

    if args.count <= 0:
        print("count 必须大于 0")
        return 1

    try:
        from pymongo import MongoClient
        from redis import Redis
    except ImportError:
        print("缺少依赖，请先安装 backend/requirements.txt")
        print("例如: cd backend && pip install -r requirements.txt")
        return 1

    from src.config import settings
    from src.security import get_password_hash

    mongo = MongoClient(settings.mongodb_uri)
    db = mongo[settings.mongodb_db_name]
    redis_client = Redis.from_url(settings.redis_uri, db=settings.redis_db, decode_responses=True)

    try:
        if args.reset_prefix:
            clear_existing_prefix(db, redis_client, args.prefix)

        password_hash = get_password_hash(args.password)
        created_or_updated = []

        for i in range(args.start_index, args.start_index + args.count):
            username = f"{args.prefix}_{i:03d}"
            existing = db["users"].find_one({"username": username})

            if existing:
                db["users"].update_one(
                    {"id": existing["id"]},
                    {
                        "$set": {
                            "password": password_hash,
                            "allow_discovery": True,
                            "updated_at": datetime.now(),
                            "last_login_at": datetime.now(),
                            "is_active": True,
                        }
                    },
                )
                user = db["users"].find_one({"id": existing["id"]})
                created_or_updated.append(user)
            else:
                user = build_user_doc(username, password_hash)
                db["users"].insert_one(user)
                created_or_updated.append(user)

        online_count = min(args.online_count, len(created_or_updated))
        online_users = random.sample(created_or_updated, k=online_count) if online_count > 0 else []
        now_ts = int(time.time())
        for idx, user in enumerate(online_users):
            redis_client.zadd("online_users:last_seen", {user["id"]: now_ts - idx * 3})
            redis_client.sadd("online_users", user["id"])

        ann_count = seed_announcements(db, created_or_updated, args.with_announcements)

        print("测试数据写入完成")
        print(f"- Mongo users: {len(created_or_updated)}")
        print(f"- Redis online_users:last_seen: {len(online_users)}")
        if ann_count > 0:
            print(f"- Mongo announcements(approved): {ann_count}")
        print(f"- 统一密码: {args.password}")
        print("- 示例账号:")
        for user in created_or_updated[: min(8, len(created_or_updated))]:
            print(f"  - {user['username']} ({user['nickname']})")
        return 0
    finally:
        mongo.close()
        redis_client.close()


if __name__ == "__main__":
    raise SystemExit(main())
