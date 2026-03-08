from fastapi import APIRouter, Depends, HTTPException, status, Body
from src.database import get_mongodb, get_redis
from src.schemas import (
    BottleCreate,
    BottleResponse,
    BottleReply,
    SuccessResponse,
    ErrorResponse
)
from src.security import get_current_user
from src.utils import (
    check_feature_permission,
    get_feature_limit,
    get_today_key,
    filter_sensitive_words
)
from datetime import datetime, timedelta
import uuid
import random


router = APIRouter()
DAILY_THROW_LIMIT = 20
DAILY_PICK_BOTTLE_LIMIT = 20
DIRECTIONAL_CHARM_COST = 5


async def reset_chat_state_on_bottle_connect(db, user_a_id: str, user_b_id: str):
    """通过捞瓶子建立会话时，重置双方旧会话状态。"""
    if user_a_id == user_b_id:
        return
    await db["chats"].delete_many({
        "$or": [
            {"from_user_id": user_a_id, "to_user_id": user_b_id},
            {"from_user_id": user_b_id, "to_user_id": user_a_id}
        ]
    })


def extract_province(location: str | None) -> str:
    if not location:
        return ""
    text = location.strip()
    for sep in ["省", "市", "-", " ", ",", "，", "/"]:
        if sep in text:
            return text.split(sep)[0].strip()
    return text


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


def is_user_matched_by_target_preferences(picker_user: dict, target_preferences: dict) -> bool:
    gender_pref = target_preferences.get("gender", "any")
    if gender_pref != "any" and picker_user.get("gender", "secret") != gender_pref:
        return False

    age = picker_user.get("age")
    age_min = int(target_preferences.get("age_min", 18))
    age_max = int(target_preferences.get("age_max", 99))
    if age is not None and (age < age_min or age > age_max):
        return False

    loc_pref = target_preferences.get("location", "any")
    if loc_pref == "same_province":
        source_province = target_preferences.get("source_province", "")
        picker_province = extract_province(picker_user.get("location"))
        if source_province and picker_province and source_province != picker_province:
            return False

    return True


@router.post("/throw", response_model=SuccessResponse)
async def throw_bottle(
    bottle_data: BottleCreate,
    user_id: str = Depends(get_current_user)
):
    """扔瓶子"""
    db = get_mongodb()
    redis = get_redis()

    user = await db["users"].find_one({"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 扔瓶子不做魅力值门槛限制
    charm_value = user["charm_value"]

    # 检查每日使用次数
    today_key = get_today_key(user_id, "throw_bottle")
    usage = await redis.get(today_key)
    usage_count = int(usage) if usage else 0
    limit = DAILY_THROW_LIMIT
    free_exhausted = usage_count >= limit

    if (not bottle_data.use_preferences) and usage_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"今日扔瓶子次数已达上限 ({limit}次)"
        )

    # 内容过滤
    content = filter_sensitive_words(bottle_data.content)

    # 创建瓶子
    bottle_id = str(uuid.uuid4())
    bottle = {
        "id": bottle_id,
        "user_id": user_id,
        "content": content,
        "images": bottle_data.images or [],
        "pick_count": 0,
        "max_pick_count": max(1, min(int(bottle_data.max_pick_count or 5), 20)),
        "status": "active",
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=24),
        "target_preferences": None
    }

    if bottle_data.use_preferences:
        bottle["target_preferences"] = {
            "gender": user.get("match_gender_preference", "any"),
            "location": user.get("match_location_preference", "any"),
            "age_min": int(user.get("match_age_min", 18)),
            "age_max": int(user.get("match_age_max", 99)),
            "source_province": extract_province(user.get("location"))
        }

    await db["bottles"].insert_one(bottle)

    # 加入 Redis 瓶子池
    await redis.sadd("bottle_pool", bottle_id)

    # 增加今日使用次数
    if not bottle_data.use_preferences:
        await redis.incr(today_key)
        await redis.expire(today_key, 86400)
    else:
        await db["users"].update_one(
            {"id": user_id},
            {"$inc": {"charm_value": -DIRECTIONAL_CHARM_COST}, "$set": {"updated_at": datetime.now()}}
        )

    return SuccessResponse(
        message="瓶子已投入大海！",
        data={
            "id": bottle_id,
            "content": content,
            "images": bottle_data.images or [],
            "status": "active",
            "created_at": bottle["created_at"],
            "expires_at": bottle["expires_at"],
            "charm_cost": DIRECTIONAL_CHARM_COST if bottle_data.use_preferences else 0,
            "free_exhausted": free_exhausted
        }
    )


@router.post("/pick", response_model=SuccessResponse)
async def pick_bottle(
    payload: dict | None = Body(default=None),
    user_id: str = Depends(get_current_user)
):
    """捞瓶子"""
    db = get_mongodb()
    redis = get_redis()

    user = await db["users"].find_one({"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 捞瓶子不做魅力值门槛限制
    charm_value = user["charm_value"]

    # 检查每日使用次数
    today_key = get_today_key(user_id, "pick_bottle")
    usage = await redis.get(today_key)
    usage_count = int(usage) if usage else 0
    limit = DAILY_PICK_BOTTLE_LIMIT
    use_preferences = bool((payload or {}).get("use_preferences", False))
    free_exhausted = usage_count >= limit

    if (not use_preferences) and usage_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"今日捞瓶子次数已达上限 ({limit}次)"
        )

    # 从瓶子池中随机捞取
    bottle_ids = await redis.smembers("bottle_pool")
    bottle_ids = [bid.decode() if isinstance(bid, bytes) else bid for bid in bottle_ids]

    if not bottle_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="大海空空如也，稍后再试试吧！"
        )

    now = datetime.now()
    bottles = await db["bottles"].find({
        "id": {"$in": bottle_ids},
        "status": "active",
        "expires_at": {"$gte": now},
        "user_id": {"$ne": user_id}
    }).to_list(length=None)

    # 先按扔瓶子时的定向配置过滤可见瓶子
    visible_bottles = []
    for b in bottles:
        target_preferences = b.get("target_preferences")
        if target_preferences and not is_user_matched_by_target_preferences(user, target_preferences):
            continue
        visible_bottles.append(b)
    bottles = visible_bottles

    if not bottles:
        # 清理已过期瓶子，避免脏数据影响后续捞取
        expired = await db["bottles"].find({
            "id": {"$in": bottle_ids},
            "expires_at": {"$lt": now},
            "status": "active"
        }).to_list(length=None)
        for item in expired:
            await db["bottles"].update_one({"id": item["id"]}, {"$set": {"status": "expired"}})
            await redis.srem("bottle_pool", item["id"])
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="暂无可捞取的他人瓶子，请稍后再试"
        )

    author_cache = {}
    preferred_bottles = []
    if use_preferences:
        for b in bottles:
            author_id = b["user_id"]
            if author_id not in author_cache:
                author_cache[author_id] = await db["users"].find_one({"id": author_id})
            author = author_cache.get(author_id)
            if author and is_match_preference_compatible(user, author):
                preferred_bottles.append(b)

    selection_pool = preferred_bottles if preferred_bottles else bottles

    # 随机选择一个瓶子（>200优先定向，无结果则随机）
    bottle = random.choice(selection_pool)
    selected_bottle_id = bottle["id"]

    # 更新瓶子捞取次数
    new_pick_count = bottle["pick_count"] + 1
    bottle_status = "active"

    if new_pick_count >= bottle["max_pick_count"]:
        bottle_status = "expired"
        await redis.srem("bottle_pool", selected_bottle_id)

    await db["bottles"].update_one(
        {"id": selected_bottle_id},
        {"$set": {"pick_count": new_pick_count, "status": bottle_status}}
    )

    # 记录捞取记录
    pick_record = {
        "id": str(uuid.uuid4()),
        "bottle_id": selected_bottle_id,
        "picker_user_id": user_id,
        "picked_at": datetime.now()
    }
    await db["bottle_picks"].insert_one(pick_record)

    # 增加今日使用次数
    if not use_preferences:
        await redis.incr(today_key)
        await redis.expire(today_key, 86400)

    # 捞瓶子每次成功扣 5 魅力值
    await db["users"].update_one(
        {"id": user_id},
        {"$inc": {"charm_value": -5}, "$set": {"updated_at": datetime.now()}}
    )

    # 获取瓶子作者信息
    author = author_cache.get(bottle["user_id"]) if use_preferences else None
    if not author:
        author = await db["users"].find_one({"id": bottle["user_id"]})
    if author:
        await reset_chat_state_on_bottle_connect(db, user_id, author["id"])

    if use_preferences:
        await db["users"].update_one(
            {"id": user_id},
            {"$inc": {"charm_value": -DIRECTIONAL_CHARM_COST}, "$set": {"updated_at": datetime.now()}}
        )

    return SuccessResponse(
        message="捞到瓶子了！",
        data={
            "bottle_id": bottle["id"],
            "content": bottle["content"],
            "images": bottle["images"],
            "author_id": author["id"] if author else None,
            "author_nickname": author["nickname"] if author else "匿名",
            "author_avatar": author.get("avatar") if author else None,
            "author_gender": author.get("gender", "secret") if author else "secret",
            "created_at": bottle["created_at"],
            "charm_cost": DIRECTIONAL_CHARM_COST if use_preferences else 0,
            "free_exhausted": free_exhausted
        }
    )


@router.post("/reply", response_model=SuccessResponse)
async def reply_bottle(
    reply_data: BottleReply,
    user_id: str = Depends(get_current_user)
):
    """回复瓶子"""
    db = get_mongodb()

    # 获取瓶子
    bottle = await db["bottles"].find_one({"id": reply_data.bottle_id})
    if not bottle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="瓶子不存在"
        )

    # 创建回复
    reply_id = str(uuid.uuid4())
    reply = {
        "id": reply_id,
        "bottle_id": reply_data.bottle_id,
        "from_user_id": user_id,
        "to_user_id": bottle["user_id"],
        "content": filter_sensitive_words(reply_data.content),
        "created_at": datetime.now()
    }

    await db["bottle_replies"].insert_one(reply)

    return SuccessResponse(
        message="回复成功！",
        data={
            "id": reply_id,
            "content": reply["content"],
            "created_at": reply["created_at"]
        }
    )


@router.post("/withdraw", response_model=SuccessResponse)
async def withdraw_bottle(
    bottle_id: str = Body(..., embed=True),
    user_id: str = Depends(get_current_user)
):
    """撤回瓶子"""
    db = get_mongodb()
    redis = get_redis()

    # 获取瓶子
    bottle = await db["bottles"].find_one({"id": bottle_id})
    if not bottle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="瓶子不存在"
        )

    if bottle["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能撤回自己的瓶子"
        )

    if bottle["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该瓶子无法撤回"
        )

    # 更新状态
    await db["bottles"].update_one(
        {"id": bottle_id},
        {"$set": {"status": "withdrawn"}}
    )

    # 从瓶子池中移除
    await redis.srem("bottle_pool", bottle_id)

    return SuccessResponse(message="瓶子已撤回")


@router.get("/my", response_model=SuccessResponse)
async def get_my_bottles(
    page: int = 1,
    page_size: int = 20,
    user_id: str = Depends(get_current_user)
):
    """获取我的瓶子"""
    db = get_mongodb()

    skip = (page - 1) * page_size

    bottles = await db["bottles"].find({
        "user_id": user_id
    }).sort("created_at", -1).skip(skip).limit(page_size).to_list(length=page_size)

    return SuccessResponse(
        message="获取成功",
        data={
            "bottles": bottles,
            "page": page,
            "page_size": page_size,
            "total": await db["bottles"].count_documents({"user_id": user_id})
        }
    )
