from datetime import datetime, timedelta
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Body

from src.config import settings
from src.database import get_mongodb, get_redis
from src.schemas import SuccessResponse
from src.security import get_current_admin, get_password_hash
from src.utils import get_sensitive_words, set_sensitive_words


router = APIRouter()


async def ensure_superadmin_account(db):
    now = datetime.now()
    admin = await db["users"].find_one({"username": settings.admin_username})
    if admin:
        if admin.get("role") != "admin":
            await db["users"].update_one(
                {"id": admin["id"]},
                {"$set": {"role": "admin", "updated_at": now}}
            )
        return

    admin_id = str(uuid.uuid4())
    await db["users"].insert_one({
        "id": admin_id,
        "username": settings.admin_username,
        "password": get_password_hash(settings.admin_init_password),
        "email": None,
        "phone": None,
        "avatar": None,
        "nickname": "超级管理员",
        "gender": "secret",
        "age": None,
        "location": None,
        "tags": ["管理员"],
        "role": "admin",
        "charm_value": 99999,
        "allow_discovery": False,
        "green_mode": False,
        "night_mode": False,
        "notification_sound": True,
        "keep_logged_in": True,
        "english_mode": False,
        "show_location": False,
        "match_gender_preference": "any",
        "match_location_preference": "any",
        "match_age_min": 18,
        "match_age_max": 70,
        "match_zone": "chat",
        "created_at": now,
        "updated_at": now,
        "last_login_at": now,
        "is_active": True
    })


async def load_sensitive_words_from_db(db):
    cfg = await db["system_configs"].find_one({"key": "green_sensitive_words"})
    if cfg and isinstance(cfg.get("words"), list):
        set_sensitive_words(cfg["words"])
    else:
        await db["system_configs"].update_one(
            {"key": "green_sensitive_words"},
            {"$setOnInsert": {"key": "green_sensitive_words", "words": get_sensitive_words(), "updated_at": datetime.now()}},
            upsert=True
        )


async def bootstrap_admin_data():
    db = get_mongodb()
    await ensure_superadmin_account(db)
    await load_sensitive_words_from_db(db)


@router.get("/me", response_model=SuccessResponse)
async def admin_me(admin_user_id: str = Depends(get_current_admin)):
    db = get_mongodb()
    user = await db["users"].find_one({"id": admin_user_id})
    return SuccessResponse(message="获取成功", data={
        "id": user["id"],
        "username": user.get("username"),
        "nickname": user.get("nickname"),
        "role": user.get("role", "user")
    })


@router.get("/dashboard", response_model=SuccessResponse)
async def admin_dashboard(_: str = Depends(get_current_admin)):
    db = get_mongodb()
    redis = get_redis()

    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=6)

    total_users = await db["users"].count_documents({})
    active_users = await db["users"].count_documents({"is_active": {"$ne": False}})
    today_new_users = await db["users"].count_documents({"created_at": {"$gte": today_start}})

    now_ts = int(now.timestamp())
    min_ts = now_ts - 300
    await redis.zremrangebyscore("online_users:last_seen", 0, min_ts - 1)
    online_count = len(await redis.zrangebyscore("online_users:last_seen", min_ts, now_ts))

    paid_orders_today = await db["payment_orders"].count_documents({"status": "paid", "paid_at": {"$gte": today_start}})
    orders_today = await db["payment_orders"].count_documents({"created_at": {"$gte": today_start}})

    agg = await db["payment_orders"].aggregate([
        {"$match": {"status": "paid", "paid_at": {"$gte": today_start}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount_cny"}}}
    ]).to_list(length=1)
    paid_amount_today = agg[0]["total"] if agg else 0

    week_rows = await db["payment_orders"].aggregate([
        {"$match": {"status": "paid", "paid_at": {"$gte": week_start}}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$paid_at"}},
                "amount": {"$sum": "$amount_cny"},
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]).to_list(length=None)
    week_map = {r["_id"]: r for r in week_rows}
    trend = []
    for i in range(7):
        day = (week_start + timedelta(days=i)).strftime("%Y-%m-%d")
        item = week_map.get(day, {})
        trend.append({"day": day, "paid_amount": item.get("amount", 0), "paid_count": item.get("count", 0)})

    return SuccessResponse(message="获取成功", data={
        "users": {
            "total": total_users,
            "active": active_users,
            "today_new": today_new_users,
            "online": online_count
        },
        "orders": {
            "today_total": orders_today,
            "today_paid": paid_orders_today,
            "today_paid_amount": paid_amount_today
        },
        "paid_trend_7d": trend
    })


@router.get("/users", response_model=SuccessResponse)
async def admin_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query(""),
    _: str = Depends(get_current_admin)
):
    db = get_mongodb()
    redis = get_redis()
    query = {}
    kw = keyword.strip()
    if kw:
        query["$or"] = [
            {"username": {"$regex": kw, "$options": "i"}},
            {"nickname": {"$regex": kw, "$options": "i"}},
            {"id": {"$regex": kw, "$options": "i"}}
        ]
    total = await db["users"].count_documents(query)
    rows = await db["users"].find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)

    users = []
    now_ts = int(datetime.now().timestamp())
    min_ts = now_ts - 300
    await redis.zremrangebyscore("online_users:last_seen", 0, min_ts - 1)
    for u in rows:
        uid = u["id"]
        score = await redis.zscore("online_users:last_seen", uid)
        is_online = bool(score and score >= min_ts)
        users.append({
            "id": uid,
            "username": u.get("username"),
            "nickname": u.get("nickname"),
            "role": u.get("role", "user"),
            "charm_value": u.get("charm_value", 0),
            "green_mode": u.get("green_mode", False),
            "allow_discovery": u.get("allow_discovery", True),
            "show_location": u.get("show_location", False),
            "location": u.get("location"),
            "is_online": is_online,
            "is_active": u.get("is_active", True),
            "created_at": u.get("created_at"),
            "last_login_at": u.get("last_login_at")
        })

    return SuccessResponse(message="获取成功", data={"rows": users, "page": page, "page_size": page_size, "total": total})


@router.patch("/users/{target_user_id}", response_model=SuccessResponse)
async def update_admin_user(
    target_user_id: str,
    payload: dict = Body(...),
    admin_user_id: str = Depends(get_current_admin)
):
    db = get_mongodb()
    target = await db["users"].find_one({"id": target_user_id})
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    admin = await db["users"].find_one({"id": admin_user_id})
    if target.get("username") == settings.admin_username and admin_user_id != target_user_id:
        raise HTTPException(status_code=400, detail="超级管理员仅可自行修改")

    allowed_keys = {
        "nickname",
        "charm_value",
        "green_mode",
        "allow_discovery",
        "show_location",
        "location",
        "is_active",
        "role"
    }
    update_data = {}
    for k, v in payload.items():
        if k in allowed_keys:
            update_data[k] = v
    if not update_data:
        raise HTTPException(status_code=400, detail="无可更新字段")

    if "role" in update_data and update_data["role"] not in {"user", "admin"}:
        raise HTTPException(status_code=400, detail="role无效")
    if target.get("username") == settings.admin_username:
        update_data["role"] = "admin"

    update_data["updated_at"] = datetime.now()
    await db["users"].update_one({"id": target_user_id}, {"$set": update_data})
    return SuccessResponse(message="更新成功")


@router.get("/sensitive-words", response_model=SuccessResponse)
async def get_green_sensitive_words(_: str = Depends(get_current_admin)):
    db = get_mongodb()
    cfg = await db["system_configs"].find_one({"key": "green_sensitive_words"})
    words = cfg.get("words", []) if cfg else get_sensitive_words()
    return SuccessResponse(message="获取成功", data={"words": words})


@router.put("/sensitive-words", response_model=SuccessResponse)
async def set_green_sensitive_words(
    payload: dict = Body(...),
    _: str = Depends(get_current_admin)
):
    db = get_mongodb()
    words = payload.get("words", [])
    if not isinstance(words, list):
        raise HTTPException(status_code=400, detail="words必须为数组")
    clean_words = [str(w).strip() for w in words if str(w).strip()]
    set_sensitive_words(clean_words)
    await db["system_configs"].update_one(
        {"key": "green_sensitive_words"},
        {"$set": {"words": clean_words, "updated_at": datetime.now()}},
        upsert=True
    )
    return SuccessResponse(message="保存成功", data={"words": clean_words, "count": len(clean_words)})


@router.get("/orders", response_model=SuccessResponse)
async def admin_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(""),
    channel: str = Query(""),
    _: str = Depends(get_current_admin)
):
    db = get_mongodb()
    query = {}
    if status:
        query["status"] = status
    if channel:
        query["channel"] = channel

    total = await db["payment_orders"].count_documents(query)
    rows = await db["payment_orders"].find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size).to_list(length=page_size)
    user_ids = list({r.get("user_id") for r in rows if r.get("user_id")})
    users = await db["users"].find({"id": {"$in": user_ids}}).to_list(length=None) if user_ids else []
    user_map = {u["id"]: u for u in users}

    items = []
    for r in rows:
        u = user_map.get(r.get("user_id"), {})
        items.append({
            "order_no": r.get("order_no"),
            "user_id": r.get("user_id"),
            "username": u.get("username", ""),
            "nickname": u.get("nickname", ""),
            "product_id": r.get("product_id"),
            "amount_cny": r.get("amount_cny", 0),
            "channel": r.get("channel"),
            "status": r.get("status"),
            "created_at": r.get("created_at"),
            "paid_at": r.get("paid_at")
        })

    return SuccessResponse(message="获取成功", data={"rows": items, "page": page, "page_size": page_size, "total": total})
