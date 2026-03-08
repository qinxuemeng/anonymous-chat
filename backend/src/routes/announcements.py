from fastapi import APIRouter, Depends, HTTPException, status, Body
from src.database import get_mongodb
from src.schemas import (
    AnnouncementCreate,
    AnnouncementClaim,
    AnnouncementResponse,
    SuccessResponse,
    ErrorResponse
)
from src.security import get_current_user
from src.utils import check_feature_permission, filter_sensitive_words
from datetime import datetime
import uuid


router = APIRouter()


@router.post("", response_model=SuccessResponse)
async def create_announcement(
    announcement_data: AnnouncementCreate,
    user_id: str = Depends(get_current_user)
):
    """发布寻人公告"""
    db = get_mongodb()

    user = await db["users"].find_one({"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 检查权限
    charm_value = user["charm_value"]
    if not check_feature_permission(charm_value, "publish_announcement"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的魅力值不足，无法发布寻人公告（需要≥100）"
        )

    # 内容过滤
    content = filter_sensitive_words(announcement_data.content)

    # 创建公告
    announcement_id = str(uuid.uuid4())
    announcement = {
        "id": announcement_id,
        "user_id": user_id,
        "nickname": announcement_data.nickname or "匿名",
        "content": content,
        "tags": announcement_data.tags or [],
        "status": "pending",
        "views": 0,
        "created_at": datetime.now(),
        "approved_at": None
    }

    await db["announcements"].insert_one(announcement)

    return SuccessResponse(
        message="公告已提交，审核通过后将显示",
        data={
            "id": announcement_id,
            "nickname": announcement["nickname"],
            "content": content,
            "tags": announcement["tags"],
            "status": "pending",
            "created_at": announcement["created_at"]
        }
    )


@router.get("", response_model=SuccessResponse)
async def get_announcements(
    page: int = 1,
    page_size: int = 10,
    user_id: str = Depends(get_current_user)
):
    """获取公告列表（轮播用）"""
    db = get_mongodb()

    skip = (page - 1) * page_size

    # 获取已审核通过的公告
    announcements = await db["announcements"].find({
        "status": "approved"
    }).sort("created_at", -1).skip(skip).limit(page_size).to_list(length=page_size)

    # 更新浏览次数
    for ann in announcements:
        await db["announcements"].update_one(
            {"id": ann["id"]},
            {"$inc": {"views": 1}}
        )

    return SuccessResponse(
        message="获取成功",
        data={
            "announcements": [
                {
                    "id": ann["id"],
                    "nickname": ann["nickname"],
                    "content": ann["content"][:100] + "..." if len(ann["content"]) > 100 else ann["content"],
                    "full_content": ann["content"],
                    "tags": ann["tags"],
                    "views": ann["views"],
                    "created_at": ann["created_at"],
                    "approved_at": ann["approved_at"]
                }
                for ann in announcements
            ],
            "page": page,
            "page_size": page_size,
            "total": await db["announcements"].count_documents({"status": "approved"})
        }
    )


@router.get("/{announcement_id}", response_model=SuccessResponse)
async def get_announcement_detail(
    announcement_id: str,
    user_id: str = Depends(get_current_user)
):
    """获取公告详情"""
    db = get_mongodb()

    announcement = await db["announcements"].find_one({"id": announcement_id})
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公告不存在"
        )

    # 更新浏览次数
    await db["announcements"].update_one(
        {"id": announcement_id},
        {"$inc": {"views": 1}}
    )

    return SuccessResponse(
        message="获取成功",
        data={
            "id": announcement["id"],
            "nickname": announcement["nickname"],
            "content": announcement["content"],
            "tags": announcement["tags"],
            "views": announcement["views"] + 1,
            "status": announcement["status"],
            "created_at": announcement["created_at"],
            "approved_at": announcement["approved_at"]
        }
    )


@router.post("/claim", response_model=SuccessResponse)
async def claim_announcement(
    claim_data: AnnouncementClaim,
    user_id: str = Depends(get_current_user)
):
    """认领公告"""
    db = get_mongodb()

    announcement = await db["announcements"].find_one({"id": claim_data.announcement_id})
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公告不存在"
        )

    # 检查是否已经认领过
    existing_claim = await db["announcement_claims"].find_one({
        "announcement_id": claim_data.announcement_id,
        "claimant_user_id": user_id
    })
    if existing_claim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已经认领过该公告"
        )

    # 创建认领记录
    claim_id = str(uuid.uuid4())
    claim = {
        "id": claim_id,
        "announcement_id": claim_data.announcement_id,
        "claimant_user_id": user_id,
        "verification_info": claim_data.verification_info,
        "status": "pending",
        "created_at": datetime.now(),
        "reviewed_at": None,
        "reviewed_by": None
    }

    await db["announcement_claims"].insert_one(claim)

    return SuccessResponse(
        message="认领申请已提交，等待发布者确认",
        data={
            "claim_id": claim_id,
            "status": "pending"
        }
    )
