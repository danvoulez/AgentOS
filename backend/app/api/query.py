import logging
from typing import List, Optional, Any, Dict, Literal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from app.core.database import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.utils.auth import CurrentUser, require_role
from app.models import CurrentStateInventoryItem, CurrentStateOrderStatus
from app.services.state_updater import (
    CS_INVENTORY_COLLECTION, CS_ORDERS_COLLECTION
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get(
    "/inventory/{product_id}",
    response_model=CurrentStateInventoryItem,
    dependencies=[Depends(require_role(["staff", "admin", "manager"]))],
    summary="Get Current State of a Specific Inventory Item"
)
async def query_inventory_item_state(
    product_id: str,
    current_user: CurrentUser = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    log = logger.bind(user_id=str(current_user.id), product_id=product_id)
    log.info("Querying current inventory item state.")
    item_state_doc = await db[CS_INVENTORY_COLLECTION].find_one({"_id": product_id})
    if not item_state_doc:
        log.warning("Inventory item state not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item state not found.")
    try:
        return CurrentStateInventoryItem(**item_state_doc)
    except Exception as e:
        log.error(f"Error parsing inventory item state from DB: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving inventory data.")

@router.get(
    "/inventory",
    response_model=List[CurrentStateInventoryItem],
    dependencies=[Depends(require_role(["staff", "admin", "manager"]))],
    summary="List Current State of Inventory Items"
)
async def query_list_inventory_items(
    current_user: CurrentUser = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_database),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    name_contains: Optional[str] = Query(None, description="Filter by product name (case-insensitive contains)"),
    min_stock: Optional[int] = Query(None, description="Filter items with stock >= this value"),
    max_stock: Optional[int] = Query(None, description="Filter items with stock <= this value"),
    sort_by: Optional[str] = Query("name", description="Field to sort by (e.g., 'name', 'current_stock', 'last_updated_at')"),
    sort_order: Optional[Literal["asc", "desc"]] = Query("asc", description="'asc' or 'desc'")
):
    log = logger.bind(user_id=str(current_user.id))
    log.info("Querying list of current inventory item states.")
    query_filter: Dict[str, Any] = {}
    if name_contains:
        query_filter["name"] = {"$regex": name_contains, "$options": "i"}
    stock_filter_parts = {}
    if min_stock is not None:
        stock_filter_parts["$gte"] = min_stock
    if max_stock is not None:
        stock_filter_parts["$lte"] = max_stock
    if stock_filter_parts:
        query_filter["current_stock"] = stock_filter_parts

    sort_direction = 1 if sort_order == "asc" else -1
    cursor = db[CS_INVENTORY_COLLECTION].find(query_filter).sort(sort_by, sort_direction).skip(skip).limit(limit)
    item_state_docs = await cursor.to_list(length=limit)
    parsed_items = []
    for doc in item_state_docs:
        try:
            parsed_items.append(CurrentStateInventoryItem(**doc))
        except Exception as e:
            log.warning(f"Skipping inventory item parse error: {doc.get('_id')}, Error: {e}")
    return parsed_items

@router.get(
    "/orders/{order_id}/status",
    response_model=CurrentStateOrderStatus,
    dependencies=[Depends(require_role(["staff", "admin", "customer"]))],
    summary="Get Current State of a Specific Order"
)
async def query_order_status(
    order_id: str,
    current_user: CurrentUser = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    log = logger.bind(user_id=str(current_user.id), order_id=order_id)
    log.info("Querying current order status.")
    order_state_doc = await db[CS_ORDERS_COLLECTION].find_one({"_id": order_id})
    if not order_state_doc:
        log.warning("Order state not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order state not found.")

    is_staff_or_admin = "staff" in current_user.roles or "admin" in current_user.roles
    if "customer" in current_user.roles and not is_staff_or_admin:
        customer_identifier_in_order = order_state_doc.get("customer_id")
        if customer_identifier_in_order != str(current_user.id) and customer_identifier_in_order != current_user.email:
            log.warning(f"Customer {current_user.email} (ID: {str(current_user.id)}) tried to access order {order_id} not belonging to them (Order CustID: {customer_identifier_in_order}).")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this order status.")
    try:
        return CurrentStateOrderStatus(**order_state_doc)
    except Exception as e:
        log.error(f"Error parsing order state from DB: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving order data.")

@router.get(
    "/orders",
    response_model=List[CurrentStateOrderStatus],
    dependencies=[Depends(require_role(["staff", "admin", "customer"]))],
    summary="List Current Orders"
)
async def query_list_orders(
    current_user: CurrentUser = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_database),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    customer_id_filter: Optional[str] = Query(None, alias="customerId"),
    status_filter: Optional[str] = Query(None, alias="status"),
    order_ref_filter: Optional[str] = Query(None, alias="orderRef"),
    sort_by: Optional[str] = Query("last_updated_at", description="Field to sort by (e.g., 'created_at', 'last_updated_at', 'status')"),
    sort_order: Optional[Literal["asc", "desc"]] = Query("desc", description="'asc' or 'desc'")
):
    log = logger.bind(user_id=str(current_user.id))
    log.info("Querying list of current order states.")
    query_filter: Dict[str, Any] = {}
    is_staff_or_admin = "staff" in current_user.roles or "admin" in current_user.roles

    if "customer" in current_user.roles and not is_staff_or_admin:
        user_identifier_for_query = str(current_user.id)
        if customer_id_filter and customer_id_filter != user_identifier_for_query:
            log.warning(f"Customer {current_user.email} attempted to query orders for different customer {customer_id_filter}. Denying.")
            return []
        query_filter["customer_id"] = user_identifier_for_query
    elif customer_id_filter:
        query_filter["customer_id"] = customer_id_filter

    if status_filter:
        query_filter["status"] = status_filter
    if order_ref_filter:
        query_filter["order_ref"] = {"$regex": order_ref_filter, "$options": "i"}

    sort_direction = 1 if sort_order == "asc" else -1
    cursor = db[CS_ORDERS_COLLECTION].find(query_filter).sort(sort_by, sort_direction).skip(skip).limit(limit)
    order_state_docs = await cursor.to_list(length=limit)
    parsed_orders = []
    for doc in order_state_docs:
        try:
            parsed_orders.append(CurrentStateOrderStatus(**doc))
        except Exception as e:
            log.warning(f"Skipping order state parse error: {doc.get('_id')}, Error: {e}")
    return parsed_orders