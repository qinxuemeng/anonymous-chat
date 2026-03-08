from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.responses import JSONResponse
from src.database import get_mongodb, get_redis
from src.schemas import (
    UserRegister,
    UserLogin,
    Token,
    UserResponse,
    SuccessResponse,
    ErrorResponse,
)
from src.security import get_password_hash, verify_password, create_access_token, get_current_user
from src.utils import generate_nickname
from datetime import datetime, timedelta
import uuid
import re


router = APIRouter()


@router.post("/register", response_model=SuccessResponse, responses={400: {"model": ErrorResponse}})
async def register_user(user_data: UserRegister = Body(...)):
    """用户注册"""
    db = get_mongodb()

    # 检查用户名格式
    if not re.match(r"^[a-zA-Z0-9_\u4e00-\u9fa5]+$", user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名只能包含字母、数字、下划线和中文"
        )

    # 检查用户名是否已存在
    existing_user = await db["users"].find_one({"username": user_data.username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    # 检查邮箱是否已存在（如果提供）
    if user_data.email:
        existing_email = await db["users"].find_one({"email": user_data.email})
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被注册"
            )

    # 检查手机号是否已存在（如果提供）
    if user_data.phone:
        existing_phone = await db["users"].find_one({"phone": user_data.phone})
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号已被注册"
            )

    # 创建新用户
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user_data.password)

    user = {
        "id": user_id,
        "username": user_data.username,
        "password": hashed_password,
        "email": user_data.email,
        "phone": user_data.phone,
        "avatar": None,
        "nickname": generate_nickname(),
        "gender": "secret",
        "age": None,
        "location": None,
        "tags": [],
        "charm_value": 500,
        "allow_discovery": True,
        "green_mode": False,
        "night_mode": False,
        "notification_sound": True,
        "keep_logged_in": False,
        "english_mode": False,
        "show_location": False,
        "match_gender_preference": "any",
        "match_location_preference": "any",
        "match_age_min": 18,
        "match_age_max": 70,
        "match_zone": "chat",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "last_login_at": datetime.now(),
        "is_active": True
    }

    await db["users"].insert_one(user)

    # 创建访问令牌
    access_token = create_access_token(data={"sub": user_id})

    return SuccessResponse(
        message="注册成功",
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user_id,
                "username": user["username"],
                "nickname": user["nickname"],
                "avatar": user["avatar"],
                "gender": user["gender"],
                "age": user["age"],
                "charm_value": user["charm_value"],
                "allow_discovery": user["allow_discovery"],
                "green_mode": user["green_mode"],
                "night_mode": user["night_mode"],
                "notification_sound": user["notification_sound"],
                "keep_logged_in": user["keep_logged_in"],
                "english_mode": user["english_mode"],
                "show_location": user["show_location"],
                "match_gender_preference": user.get("match_gender_preference", "any"),
                "match_location_preference": user.get("match_location_preference", "any"),
                "match_age_min": user.get("match_age_min", 18),
                "match_age_max": user.get("match_age_max", 70),
                "match_zone": user.get("match_zone", "chat"),
                "created_at": user["created_at"]
            }
        }
    )


@router.post("/login", response_model=SuccessResponse, responses={401: {"model": ErrorResponse}})
async def login_user(login_data: UserLogin = Body(...)):
    """用户登录"""
    db = get_mongodb()

    # 查找用户
    user = await db["users"].find_one({"username": login_data.username})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 验证密码
    if not verify_password(login_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 更新最后登录时间
    await db["users"].update_one(
        {"id": user["id"]},
        {"$set": {"last_login_at": datetime.now(), "updated_at": datetime.now()}}
    )

    # 每日首次进入平台自动 +5 魅力值
    day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    existing_reward = await db["charm_history"].find_one({
        "user_id": user["id"],
        "action": "login",
        "created_at": {"$gte": day_start}
    })
    if not existing_reward:
        reward = 5
        await db["users"].update_one(
            {"id": user["id"]},
            {"$inc": {"charm_value": reward}, "$set": {"updated_at": datetime.now()}}
        )
        refreshed = await db["users"].find_one({"id": user["id"]})
        await db["charm_history"].insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "action": "login",
            "change_value": reward,
            "description": "每日进入平台奖励",
            "new_value": refreshed["charm_value"],
            "created_at": datetime.now()
        })
        user = refreshed
    else:
        user = await db["users"].find_one({"id": user["id"]})

    # 创建访问令牌
    access_token = create_access_token(data={"sub": user["id"]})

    return SuccessResponse(
        message="登录成功",
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "nickname": user["nickname"],
                "avatar": user["avatar"],
                "gender": user["gender"],
                "age": user["age"],
                "charm_value": user["charm_value"],
                "allow_discovery": user["allow_discovery"],
                "green_mode": user["green_mode"],
                "night_mode": user["night_mode"],
                "notification_sound": user["notification_sound"],
                "keep_logged_in": user["keep_logged_in"],
                "english_mode": user["english_mode"],
                "show_location": user["show_location"],
                "match_gender_preference": user.get("match_gender_preference", "any"),
                "match_location_preference": user.get("match_location_preference", "any"),
                "match_age_min": user.get("match_age_min", 18),
                "match_age_max": user.get("match_age_max", 70),
                "match_zone": user.get("match_zone", "chat"),
                "created_at": user["created_at"]
            }
        }
    )


@router.get("/profile", response_model=SuccessResponse)
async def get_profile(user_id: str = Depends(get_current_user)):
    """获取用户资料"""
    db = get_mongodb()

    user = await db["users"].find_one({"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return SuccessResponse(
        message="获取成功",
        data={
            "id": user["id"],
            "username": user["username"],
            "nickname": user["nickname"],
            "avatar": user["avatar"],
            "gender": user["gender"],
            "age": user["age"],
            "charm_value": user["charm_value"],
            "allow_discovery": user["allow_discovery"],
            "green_mode": user["green_mode"],
            "night_mode": user["night_mode"],
            "notification_sound": user["notification_sound"],
            "keep_logged_in": user["keep_logged_in"],
            "english_mode": user["english_mode"],
            "show_location": user["show_location"],
            "match_gender_preference": user.get("match_gender_preference", "any"),
            "match_location_preference": user.get("match_location_preference", "any"),
            "match_age_min": user.get("match_age_min", 18),
            "match_age_max": user.get("match_age_max", 70),
            "match_zone": user.get("match_zone", "chat"),
            "tags": user.get("tags", []),
            "created_at": user["created_at"]
        }
    )


@router.post("/logout", response_model=SuccessResponse)
async def logout_user(user_id: str = Depends(get_current_user)):
    """用户登出，清理在线状态。"""
    redis = get_redis()
    await redis.zrem("online_users:last_seen", user_id)
    await redis.srem("online_users", user_id)
    return SuccessResponse(message="已退出登录")
