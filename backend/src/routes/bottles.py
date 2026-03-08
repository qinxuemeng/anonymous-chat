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

    # 检查权限
    charm_value = user["charm_value"]
    if not check_feature_permission(charm_value, "throw_bottle"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的魅力值不足，无法使用扔瓶子功能（需要≥50）"
        )

    # 检查每日使用次数
    today_key = get_today_key(user_id, "throw_bottle")
    usage = await redis.get(today_key)
    usage_count = int(usage) if usage else 0
    limit = get_feature_limit(charm_value, "throw_bottle")

    if usage_count >= limit:
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
        "max_pick_count": 10,
        "status": "active",
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=24)
    }

    await db["bottles"].insert_one(bottle)

    # 加入 Redis 瓶子池
    await redis.sadd("bottle_pool", bottle_id)

    # 增加今日使用次数
    await redis.incr(today_key)
    await redis.expire(today_key, 86400)

    return SuccessResponse(
        message="瓶子已投入大海！",
        data={
            "id": bottle_id,
            "content": content,
            "images": bottle_data.images or [],
            "status": "active",
            "created_at": bottle["created_at"],
            "expires_at": bottle["expires_at"]
        }
    )


@router.post("/pick", response_model=SuccessResponse)
async def pick_bottle(
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

    # 检查权限
    charm_value = user["charm_value"]
    if not check_feature_permission(charm_value, "pick_bottle"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的魅力值不足，无法使用捞瓶子功能（需要≥50）"
        )

    # 检查每日使用次数
    today_key = get_today_key(user_id, "pick_bottle")
    usage = await redis.get(today_key)
    usage_count = int(usage) if usage else 0
    limit = get_feature_limit(charm_value, "pick_bottle")

    if usage_count >= limit:
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

    # 随机选择一个瓶子
    selected_bottle_id = random.choice(bottle_ids)

    # 获取瓶子详情
    bottle = await db["bottles"].find_one({
        "id": selected_bottle_id,
        "status": "active"
    })

    if not bottle or bottle["expires_at"] < datetime.now():
        # 移除过期或不存在的瓶子
        await redis.srem("bottle_pool", selected_bottle_id)
        if bottle:
            await db["bottles"].update_one(
                {"id": selected_bottle_id},
                {"$set": {"status": "expired"}}
            )
        return await pick_bottle(user_id)

    # 更新瓶子捞取次数
    new_pick_count = bottle["pick_count"] + 1
    status = "active"

    if new_pick_count >= bottle["max_pick_count"]:
        status = "expired"
        await redis.srem("bottle_pool", selected_bottle_id)

    await db["bottles"].update_one(
        {"id": selected_bottle_id},
        {"$set": {"pick_count": new_pick_count, "status": status}}
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
    await redis.incr(today_key)
    await redis.expire(today_key, 86400)

    # 获取瓶子作者信息
    author = await db["users"].find_one({"id": bottle["user_id"]})

    return SuccessResponse(
        message="捞到瓶子了！",
        data={
            "bottle_id": bottle["id"],
            "content": bottle["content"],
            "images": bottle["images"],
            "author_nickname": author["nickname"] if author else "匿名",
            "author_avatar": author.get("avatar") if author else None,
            "created_at": bottle["created_at"]
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
