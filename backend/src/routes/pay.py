from datetime import datetime, timedelta
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Body

from src.database import get_mongodb
from src.schemas import SuccessResponse, PayCreateOrderRequest
from src.security import get_current_user


router = APIRouter()


DEFAULT_PRODUCTS = [
    {"id": "charm_30", "name": "30魅力值", "type": "recharge", "amount_cny": 30, "charm_value": 30, "bonus_charm": 0, "is_active": True},
    {"id": "charm_68", "name": "68魅力值", "type": "recharge", "amount_cny": 68, "charm_value": 68, "bonus_charm": 5, "is_active": True},
    {"id": "charm_108", "name": "108魅力值", "type": "recharge", "amount_cny": 108, "charm_value": 108, "bonus_charm": 12, "is_active": True},
]


async def ensure_products(db):
    count = await db["products"].count_documents({})
    if count > 0:
        return
    now = datetime.now()
    docs = []
    for p in DEFAULT_PRODUCTS:
        docs.append({
            **p,
            "created_at": now,
            "updated_at": now
        })
    await db["products"].insert_many(docs)


@router.get("/products", response_model=SuccessResponse)
async def list_products(user_id: str = Depends(get_current_user)):
    db = get_mongodb()
    await ensure_products(db)
    products = await db["products"].find({"is_active": True}).sort("amount_cny", 1).to_list(length=None)
    return SuccessResponse(message="获取成功", data={"products": products})


@router.post("/orders", response_model=SuccessResponse)
async def create_order(payload: PayCreateOrderRequest, user_id: str = Depends(get_current_user)):
    db = get_mongodb()
    await ensure_products(db)

    product = await db["products"].find_one({"id": payload.product_id, "is_active": True})
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")

    idempotency_key = payload.idempotency_key or str(uuid.uuid4())
    existing = await db["payment_orders"].find_one({"user_id": user_id, "idempotency_key": idempotency_key})
    if existing:
        return SuccessResponse(message="下单成功", data={"order_no": existing["order_no"], "status": existing["status"]})

    order_no = f"O{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4().int)[-6:]}"
    now = datetime.now()
    order = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "order_no": order_no,
        "product_id": product["id"],
        "amount_cny": product["amount_cny"],
        "channel": payload.channel,
        "status": "created",
        "provider_order_id": None,
        "provider_trade_no": None,
        "idempotency_key": idempotency_key,
        "expire_at": now + timedelta(minutes=15),
        "paid_at": None,
        "created_at": now,
        "updated_at": now,
    }
    await db["payment_orders"].insert_one(order)
    pay_params = {
        "channel": payload.channel,
        "order_no": order_no,
        "amount": order["amount_cny"],
        "mock_pay": True
    }
    return SuccessResponse(message="下单成功", data={"order_no": order_no, "status": "created", "pay_params": pay_params})


@router.get("/orders/{order_no}", response_model=SuccessResponse)
async def get_order_status(order_no: str, user_id: str = Depends(get_current_user)):
    db = get_mongodb()
    order = await db["payment_orders"].find_one({"order_no": order_no, "user_id": user_id})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    return SuccessResponse(message="获取成功", data={"order_no": order["order_no"], "status": order["status"], "paid_at": order.get("paid_at")})


async def _mark_order_paid(db, order_no: str, channel: str, provider_trade_no: str):
    order = await db["payment_orders"].find_one({"order_no": order_no})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    if order["status"] == "paid":
        return order

    product = await db["products"].find_one({"id": order["product_id"]})
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")

    gain = int(product.get("charm_value", 0)) + int(product.get("bonus_charm", 0))
    now = datetime.now()
    await db["payment_orders"].update_one(
        {"order_no": order_no, "status": {"$ne": "paid"}},
        {"$set": {"status": "paid", "provider_trade_no": provider_trade_no, "paid_at": now, "updated_at": now}}
    )
    await db["users"].update_one(
        {"id": order["user_id"]},
        {"$inc": {"charm_value": gain}, "$set": {"updated_at": now}}
    )
    refreshed = await db["users"].find_one({"id": order["user_id"]})
    await db["charm_ledger"].insert_one({
        "id": str(uuid.uuid4()),
        "user_id": order["user_id"],
        "change": gain,
        "balance_after": refreshed.get("charm_value", 0),
        "biz_type": "recharge",
        "biz_id": order_no,
        "description": f"{'微信' if channel == 'wechat' else '支付宝'}充值到账",
        "meta": {"channel": channel, "amount_cny": order.get("amount_cny", 0)},
        "created_at": now
    })
    return await db["payment_orders"].find_one({"order_no": order_no})


@router.post("/callback/wechat", response_model=SuccessResponse)
async def callback_wechat(payload: dict = Body(...)):
    db = get_mongodb()
    order_no = payload.get("order_no")
    trade_no = payload.get("trade_no") or str(uuid.uuid4())
    pay_status = payload.get("status") or "SUCCESS"
    await db["payment_callbacks"].insert_one({
        "id": str(uuid.uuid4()),
        "channel": "wechat",
        "raw_body": payload,
        "verify_ok": True,
        "order_no": order_no,
        "provider_trade_no": trade_no,
        "status": pay_status,
        "created_at": datetime.now()
    })
    if pay_status != "SUCCESS":
        return SuccessResponse(message="回调已接收")
    await _mark_order_paid(db, order_no, "wechat", trade_no)
    return SuccessResponse(message="回调处理成功")


@router.post("/callback/alipay", response_model=SuccessResponse)
async def callback_alipay(payload: dict = Body(...)):
    db = get_mongodb()
    order_no = payload.get("order_no")
    trade_no = payload.get("trade_no") or str(uuid.uuid4())
    pay_status = payload.get("status") or "SUCCESS"
    await db["payment_callbacks"].insert_one({
        "id": str(uuid.uuid4()),
        "channel": "alipay",
        "raw_body": payload,
        "verify_ok": True,
        "order_no": order_no,
        "provider_trade_no": trade_no,
        "status": pay_status,
        "created_at": datetime.now()
    })
    if pay_status != "SUCCESS":
        return SuccessResponse(message="回调已接收")
    await _mark_order_paid(db, order_no, "alipay", trade_no)
    return SuccessResponse(message="回调处理成功")


@router.post("/mock/confirm", response_model=SuccessResponse)
async def mock_confirm(order_no: str = Body(..., embed=True), channel: str = Body(..., embed=True), user_id: str = Depends(get_current_user)):
    """测试环境：模拟支付成功。"""
    db = get_mongodb()
    order = await db["payment_orders"].find_one({"order_no": order_no, "user_id": user_id})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")
    if channel not in {"wechat", "alipay"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的支付方式")
    updated = await _mark_order_paid(db, order_no, channel, str(uuid.uuid4()))
    return SuccessResponse(message="支付成功", data={"order_no": order_no, "status": updated["status"]})
