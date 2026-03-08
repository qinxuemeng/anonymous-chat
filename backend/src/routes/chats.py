from fastapi import APIRouter, Depends, HTTPException, status
from src.database import get_mongodb, get_redis
from src.schemas import ChatMessageCreate, LikeMessage, ReportMessage, BlockUser, SuccessResponse
from src.security import get_current_user, ONLINE_WINDOW_SECONDS
from src.utils import filter_sensitive_words, check_english_only
from datetime import datetime, timedelta
import uuid
import time


router = APIRouter()
CHAT_RETENTION_DAYS = 7
DELETE_NOTICE_CONTENT = "已被对方删除"


async def _cleanup_expired_messages(db, current_user_id: str):
    """清理当前用户可见范围内已过期消息。"""
    now = datetime.now()
    fallback_expire_before = now - timedelta(days=CHAT_RETENTION_DAYS)
    await db["chats"].delete_many({
        "$or": [
            {
                "expires_at": {"$lt": now},
                "$or": [{"from_user_id": current_user_id}, {"to_user_id": current_user_id}]
            },
            {
                "expires_at": {"$exists": False},
                "created_at": {"$lt": fallback_expire_before},
                "$or": [{"from_user_id": current_user_id}, {"to_user_id": current_user_id}]
            }
        ]
    })


def _non_expired_filter(now: datetime):
    return {
        "$or": [
            {"expires_at": {"$gt": now}},
            {
                "expires_at": {"$exists": False},
                "created_at": {"$gte": now - timedelta(days=CHAT_RETENTION_DAYS)}
            }
        ]
    }


def _visible_for_user_filter(user_id: str):
    return {
        "$or": [
            {"hidden_for_users": {"$exists": False}},
            {"hidden_for_users": {"$ne": user_id}}
        ]
    }


@router.post("/message", response_model=SuccessResponse)
async def send_message(
    message: ChatMessageCreate,
    user_id: str = Depends(get_current_user)
):
    """发送消息"""
    db = get_mongodb()
    await _cleanup_expired_messages(db, user_id)

    # 检查接收用户是否存在
    to_user = await db["users"].find_one({"id": message.to_user_id})
    if not to_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="接收用户不存在"
        )

    # 获取发送用户的设置
    from_user = await db["users"].find_one({"id": user_id})
    # 魅力值<20 强制绿色模式
    green_mode = from_user.get("green_mode", False) or from_user.get("charm_value", 0) < 20
    english_mode = from_user.get("english_mode", False)

    # 内容过滤
    content = message.content

    if green_mode:
        content = filter_sensitive_words(content)

    if english_mode:
        if not check_english_only(content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="英语模式下只能使用字母、数字和基本标点符号"
            )

    # 如果会话中存在“已被对方删除”提示，则禁止继续发送消息（服务端控制）
    deleted_notice_exists = await db["chats"].find_one({
        "from_user_id": message.to_user_id,
        "to_user_id": user_id,
        "is_system": True,
        "content": DELETE_NOTICE_CONTENT
    })
    if deleted_notice_exists:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您已被对方删除，暂时无法发送消息"
        )

    # 创建消息记录
    message_id = str(uuid.uuid4())
    now = datetime.now()
    expires_at = now + timedelta(days=CHAT_RETENTION_DAYS)
    chat_message = {
        "id": message_id,
        "from_user_id": user_id,
        "to_user_id": message.to_user_id,
        "type": message.type,
        "content": content,
        "read": False,
        "liked": False,
        "created_at": now,
        "expires_at": expires_at,
        "hidden_for_users": []
    }

    await db["chats"].insert_one(chat_message)
    await db["chats"].update_many(
        {
            "$or": [
                {"from_user_id": user_id, "to_user_id": message.to_user_id},
                {"from_user_id": message.to_user_id, "to_user_id": user_id}
            ]
        },
        {"$set": {"expires_at": expires_at}}
    )

    # 增加魅力值（文明发言）
    await db["users"].update_one(
        {"id": user_id},
        {"$inc": {"charm_value": 1}, "$set": {"updated_at": now}}
    )

    return SuccessResponse(
        message="消息发送成功",
        data={
            "id": message_id,
            "from_user_id": user_id,
            "to_user_id": message.to_user_id,
            "type": message.type,
            "content": content,
            "read": False,
            "liked": False,
            "created_at": chat_message["created_at"],
            "expires_at": chat_message["expires_at"]
        }
    )


@router.get("/history", response_model=SuccessResponse)
async def get_chat_history(
    user_id: str,
    page: int = 1,
    page_size: int = 50,
    current_user_id: str = Depends(get_current_user)
):
    """获取聊天记录"""
    db = get_mongodb()
    await _cleanup_expired_messages(db, current_user_id)
    now = datetime.now()
    base_filter = _non_expired_filter(now)

    # 进入会话即标记来自对方的消息为已读
    await db["chats"].update_many(
        {
            "$and": [
                {"from_user_id": user_id, "to_user_id": current_user_id, "read": False},
                base_filter,
                _visible_for_user_filter(current_user_id)
            ]
        },
        {"$set": {"read": True}}
    )

    # 计算分页
    skip = (page - 1) * page_size

    # 获取聊天记录（双向）
    query = {
        "$and": [
            {
                "$or": [
                    {"from_user_id": current_user_id, "to_user_id": user_id},
                    {"from_user_id": user_id, "to_user_id": current_user_id}
                ]
            },
            base_filter,
            _visible_for_user_filter(current_user_id)
        ]
    }
    messages = await db["chats"].find(query).sort("created_at", -1).skip(skip).limit(page_size).to_list(length=page_size)

    # 格式化响应
    formatted_messages = []
    for msg in messages:
        formatted_messages.append({
            "id": msg["id"],
            "from_user_id": msg["from_user_id"],
            "to_user_id": msg["to_user_id"],
            "type": msg["type"],
            "content": msg["content"],
            "read": msg["read"],
            "liked": msg["liked"],
            "created_at": msg["created_at"],
            "expires_at": msg.get("expires_at"),
            "is_system": msg.get("is_system", False)
        })

    return SuccessResponse(
        message="获取成功",
        data={
            "messages": formatted_messages,
            "page": page,
            "page_size": page_size,
            "total": await db["chats"].count_documents(query)
        }
    )


@router.get("/conversations", response_model=SuccessResponse)
async def get_conversations(current_user_id: str = Depends(get_current_user)):
    """获取会话列表（按最后一条消息排序）。"""
    db = get_mongodb()
    await _cleanup_expired_messages(db, current_user_id)
    now = datetime.now()
    messages = await db["chats"].find({
        "$and": [
            {"$or": [{"from_user_id": current_user_id}, {"to_user_id": current_user_id}]},
            _non_expired_filter(now),
            _visible_for_user_filter(current_user_id)
        ]
    }).sort("created_at", -1).to_list(length=None)

    peer_last_message = {}
    peer_deleted_by_other = {}
    peer_unread_count = {}
    for msg in messages:
        peer_id = msg["to_user_id"] if msg["from_user_id"] == current_user_id else msg["from_user_id"]
        if peer_id not in peer_unread_count:
            peer_unread_count[peer_id] = 0
        if peer_id not in peer_deleted_by_other:
            peer_deleted_by_other[peer_id] = False
        if (
            msg.get("to_user_id") == current_user_id
            and msg.get("from_user_id") == peer_id
            and not msg.get("read", False)
            and not msg.get("is_system", False)
        ):
            peer_unread_count[peer_id] += 1
        if (
            msg.get("is_system")
            and msg.get("content") == DELETE_NOTICE_CONTENT
            and msg.get("from_user_id") == peer_id
            and msg.get("to_user_id") == current_user_id
        ):
            peer_deleted_by_other[peer_id] = True
        if peer_id in peer_last_message:
            continue
        peer_last_message[peer_id] = msg

    peer_ids = list(peer_last_message.keys())
    users = await db["users"].find({"id": {"$in": peer_ids}}).to_list(length=None) if peer_ids else []
    user_map = {u["id"]: u for u in users}
    redis = get_redis()
    now_ts = int(time.time())
    min_ts = now_ts - ONLINE_WINDOW_SECONDS
    await redis.zremrangebyscore("online_users:last_seen", 0, min_ts - 1)
    online_list = await redis.zrangebyscore("online_users:last_seen", min_ts, now_ts)
    online_set = {(uid.decode() if isinstance(uid, bytes) else uid) for uid in online_list}

    conversations = []
    for peer_id, last_msg in peer_last_message.items():
        peer = user_map.get(peer_id, {})
        deleted_by_other = peer_deleted_by_other.get(peer_id, False)
        effective_online = (peer_id in online_set) and (not deleted_by_other)
        conversations.append({
            "user_id": peer_id,
            "nickname": peer.get("nickname") or "神秘人",
            "avatar": peer.get("avatar") or "",
            "last_message": last_msg.get("content") or "",
            "last_message_type": last_msg.get("type") or "text",
            "last_message_at": last_msg.get("created_at"),
            "unread_count": peer_unread_count.get(peer_id, 0),
            "is_online": effective_online,
            "deleted_by_other": deleted_by_other
        })

    conversations.sort(
        key=lambda x: (
            1 if x.get("is_online") else 0,
            x.get("last_message_at") or datetime.min
        ),
        reverse=True
    )
    return SuccessResponse(message="获取成功", data={"conversations": conversations})


@router.get("/unread/count", response_model=SuccessResponse)
async def get_unread_count(current_user_id: str = Depends(get_current_user)):
    """获取当前用户总未读消息数。"""
    db = get_mongodb()
    await _cleanup_expired_messages(db, current_user_id)
    now = datetime.now()
    total = await db["chats"].count_documents({
        "$and": [
            {"to_user_id": current_user_id, "read": False, "is_system": {"$ne": True}},
            _non_expired_filter(now),
            _visible_for_user_filter(current_user_id)
        ]
    })
    return SuccessResponse(message="获取成功", data={"unread_count": total})


@router.get("/presence/{target_user_id}", response_model=SuccessResponse)
async def get_user_presence(target_user_id: str, current_user_id: str = Depends(get_current_user)):
    """获取目标用户在线状态。"""
    db = get_mongodb()
    target = await db["users"].find_one({"id": target_user_id})
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    redis = get_redis()
    now_ts = int(time.time())
    min_ts = now_ts - ONLINE_WINDOW_SECONDS
    await redis.zremrangebyscore("online_users:last_seen", 0, min_ts - 1)
    score = await redis.zscore("online_users:last_seen", target_user_id)
    is_online = bool(score and score >= min_ts)
    return SuccessResponse(message="获取成功", data={"user_id": target_user_id, "is_online": is_online})


@router.delete("/conversation/{peer_user_id}", response_model=SuccessResponse)
async def delete_conversation(peer_user_id: str, current_user_id: str = Depends(get_current_user)):
    """删除与指定用户的会话（仅当前用户隐藏），并给对方发送删除提示。"""
    db = get_mongodb()
    result = await db["chats"].update_many({
        "$or": [
            {"from_user_id": current_user_id, "to_user_id": peer_user_id},
            {"from_user_id": peer_user_id, "to_user_id": current_user_id}
        ]
    }, {
        "$addToSet": {"hidden_for_users": current_user_id}
    })

    now = datetime.now()
    await db["chats"].insert_one({
        "id": str(uuid.uuid4()),
        "from_user_id": current_user_id,
        "to_user_id": peer_user_id,
        "type": "text",
        "content": DELETE_NOTICE_CONTENT,
        "read": False,
        "liked": False,
        "created_at": now,
        "expires_at": now + timedelta(days=CHAT_RETENTION_DAYS),
        "is_system": True,
        "hidden_for_users": [current_user_id]
    })

    return SuccessResponse(message="删除成功", data={"hidden_count": result.modified_count})


@router.post("/like", response_model=SuccessResponse)
async def like_message(
    like_data: LikeMessage,
    user_id: str = Depends(get_current_user)
):
    """点赞消息"""
    db = get_mongodb()

    # 检查消息是否存在
    message = await db["chats"].find_one({"id": like_data.message_id})
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在"
        )

    # 不能给自己的消息点赞
    if message["from_user_id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能给自己的消息点赞"
        )

    # 更新消息点赞状态
    await db["chats"].update_one(
        {"id": like_data.message_id},
        {"$set": {"liked": True}}
    )

    # 给发送者增加魅力值
    await db["users"].update_one(
        {"id": message["from_user_id"]},
        {"$inc": {"charm_value": 2}, "$set": {"updated_at": datetime.now()}}
    )

    return SuccessResponse(message="点赞成功")


@router.post("/report", response_model=SuccessResponse)
async def report_message(
    report_data: ReportMessage,
    user_id: str = Depends(get_current_user)
):
    """举报消息"""
    db = get_mongodb()

    message = await db["chats"].find_one({"id": report_data.message_id})
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在"
        )

    # 检查是否已经举报过
    existing_report = await db["reports"].find_one({
        "user_id": user_id,
        "target_id": report_data.message_id,
        "target_type": "message"
    })
    if existing_report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已经举报过该消息"
        )

    # 创建举报记录
    await db["reports"].insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "target_id": report_data.message_id,
        "target_type": "message",
        "target_user_id": message["from_user_id"],
        "reason": report_data.reason,
        "status": "pending",
        "created_at": datetime.now(),
        "reviewed_at": None,
        "reviewed_by": None
    })

    return SuccessResponse(message="举报成功，我们将尽快处理")


@router.post("/block", response_model=SuccessResponse)
async def block_user(
    block_data: BlockUser,
    user_id: str = Depends(get_current_user)
):
    """拉黑用户"""
    db = get_mongodb()

    # 不能拉黑自己
    if block_data.user_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能拉黑自己"
        )

    # 检查用户是否存在
    target_user = await db["users"].find_one({"id": block_data.user_id})
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="目标用户不存在"
        )

    # 检查是否已经拉黑过
    existing_block = await db["blocks"].find_one({
        "user_id": user_id,
        "blocked_user_id": block_data.user_id
    })
    if existing_block:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已经拉黑过该用户"
        )

    # 创建拉黑记录
    await db["blocks"].insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "blocked_user_id": block_data.user_id,
        "created_at": datetime.now()
    })

    return SuccessResponse(message="拉黑成功")
