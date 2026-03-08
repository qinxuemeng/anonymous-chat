from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from src.database import get_mongodb, get_redis
from src.schemas import (
    UserUpdate,
    UserSettingsUpdate,
    CharmValueResponse,
    SuccessResponse,
    ErrorResponse
)
from src.security import get_current_user
from src.utils import validate_image, save_uploaded_file
from datetime import datetime
import os
import json


router = APIRouter()


@router.put("/profile", response_model=SuccessResponse)
async def update_profile(
    user_data: UserUpdate,
    user_id: str = Depends(get_current_user)
):
    """更新用户资料"""
    db = get_mongodb()

    user = await db["users"].find_one({"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    update_data = user_data.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.now()

    await db["users"].update_one(
        {"id": user_id},
        {"$set": update_data}
    )

    # 获取更新后的用户信息
    updated_user = await db["users"].find_one({"id": user_id})

    return SuccessResponse(
        message="资料更新成功",
        data={
            "id": updated_user["id"],
            "username": updated_user["username"],
            "nickname": updated_user["nickname"],
            "avatar": updated_user["avatar"],
            "gender": updated_user["gender"],
            "age": updated_user["age"],
            "charm_value": updated_user["charm_value"],
            "tags": updated_user.get("tags", []),
            "created_at": updated_user["created_at"],
            "updated_at": updated_user["updated_at"]
        }
    )


@router.put("/settings", response_model=SuccessResponse)
async def update_settings(
    settings: UserSettingsUpdate,
    user_id: str = Depends(get_current_user)
):
    """更新用户设置"""
    db = get_mongodb()

    user = await db["users"].find_one({"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    update_data = settings.dict(exclude_unset=True)
    charm_value = user.get("charm_value", 0)
    allowed_gender_preferences = {"any", "male", "female"}
    allowed_location_preferences = {"any", "same_province"}
    allowed_zones = {"chat", "green"}

    if "match_gender_preference" in update_data and update_data["match_gender_preference"] not in allowed_gender_preferences:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="匹配性别设置无效"
        )

    if "match_location_preference" in update_data and update_data["match_location_preference"] not in allowed_location_preferences:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="匹配位置设置无效"
        )

    if "match_zone" in update_data and update_data["match_zone"] not in allowed_zones:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="分区设置无效"
        )

    min_age = update_data.get("match_age_min", user.get("match_age_min", 18))
    max_age = update_data.get("match_age_max", user.get("match_age_max", 70))
    if min_age is not None and max_age is not None:
        if min_age < 18 or max_age > 70 or min_age > max_age:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="年龄区间设置无效"
            )

    # 魅力值<20 强制绿色模式
    if charm_value < 20:
        update_data["green_mode"] = True

    effective_green = update_data.get("green_mode", user.get("green_mode", False)) or charm_value < 20
    target_zone = update_data.get("match_zone", user.get("match_zone", "chat"))
    if target_zone == "green" and not effective_green:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="清流分区仅支持绿色模式用户"
        )

    if not update_data:
        return SuccessResponse(message="无可更新设置")

    update_data["updated_at"] = datetime.now()

    await db["users"].update_one(
        {"id": user_id},
        {"$set": update_data}
    )

    return SuccessResponse(
        message="设置更新成功"
    )


@router.delete("/account", response_model=SuccessResponse)
async def delete_account(
    user_id: str = Depends(get_current_user)
):
    """注销账号"""
    db = get_mongodb()
    redis = get_redis()

    user = await db["users"].find_one({"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    await db["users"].delete_one({"id": user_id})
    await db["chats"].delete_many({"$or": [{"from_user_id": user_id}, {"to_user_id": user_id}]})
    await db["matches"].delete_many({"$or": [{"user_id": user_id}, {"matched_user_id": user_id}]})
    await db["bottles"].delete_many({"user_id": user_id})
    await db["bottle_picks"].delete_many({"picker_user_id": user_id})
    await db["bottle_replies"].delete_many({"$or": [{"from_user_id": user_id}, {"to_user_id": user_id}]})
    await db["announcements"].delete_many({"user_id": user_id})
    await db["announcement_claims"].delete_many({"claimant_user_id": user_id})
    await db["blocks"].delete_many({"$or": [{"user_id": user_id}, {"blocked_user_id": user_id}]})
    await db["reports"].delete_many({"$or": [{"user_id": user_id}, {"target_user_id": user_id}]})
    await db["charm_history"].delete_many({"user_id": user_id})

    await redis.zrem("online_users:last_seen", user_id)
    await redis.srem("online_users", user_id)
    for queue_key in ["match_queue:random", "match_queue:random:green", "match_queue:random:chat", "match_queue:random:normal"]:
        waiting_users = await redis.lrange(queue_key, 0, -1)
        for waiting_user_str in waiting_users:
            waiting_user = json.loads(waiting_user_str)
            if waiting_user.get("user_id") == user_id:
                await redis.lrem(queue_key, 0, waiting_user_str)

    async for key in redis.scan_iter(match=f"usage:{user_id}:*"):
        await redis.delete(key)

    return SuccessResponse(message="账号已注销")


@router.get("/discover/{target_user_id}", response_model=SuccessResponse)
async def get_discover_user(
    target_user_id: str,
    user_id: str = Depends(get_current_user)
):
    """获取发现页使用的陌生人公开信息"""
    db = get_mongodb()

    if target_user_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能查看自己"
        )

    target_user = await db["users"].find_one({"id": target_user_id})
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    is_blocked = await db["blocks"].find_one({
        "$or": [
            {"user_id": user_id, "blocked_user_id": target_user_id},
            {"user_id": target_user_id, "blocked_user_id": user_id}
        ]
    })
    if is_blocked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不可被发现"
        )

    gender_map = {"male": "男", "female": "女", "secret": "保密"}
    gender_value = gender_map.get(target_user.get("gender", "secret"), "保密")
    city = target_user.get("location") if target_user.get("show_location", False) else ""

    return SuccessResponse(
        message="获取成功",
        data={
            "id": target_user["id"],
            "nickname": target_user.get("nickname") or "匿名用户",
            "avatar": target_user.get("avatar"),
            "charm_value": target_user.get("charm_value", 0),
            "gender": gender_value,
            "age": target_user.get("age"),
            "city": city,
            "tags": target_user.get("tags", [])
        }
    )


@router.post("/avatar", response_model=SuccessResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """上传头像"""
    db = get_mongodb()

    user = await db["users"].find_one({"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 验证文件类型
    if not validate_image(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只允许上传图片文件"
        )

    # 保存文件
    file_path = await save_uploaded_file(file, "avatars")
    avatar_url = f"/uploads/avatars/{os.path.basename(file_path)}"

    await db["users"].update_one(
        {"id": user_id},
        {"$set": {"avatar": avatar_url, "updated_at": datetime.now()}}
    )

    return SuccessResponse(
        message="头像上传成功",
        data={"avatar": avatar_url}
    )


@router.get("/charm", response_model=SuccessResponse)
async def get_charm_info(
    user_id: str = Depends(get_current_user)
):
    """获取魅力值信息"""
    db = get_mongodb()

    user = await db["users"].find_one({"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    charm_value = user["charm_value"]

    # 计算用户等级
    if charm_value < 20:
        level = "受限"
        permissions = {
            "chat": True,
            "match": True,
            "throw_bottle": False,
            "pick_bottle": False,
            "send_file": False,
            "edit_nickname": False,
            "custom_avatar": False,
            "publish_announcement": False,
            "edit_settings": False,
            "virtual_chat": True
        }
    elif charm_value < 35:
        level = "观察"
        permissions = {
            "chat": True,
            "match": True,
            "throw_bottle": False,
            "pick_bottle": False,
            "send_file": False,
            "edit_nickname": False,
            "custom_avatar": False,
            "publish_announcement": False,
            "edit_settings": False,
            "virtual_chat": True
        }
    elif charm_value < 50:
        level = "进阶"
        permissions = {
            "chat": True,
            "match": True,
            "throw_bottle": False,
            "pick_bottle": False,
            "send_file": True,
            "edit_nickname": True,
            "custom_avatar": False,
            "publish_announcement": False,
            "edit_settings": False,
            "virtual_chat": True
        }
    elif charm_value < 100:
        level = "活跃"
        permissions = {
            "chat": True,
            "match": True,
            "throw_bottle": True,
            "pick_bottle": True,
            "send_file": True,
            "edit_nickname": True,
            "custom_avatar": True,
            "publish_announcement": False,
            "edit_settings": False,
            "virtual_chat": True
        }
    elif charm_value < 200:
        level = "优质"
        permissions = {
            "chat": True,
            "match": True,
            "throw_bottle": True,
            "pick_bottle": True,
            "send_file": True,
            "edit_nickname": True,
            "custom_avatar": True,
            "publish_announcement": True,
            "edit_settings": False,
            "virtual_chat": True
        }
    else:
        level = "核心"
        permissions = {
            "chat": True,
            "match": True,
            "throw_bottle": True,
            "pick_bottle": True,
            "send_file": True,
            "edit_nickname": True,
            "custom_avatar": True,
            "publish_announcement": True,
            "edit_settings": True,
            "virtual_chat": True
        }

    return SuccessResponse(
        message="获取成功",
        data={
            "charm_value": charm_value,
            "level": level,
            "permissions": permissions,
            "daily_usage": {
                "match": await get_daily_usage(db, user_id, "match"),
                "pick_bottle": await get_daily_usage(db, user_id, "pick_bottle"),
                "throw_bottle": await get_daily_usage(db, user_id, "throw_bottle"),
                "pick_online": await get_daily_usage(db, user_id, "pick_online")
            }
        }
    )


async def get_daily_usage(db, user_id, feature):
    """获取每日使用次数"""
    # 这里可以从数据库查询用户的每日使用次数
    # 现在暂时返回默认值
    return 0
