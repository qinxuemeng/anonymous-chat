from fastapi import APIRouter, Depends, HTTPException, status, Body
from src.database import get_mongodb, get_redis
from src.schemas import (
    MatchRequest,
    SuccessResponse,
)
from src.security import get_current_user, ONLINE_WINDOW_SECONDS
from src.utils import check_feature_permission, get_feature_limit, get_today_key
from datetime import datetime
import uuid
import random
import json
import time


router = APIRouter()
DAILY_PICK_ONLINE_FREE_LIMIT = 10
DIRECTIONAL_CHARM_COST = 5


async def reset_chat_state_on_rematch(db, user_a_id: str, user_b_id: str):
    """再次匹配成功后，重置双方会话到首次匹配状态。"""
    await db["chats"].delete_many({
        "$or": [
            {"from_user_id": user_a_id, "to_user_id": user_b_id},
            {"from_user_id": user_b_id, "to_user_id": user_a_id}
        ]
    })


def effective_green_mode(user: dict) -> bool:
    return user.get("green_mode", False) or user.get("charm_value", 0) < 20


def extract_province(location: str | None) -> str:
    if not location:
        return ""
    text = location.strip()
    for sep in ["省", "市", "-", " ", ",", "，", "/"]:
        if sep in text:
            return text.split(sep)[0].strip()
    return text


def match_zone(user: dict) -> str:
    zone = user.get("match_zone", "chat")
    return zone if zone in {"chat", "green"} else "chat"


def is_match_preference_compatible(source_user: dict, target_user: dict) -> bool:
    target_age = target_user.get("age")
    source_age = source_user.get("age")

    source_min = source_user.get("match_age_min", 18)
    source_max = source_user.get("match_age_max", 99)
    if target_age is not None and (target_age < source_min or target_age > source_max):
        return False

    source_gender_pref = source_user.get("match_gender_preference", "any")
    target_gender = target_user.get("gender", "secret")
    if source_gender_pref != "any" and target_gender != source_gender_pref:
        return False

    target_min = target_user.get("match_age_min", 18)
    target_max = target_user.get("match_age_max", 99)
    if source_age is not None and (source_age < target_min or source_age > target_max):
        return False

    target_gender_pref = target_user.get("match_gender_preference", "any")
    source_gender = source_user.get("gender", "secret")
    if target_gender_pref != "any" and source_gender != target_gender_pref:
        return False

    source_loc_pref = source_user.get("match_location_preference", "any")
    target_loc_pref = target_user.get("match_location_preference", "any")
    source_province = extract_province(source_user.get("location"))
    target_province = extract_province(target_user.get("location"))
    if source_loc_pref == "same_province" and source_province and target_province and source_province != target_province:
        return False
    if target_loc_pref == "same_province" and source_province and target_province and source_province != target_province:
        return False

    return True


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

    charm_value = user["charm_value"]
    if not check_feature_permission(charm_value, "match"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的魅力值不足，无法使用随机匹配功能"
        )

    today_key = get_today_key(user_id, "match")
    usage = await redis.get(today_key)
    usage_count = int(usage) if usage else 0
    limit = get_feature_limit(charm_value, "match")

    if usage_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"今日随机匹配次数已达上限 ({limit}次)"
        )

    use_preferences = bool(getattr(request, "use_preferences", False))
    if use_preferences and charm_value <= 200:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="魅力值需大于200，才可按陌生人设置定向匹配"
        )

    queue_key = f"match_queue:random:{match_zone(user)}:{'pref' if use_preferences else 'all'}"

    existing_waiting = await db["matches"].find_one(
        {"user_id": user_id, "status": "waiting", "queue": queue_key},
        sort=[("start_time", -1)]
    )
    if existing_waiting:
        waiting_users = await redis.lrange(queue_key, 0, -1)
        in_queue = False
        for waiting_user_str in waiting_users:
            waiting_user = json.loads(waiting_user_str)
            if (
                waiting_user.get("user_id") == user_id
                and waiting_user.get("match_id") == existing_waiting["id"]
            ):
                in_queue = True
                break

        if not in_queue:
            waiting_info = {
                "user_id": user_id,
                "match_id": existing_waiting["id"],
                "charm_value": charm_value,
                "joined_at": datetime.now().isoformat()
            }
            await redis.rpush(queue_key, json.dumps(waiting_info))

        return SuccessResponse(
            message="您已在匹配队列中，正在为您寻找匹配...",
            data={
                "match_id": existing_waiting["id"],
                "matched_user_id": None,
                "status": "waiting",
                "waiting_time": (datetime.now() - existing_waiting["start_time"]).total_seconds() if existing_waiting.get("start_time") else 0
            }
        )

    if use_preferences:
        await db["users"].update_one(
            {"id": user_id},
            {"$inc": {"charm_value": -10}, "$set": {"updated_at": datetime.now()}}
        )

    waiting_users = await redis.lrange(queue_key, 0, -1)

    matched_user = None
    for waiting_user_str in waiting_users:
        waiting_user = json.loads(waiting_user_str)
        if waiting_user["user_id"] == user_id:
            continue

        waiting_match = await db["matches"].find_one(
            {
                "id": waiting_user.get("match_id"),
                "user_id": waiting_user["user_id"],
                "status": "waiting",
                "queue": queue_key
            }
        )
        if not waiting_match:
            await redis.lrem(queue_key, 0, waiting_user_str)
            continue

        waiting_target_user = await db["users"].find_one({"id": waiting_user["user_id"]})
        if not waiting_target_user:
            await redis.lrem(queue_key, 0, waiting_user_str)
            continue

        if use_preferences and not is_match_preference_compatible(user, waiting_target_user):
            continue

        is_blocked = await db["blocks"].find_one({
            "$or": [
                {"user_id": user_id, "blocked_user_id": waiting_user["user_id"]},
                {"user_id": waiting_user["user_id"], "blocked_user_id": user_id}
            ]
        })

        if not is_blocked:
            matched_user = waiting_user
            await redis.lrem(queue_key, 0, waiting_user_str)
            break

    if matched_user:
        await reset_chat_state_on_rematch(db, user_id, matched_user["user_id"])

        match_id = str(uuid.uuid4())
        match_record = {
            "id": match_id,
            "user_id": user_id,
            "matched_user_id": matched_user["user_id"],
            "type": "random",
            "queue": queue_key,
            "status": "matched",
            "start_time": datetime.now(),
            "end_time": None
        }
        await db["matches"].insert_one(match_record)

        await db["matches"].update_one(
            {"id": matched_user["match_id"]},
            {"$set": {
                "matched_user_id": user_id,
                "status": "matched"
            }}
        )

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

    match_id = str(uuid.uuid4())
    waiting_info = {
        "user_id": user_id,
        "match_id": match_id,
        "charm_value": charm_value,
        "joined_at": datetime.now().isoformat()
    }
    await redis.rpush(queue_key, json.dumps(waiting_info))

    match_record = {
        "id": match_id,
        "user_id": user_id,
        "matched_user_id": None,
        "type": "random",
        "queue": queue_key,
        "status": "waiting",
        "start_time": datetime.now(),
        "end_time": None
    }
    await db["matches"].insert_one(match_record)

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

    charm_value = user["charm_value"]
    if not check_feature_permission(charm_value, "match"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的魅力值不足，无法使用捞个在线功能"
        )

    today_key = get_today_key(user_id, "pick_online")
    usage = await redis.get(today_key)
    usage_count = int(usage) if usage else 0
    # 按产品规则：捞个在线随机模式固定每日免费 10 次
    limit = DAILY_PICK_ONLINE_FREE_LIMIT
    use_preferences = bool(getattr(request, "use_preferences", False))
    free_exhausted = usage_count >= limit

    if (not use_preferences) and usage_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"今日捞个在线次数已达上限 ({limit}次)"
        )

    now_ts = int(time.time())
    min_ts = now_ts - ONLINE_WINDOW_SECONDS

    await redis.zremrangebyscore("online_users:last_seen", 0, min_ts - 1)
    online_users = await redis.zrangebyscore("online_users:last_seen", min_ts, now_ts)
    online_users = list(online_users)

    if not online_users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="暂无在线用户"
        )

    current_zone = match_zone(user)
    valid_users = []
    preferred_users = []
    for uid in online_users:
        uid_str = uid.decode() if isinstance(uid, bytes) else uid
        if uid_str == user_id:
            continue

        target_user = await db["users"].find_one({"id": uid_str})
        if target_user and target_user.get("allow_discovery", True):
            if match_zone(target_user) != current_zone:
                continue

            is_blocked = await db["blocks"].find_one({
                "$or": [
                    {"user_id": user_id, "blocked_user_id": uid_str},
                    {"user_id": uid_str, "blocked_user_id": user_id}
                ]
            })

            if not is_blocked:
                valid_users.append(target_user)
                if use_preferences and is_match_preference_compatible(user, target_user):
                    preferred_users.append(target_user)

    if not valid_users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="暂无符合条件的在线用户"
        )

    selection_pool = preferred_users if preferred_users else valid_users
    if user.get("gender") == "female":
        high_charm_users = [u for u in selection_pool if u["charm_value"] >= 100]
        selected_user = random.choice(high_charm_users) if high_charm_users else random.choice(selection_pool)
    else:
        selected_user = random.choice(selection_pool)

    await reset_chat_state_on_rematch(db, user_id, selected_user["id"])

    if use_preferences:
        await db["users"].update_one(
            {"id": user_id},
            {"$inc": {"charm_value": -DIRECTIONAL_CHARM_COST}, "$set": {"updated_at": datetime.now()}}
        )

    if not use_preferences:
        await redis.incr(today_key)
        await redis.expire(today_key, 86400)

    return SuccessResponse(
        message="捞取成功！",
        data={
            "user_id": selected_user["id"],
            "nickname": selected_user["nickname"],
            "avatar": selected_user.get("avatar"),
            "charm_value": selected_user["charm_value"],
            "charm_cost": DIRECTIONAL_CHARM_COST if use_preferences else 0,
            "free_exhausted": free_exhausted
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

    queue_keys = []
    async for key in redis.scan_iter(match="match_queue:random:*"):
        queue_keys.append(key.decode() if isinstance(key, bytes) else key)
    if not queue_keys:
        queue_keys = ["match_queue:random:green", "match_queue:random:chat", "match_queue:random:normal"]

    for queue_key in queue_keys:
        waiting_users = await redis.lrange(queue_key, 0, -1)
        for waiting_user_str in waiting_users:
            waiting_user = json.loads(waiting_user_str)
            if waiting_user["match_id"] == match_id and waiting_user["user_id"] == user_id:
                await redis.lrem(queue_key, 0, waiting_user_str)
                break

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
