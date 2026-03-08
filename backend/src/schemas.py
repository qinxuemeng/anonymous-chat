from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    SECRET = "secret"


# ============== 用户相关 ==============


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=6, max_length=72)
    email: Optional[EmailStr] = Field(None, description="Email (optional)")
    phone: Optional[str] = Field(None, description="Phone number (optional)")

    @field_validator("email", mode="before")
    @classmethod
    def empty_email_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v

    @field_validator("phone", mode="before")
    @classmethod
    def empty_phone_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    gender: Optional[Gender] = None
    age: Optional[int] = None
    charm_value: int = 500
    allow_discovery: bool = True
    green_mode: bool = False
    night_mode: bool = False
    notification_sound: bool = True
    keep_logged_in: bool = False
    english_mode: bool = False
    show_location: bool = False
    match_gender_preference: str = "any"
    match_location_preference: str = "any"
    match_age_min: int = 18
    match_age_max: int = 99
    match_zone: str = "chat"
    tags: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    gender: Optional[Gender] = None
    age: Optional[int] = None
    tags: Optional[List[str]] = None


class UserSettingsUpdate(BaseModel):
    allow_discovery: Optional[bool] = None
    green_mode: Optional[bool] = None
    night_mode: Optional[bool] = None
    notification_sound: Optional[bool] = None
    keep_logged_in: Optional[bool] = None
    english_mode: Optional[bool] = None
    show_location: Optional[bool] = None
    match_gender_preference: Optional[str] = None
    match_location_preference: Optional[str] = None
    match_age_min: Optional[int] = None
    match_age_max: Optional[int] = None
    match_zone: Optional[str] = None


# ============== 认证相关 ==============


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None


# ============== 聊天相关 ==============


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    EMOJI = "emoji"


class ChatMessageCreate(BaseModel):
    to_user_id: str
    type: MessageType = MessageType.TEXT
    content: str


class ChatMessageResponse(BaseModel):
    id: str
    from_user_id: str
    to_user_id: str
    type: MessageType
    content: str
    read: bool = False
    liked: bool = False
    created_at: datetime


class LikeMessage(BaseModel):
    message_id: str


class ReportMessage(BaseModel):
    message_id: str
    reason: str


class BlockUser(BaseModel):
    user_id: str


# ============== 匹配相关 ==============


class MatchType(str, Enum):
    RANDOM = "random"
    ONLINE = "online"


class MatchStatus(str, Enum):
    WAITING = "waiting"
    MATCHED = "matched"
    COMPLETED = "completed"


class MatchRequest(BaseModel):
    type: MatchType
    use_preferences: bool = False


class MatchResponse(BaseModel):
    id: Optional[str] = None
    matched_user_id: Optional[str] = None
    status: MatchStatus
    waiting_time: Optional[int] = 0


# ============== 漂流瓶相关 ==============


class BottleCreate(BaseModel):
    content: str
    images: Optional[List[str]] = []
    max_pick_count: int = Field(default=5, ge=1, le=20)
    use_preferences: bool = False


class BottleResponse(BaseModel):
    id: str
    user_id: str
    content: str
    images: List[str] = []
    pick_count: int = 0
    max_pick_count: int = 5
    status: str = "active"
    created_at: datetime
    expires_at: datetime


class BottlePickResponse(BaseModel):
    bottle_id: str
    content: str
    images: List[str]
    picker_user_id: Optional[str] = None


class BottleReply(BaseModel):
    bottle_id: str
    content: str


# ============== 寻人公告相关 ==============


class AnnouncementCreate(BaseModel):
    nickname: Optional[str] = "匿名"
    content: str = Field(..., max_length=1000)
    tags: Optional[List[str]] = []


class AnnouncementResponse(BaseModel):
    id: str
    user_id: str
    nickname: str
    content: str
    tags: List[str] = []
    status: str = "pending"
    views: int = 0
    created_at: datetime
    approved_at: Optional[datetime] = None


class AnnouncementClaim(BaseModel):
    announcement_id: str
    verification_info: str


# ============== 魅力值相关 ==============


class CharmAction(str, Enum):
    LOGIN = "login"
    SPEAK = "speak"
    BEHAVE = "behave"
    LIKED = "liked"
    MEMBER = "member"
    REPORTED = "reported"
    AUDIT_FAILED = "audit_failed"


class CharmValueResponse(BaseModel):
    user_id: str
    charm_value: int
    level: str
    permissions: Dict[str, Any]
    daily_usage: Dict[str, int]


class CharmRechargeRequest(BaseModel):
    amount: int = Field(..., ge=1, le=9999)
    channel: str = Field(..., pattern="^(wechat|alipay)$")


class PayCreateOrderRequest(BaseModel):
    product_id: str
    channel: str = Field(..., pattern="^(wechat|alipay)$")
    idempotency_key: Optional[str] = None


# ============== 通用响应 ==============


class SuccessResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    code: Optional[str] = None
