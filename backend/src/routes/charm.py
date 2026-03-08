from fastapi import APIRouter, Depends, HTTPException, status
from src.database import get_mongodb, get_redis
from src.schemas import (
    SuccessResponse,
    ErrorResponse
)
from src.security import get_current_user
from src.utils import (
    get_charm_level,
    get_feature_limit,
    get_today_key,
    check_feature_permission
)
from datetime import datetime
import random


router = APIRouter()


@router.get("/info", response_model=SuccessResponse)
async def get_charm_info(
    user_id: str = Depends(get_current_user)
):
    """获取魅力值信息"""
    db = get_mongodb()
    redis = get_redis()

    user = await db["users"].find_one({"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    charm_value = user["charm_value"]

    level = get_charm_level(charm_value)

    permissions = {
        "chat": check_feature_permission(charm_value, "chat"),
        "match": check_feature_permission(charm_value, "match"),
        "throw_bottle": check_feature_permission(charm_value, "throw_bottle"),
        "pick_bottle": check_feature_permission(charm_value, "pick_bottle"),
        "send_file": check_feature_permission(charm_value, "send_file"),
        "edit_nickname": check_feature_permission(charm_value, "edit_nickname"),
        "custom_avatar": check_feature_permission(charm_value, "custom_avatar"),
        "publish_announcement": check_feature_permission(charm_value, "publish_announcement"),
        "edit_settings": check_feature_permission(charm_value, "edit_settings"),
        "virtual_chat": check_feature_permission(charm_value, "virtual_chat")
    }

    # 获取每日使用次数
    daily_usage = {}
    for feature in ["match", "pick_bottle", "throw_bottle", "pick_online"]:
        today_key = get_today_key(user_id, feature)
        usage = await redis.get(today_key)
        usage_count = int(usage) if usage else 0
        limit = get_feature_limit(charm_value, feature)
        daily_usage[feature] = {
            "used": usage_count,
            "limit": limit,
            "remaining": max(0, limit - usage_count)
        }

    return SuccessResponse(
        message="获取成功",
        data={
            "charm_value": charm_value,
            "level": level,
            "permissions": permissions,
            "daily_usage": daily_usage
        }
    )


@router.get("/history", response_model=SuccessResponse)
async def get_charm_history(
    page: int = 1,
    page_size: int = 20,
    user_id: str = Depends(get_current_user)
):
    """获取魅力值变更历史"""
    db = get_mongodb()

    skip = (page - 1) * page_size

    history = await db["charm_history"].find({
        "user_id": user_id
    }).sort("created_at", -1).skip(skip).limit(page_size).to_list(length=page_size)

    return SuccessResponse(
        message="获取成功",
        data={
            "history": history,
            "page": page,
            "page_size": page_size,
            "total": await db["charm_history"].count_documents({"user_id": user_id})
        }
    )


@router.post("/daily-checkin", response_model=SuccessResponse)
async def daily_checkin(
    user_id: str = Depends(get_current_user)
):
    """每日签到获取魅力值"""
    db = get_mongodb()

    today = datetime.now().strftime("%Y-%m-%d")

    # 检查是否已签到
    existing_checkin = await db["charm_history"].find_one({
        "user_id": user_id,
        "action": "login",
        "created_at": {"$gte": datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)}
    })

    if existing_checkin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="今日已签到"
        )

    # 增加魅力值
    reward = 5
    await db["users"].update_one(
        {"id": user_id},
        {"$inc": {"charm_value": reward}, "$set": {"updated_at": datetime.now()}}
    )

    # 记录变更历史
    await db["charm_history"].insert_one({
        "id": str(datetime.now().timestamp()),
        "user_id": user_id,
        "action": "login",
        "change_value": reward,
        "description": "每日登录奖励",
        "new_value": (await db["users"].find_one({"id": user_id}))["charm_value"],
        "created_at": datetime.now()
    })

    return SuccessResponse(
        message=f"签到成功！获得 {reward} 魅力值",
        data={
            "reward": reward,
            "current_charm_value": (await db["users"].find_one({"id": user_id}))["charm_value"]
        }
    )


@router.get("/privileges", response_model=SuccessResponse)
async def get_privileges(
    user_id: str = Depends(get_current_user)
):
    """获取权限说明"""
    db = get_mongodb()

    user = await db["users"].find_one({"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    charm_value = user["charm_value"]

    privileges = {
        "chat": {
            "required": 0,
            "current": charm_value,
            "unlocked": charm_value >= 0,
            "description": "基础聊天功能"
        },
        "match": {
            "required": 0,
            "current": charm_value,
            "unlocked": charm_value >= 0,
            "description": "随机匹配功能"
        },
        "throw_bottle": {
            "required": 50,
            "current": charm_value,
            "unlocked": charm_value >= 50,
            "description": "扔瓶子功能"
        },
        "pick_bottle": {
            "required": 50,
            "current": charm_value,
            "unlocked": charm_value >= 50,
            "description": "捞瓶子功能"
        },
        "send_file": {
            "required": 35,
            "current": charm_value,
            "unlocked": charm_value >= 35,
            "description": "发送文件功能"
        },
        "edit_nickname": {
            "required": 35,
            "current": charm_value,
            "unlocked": charm_value >= 35,
            "description": "修改昵称功能"
        },
        "custom_avatar": {
            "required": 50,
            "current": charm_value,
            "unlocked": charm_value >= 50,
            "description": "自定义头像功能"
        },
        "publish_announcement": {
            "required": 100,
            "current": charm_value,
            "unlocked": charm_value >= 100,
            "description": "发布寻人公告功能"
        },
        "edit_settings": {
            "required": 200,
            "current": charm_value,
            "unlocked": charm_value >= 200,
            "description": "高级设置功能"
        },
        "virtual_chat": {
            "required": 0,
            "current": charm_value,
            "unlocked": charm_value >= 0,
            "description": "虚拟人物对话功能"
        }
    }

    return SuccessResponse(
        message="获取成功",
        data={
            "privileges": privileges
        }
    )
