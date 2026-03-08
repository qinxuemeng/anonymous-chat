from fastapi import APIRouter, Depends, HTTPException, status, Body
from src.database import get_mongodb, get_redis
from src.schemas import (
    ChatMessageCreate,
    LikeMessage,
    ReportMessage,
    BlockUser,
    ChatMessageResponse,
    SuccessResponse,
    ErrorResponse
)
from src.security import get_current_user
from src.utils import filter_sensitive_words, check_english_only
from datetime import datetime
import uuid


router = APIRouter()


@router.post("/message", response_model=SuccessResponse)
async def send_message(
    message: ChatMessageCreate,
    user_id: str = Depends(get_current_user)
):
    """发送消息"""
    db = get_mongodb()

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

    # 创建消息记录
    message_id = str(uuid.uuid4())
    chat_message = {
        "id": message_id,
        "from_user_id": user_id,
        "to_user_id": message.to_user_id,
        "type": message.type,
        "content": content,
        "read": False,
        "liked": False,
        "created_at": datetime.now()
    }

    await db["chats"].insert_one(chat_message)

    # 增加魅力值（文明发言）
    await db["users"].update_one(
        {"id": user_id},
        {"$inc": {"charm_value": 1}, "$set": {"updated_at": datetime.now()}}
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
            "created_at": chat_message["created_at"]
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

    # 计算分页
    skip = (page - 1) * page_size

    # 获取聊天记录（双向）
    messages = await db["chats"].find({
        "$or": [
            {"from_user_id": current_user_id, "to_user_id": user_id},
            {"from_user_id": user_id, "to_user_id": current_user_id}
        ]
    }).sort("created_at", -1).skip(skip).limit(page_size).to_list(length=page_size)

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
            "created_at": msg["created_at"]
        })

    return SuccessResponse(
        message="获取成功",
        data={
            "messages": formatted_messages,
            "page": page,
            "page_size": page_size,
            "total": await db["chats"].count_documents({
                "$or": [
                    {"from_user_id": current_user_id, "to_user_id": user_id},
                    {"from_user_id": user_id, "to_user_id": current_user_id}
                ]
            })
        }
    )


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
