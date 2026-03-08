import os
import uuid
from fastapi import UploadFile
from datetime import datetime
from typing import List
from src.config import settings


# 随机昵称库
NICKNAMES = [
    "神秘人", "过客", "旅人", "寻梦人", "夜行者",
    "追梦人", "忘忧草", "向日葵", "星辰", "月光",
    "风信子", "紫罗兰", "茉莉", "青柠", "橙子",
    "咖啡", "奶茶", "糖果", "泡泡", "云朵",
    "飞鸟", "鱼儿", "猫儿", "狗儿", "兔子",
    "阳光", "彩虹", "雨滴", "雪花", "落叶"
]


def generate_nickname() -> str:
    """生成随机昵称"""
    import random
    base_nick = random.choice(NICKNAMES)
    suffix = str(random.randint(100, 999))
    return f"{base_nick}{suffix}"


def validate_image(file: UploadFile) -> bool:
    """验证图片文件"""
    if not file.content_type:
        return False
    return file.content_type in ["image/jpeg", "image/png", "image/gif", "image/webp"]


async def save_uploaded_file(file: UploadFile, directory: str) -> str:
    """保存上传的文件"""
    upload_dir = os.path.join(settings.upload_dir, directory)
    os.makedirs(upload_dir, exist_ok=True)

    # 生成唯一文件名
    file_extension = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)

    # 保存文件
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return file_path


def get_charm_level(charm_value: int) -> str:
    """获取魅力值等级"""
    if charm_value < 20:
        return "受限"
    elif charm_value < 35:
        return "观察"
    elif charm_value < 50:
        return "进阶"
    elif charm_value < 100:
        return "活跃"
    elif charm_value < 200:
        return "优质"
    else:
        return "核心"


def get_feature_limit(charm_value: int, feature: str) -> int:
    """获取功能使用次数限制"""
    base_limits = {
        "match": 200,
        "pick_bottle": 10,
        "throw_bottle": 10,
        "pick_online": 2,
        "send_file": 50,
        "virtual_chat": 10
    }

    base_limit = base_limits.get(feature, 0)

    # 魅力值 200 以上，每 +50 魅力值，所有功能日次数 +1
    if charm_value >= 200:
        additional = (charm_value - 200) // 50 + 1
        return base_limit + additional

    # 受限用户
    if charm_value < 20 and feature in ["match", "pick_online", "pick_bottle"]:
        if feature == "match":
            return 200
        return 2

    return base_limit


def get_today_key(user_id: str, feature: str) -> str:
    """获取今日使用次数的 Redis 键"""
    today = datetime.now().strftime("%Y-%m-%d")
    return f"usage:{user_id}:{feature}:{today}"


def check_feature_permission(charm_value: int, feature: str) -> bool:
    """检查功能权限"""
    permissions = {
        "chat": 0,
        "match": 0,
        "throw_bottle": 50,
        "pick_bottle": 50,
        "send_file": 35,
        "edit_nickname": 35,
        "custom_avatar": 50,
        "publish_announcement": 100,
        "edit_settings": 200,
        "virtual_chat": 0
    }

    required = permissions.get(feature, 0)
    return charm_value >= required


# 敏感词过滤（简化版）
SENSITIVE_WORDS = [
    "色情", "暴力", "恐怖", "诈骗", "赌博",
    "毒品", "枪支", "爆炸", "攻击", "侮辱"
]


def get_sensitive_words() -> List[str]:
    return SENSITIVE_WORDS


def set_sensitive_words(words: List[str]) -> None:
    global SENSITIVE_WORDS
    SENSITIVE_WORDS = [str(w).strip() for w in words if str(w).strip()]


def filter_sensitive_words(text: str) -> str:
    """过滤敏感词"""
    filtered_text = text
    for word in SENSITIVE_WORDS:
        if word in filtered_text:
            filtered_text = filtered_text.replace(word, "*" * len(word))
    return filtered_text


def check_english_only(text: str) -> bool:
    """检查是否只包含英文字母、数字和标点"""
    import re
    # 允许字母、数字、基本标点符号和空格
    pattern = r'^[a-zA-Z0-9\s\.,!?;:\'\"\-_\(\)\[\]{}@#$%^&*+=/\\|<>`~]*$'
    return bool(re.match(pattern, text))
