from fastapi import APIRouter, Depends, HTTPException, status, Body
from src.database import get_mongodb, get_redis
from src.schemas import (
    MatchRequest,
    MatchResponse,
    MatchType,
    MatchStatus,
    SuccessResponse,
    ErrorResponse
)
from src.security import get_current_user, ONLINE_WINDOW_SECONDS
from src.utils import check_feature_permission, get_feature_limit, get_today_key
from datetime import datetime
import uuid
import random
import json
import time


router = APIRouter()


@router.post("/random", response_model=SuccessResponse)
async def random_match(
    request: MatchRequest,
    user_id: str = Depends(get_current_user)
):
    """随机匹配"""
    db = get_mongodb()
    redis = get_redis()

    user = await db["users"].find_one({"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 检查权限
    charm_value = user["charm_value"]
    if not check_feature_permission(charm_value, "match"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的魅力值不足，无法使用随机匹配功能"
        )

    # 检查每日使用次数
    today_key = get_today_key(user_id, "match")
    usage = await redis.get(today_key)
    usage_count = int(usage) if usage else 0
    limit = get_feature_limit(charm_value, "match")

    if usage_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"今日随机匹配次数已达上限 ({limit}次)"
        )

    # 幂等处理：如果用户已经在等待中，直接返回现有匹配任务
    existing_waiting = await db["matches"].find_one(
        {"user_id": user_id, "status": "waiting"},
        sort=[("start_time", -1)]
    )
    if existing_waiting:
        waiting_users = await redis.lrange("match_queue:random", 0, -1)
        in_queue = False
        for waiting_user_str in waiting_users:
            waiting_user = json.loads(waiting_user_str)
            if (
                waiting_user.get("user_id") == user_id
                and waiting_user.get("match_id") == existing_waiting["id"]
            ):
                in_queue = True
                break

        # 修复数据库和队列状态漂移：记录仍在 waiting 但队列丢失时补回队列
        if not in_queue:
            waiting_info = {
                "user_id": user_id,
                "match_id": existing_waiting["id"],
                "charm_value": charm_value,
                "joined_at": datetime.now().isoformat()
            }
            await redis.rpush("match_queue:random", json.dumps(waiting_info))

        return SuccessResponse(
            message="您已在匹配队列中，正在为您寻找匹配...",
            data={
                "match_id": existing_waiting["id"],
                "matched_user_id": None,
                "status": "waiting",
                "waiting_time": (datetime.now() - existing_waiting["start_time"]).total_seconds() if existing_waiting.get("start_time") else 0
            }
        )

    # 查找正在等待匹配的用户
    waiting_users = await redis.lrange("match_queue:random", 0, -1)

    matched_user = None
    match_id = None

    for waiting_user_str in waiting_users:
        waiting_user = json.loads(waiting_user_str)
        if waiting_user["user_id"] != user_id:
            # 清理失效记录，避免脏队列阻塞匹配
            waiting_match = await db["matches"].find_one(
                {
                    "id": waiting_user.get("match_id"),
                    "user_id": waiting_user["user_id"],
                    "status": "waiting"
                }
            )
            if not waiting_match:
                await redis.lrem("match_queue:random", 0, waiting_user_str)
                continue

            # 检查是否被拉黑
            is_blocked = await db["blocks"].find_one({
                "$or": [
                    {"user_id": user_id, "blocked_user_id": waiting_user["user_id"]},
                    {"user_id": waiting_user["user_id"], "blocked_user_id": user_id}
                ]
            })

            if not is_blocked:
                matched_user = waiting_user
                # 从队列中移除
                await redis.lrem("match_queue:random", 0, waiting_user_str)
                break

    if matched_user:
        # 找到匹配，创建匹配记录
        match_id = str(uuid.uuid4())
        match_record = {
            "id": match_id,
            "user_id": user_id,
            "matched_user_id": matched_user["user_id"],
            "type": "random",
            "status": "matched",
            "start_time": datetime.now(),
            "end_time": None
        }
        await db["matches"].insert_one(match_record)

        # 更新对方的匹配记录
        await db["matches"].update_one(
            {"id": matched_user["match_id"]},
            {"$set": {
                "matched_user_id": user_id,
                "status": "matched"
            }}
        )

        # 增加今日使用次数
        await redis.incr(today_key)
        await redis.expire(today_key, 86400)

        return SuccessResponse(
            message="匹配成功！",
            data={
                "match_id": match_id,
                "matched_user_id": matched_user["user_id"],
                "status": "matched",
                "waiting_time": 0
            }
        )
    else:
        # 没有找到匹配，加入等待队列
        match_id = str(uuid.uuid4())
        waiting_info = {
            "user_id": user_id,
            "match_id": match_id,
            "charm_value": charm_value,
            "joined_at": datetime.now().isoformat()
        }

        await redis.rpush("match_queue:random", json.dumps(waiting_info))

        # 创建匹配记录
        match_record = {
            "id": match_id,
            "user_id": user_id,
            "matched_user_id": None,
            "type": "random",
            "status": "waiting",
            "start_time": datetime.now(),
            "end_time": None
        }
        await db["matches"].insert_one(match_record)

        # 增加今日使用次数
        await redis.incr(today_key)
        await redis.expire(today_key, 86400)

        return SuccessResponse(
            message="已加入匹配队列，正在为您寻找匹配...",
            data={
                "match_id": match_id,
                "matched_user_id": None,
                "status": "waiting",
                "waiting_time": 0
            }
        )


@router.post("/online", response_model=SuccessResponse)
async def pick_online(
    request: MatchRequest,
    user_id: str = Depends(get_current_user)
):
    """捞个在线"""
    db = get_mongodb()
    redis = get_redis()

    user = await db["users"].find_one({"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 检查权限
    charm_value = user["charm_value"]
    if not check_feature_permission(charm_value, "match"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的魅力值不足，无法使用捞个在线功能"
        )

    # 检查每日使用次数
    today_key = get_today_key(user_id, "pick_online")
    usage = await redis.get(today_key)
    usage_count = int(usage) if usage else 0
    limit = get_feature_limit(charm_value, "pick_online")

    if usage_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"今日捞个在线次数已达上限 ({limit}次)"
        )

    # 获取最近活跃用户列表（在线窗口内）
    now_ts = int(time.time())
    min_ts = now_ts - ONLINE_WINDOW_SECONDS

    # 清理过期在线用户，避免集合无限增长
    await redis.zremrangebyscore("online_users:last_seen", 0, min_ts - 1)
    online_users = await redis.zrangebyscore("online_users:last_seen", min_ts, now_ts)
    online_users = list(online_users)

    if not online_users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="暂无在线用户"
        )

    # 筛选允许被发现的用户
    valid_users = []
    for uid in online_users:
        uid_str = uid.decode() if isinstance(uid, bytes) else uid
        if uid_str == user_id:
            continue

        # 检查是否允许被发现
        target_user = await db["users"].find_one({"id": uid_str})
        if target_user and target_user.get("allow_discovery", True):
            # 检查是否被拉黑
            is_blocked = await db["blocks"].find_one({
                "$or": [
                    {"user_id": user_id, "blocked_user_id": uid_str},
                    {"user_id": uid_str, "blocked_user_id": user_id}
                ]
            })

            if not is_blocked:
                valid_users.append(target_user)

    if not valid_users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="暂无符合条件的在线用户"
        )

    # 女性用户“捞个在线”优先匹配魅力值>=100的用户
    if user.get("gender") == "female":
        high_charm_users = [u for u in valid_users if u["charm_value"] >= 100]
        selected_user = random.choice(high_charm_users) if high_charm_users else random.choice(valid_users)
    else:
        selected_user = random.choice(valid_users)

    # 增加今日使用次数
    await redis.incr(today_key)
    await redis.expire(today_key, 86400)

    return SuccessResponse(
        message="捞取成功！",
        data={
            "user_id": selected_user["id"],
            "nickname": selected_user["nickname"],
            "avatar": selected_user.get("avatar"),
            "charm_value": selected_user["charm_value"]
        }
    )


@router.post("/cancel", response_model=SuccessResponse)
async def cancel_match(
    match_id: str = Body(..., embed=True),
    user_id: str = Depends(get_current_user)
):
    """取消匹配"""
    db = get_mongodb()
    redis = get_redis()

    # 从队列中移除
    waiting_users = await redis.lrange("match_queue:random", 0, -1)
    for waiting_user_str in waiting_users:
        waiting_user = json.loads(waiting_user_str)
        if waiting_user["match_id"] == match_id and waiting_user["user_id"] == user_id:
            await redis.lrem("match_queue:random", 0, waiting_user_str)
            break

    # 更新匹配记录状态
    await db["matches"].update_one(
        {"id": match_id, "user_id": user_id, "status": "waiting"},
        {"$set": {"status": "completed", "end_time": datetime.now()}}
    )

    return SuccessResponse(message="取消匹配成功")


@router.get("/status/{match_id}", response_model=SuccessResponse)
async def get_match_status(
    match_id: str,
    user_id: str = Depends(get_current_user)
):
    """获取匹配状态"""
    db = get_mongodb()

    match = await db["matches"].find_one({"id": match_id, "user_id": user_id})
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="匹配记录不存在"
        )

    return SuccessResponse(
        message="获取成功",
        data={
            "match_id": match["id"],
            "status": match["status"],
            "matched_user_id": match.get("matched_user_id"),
            "waiting_time": (datetime.now() - match["start_time"]).total_seconds() if match["start_time"] else 0
        }
    )
