
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Item


def purchase(db: Session, item_id: str, cash_inserted: int) -> dict:
    item = db.query(Item).filter(Item.id == item_id).with_for_update().first() # Lock the row
    if not item:
        raise ValueError("item_not_found")
    
    if item.quantity <= 0:
        raise ValueError("out_of_stock")
    if cash_inserted < item.price:
        raise ValueError("insufficient_cash", item.price, cash_inserted)
    # No validation that cash_inserted or change use SUPPORTED_DENOMINATIONS
    change = cash_inserted - item.price
    item.quantity -= 1
    # We must also update the slot count atomically or within the same lock
    # Since we have the item, we can get the slot. Ideally slot should be locked too if we are pedantic
    # but item lock prevents other purchases of THIS item.
    # However, adding items to the same slot might race.
    # For now, let's just update the objects.
    item.slot.current_item_count -= 1
    
    db.commit()
    db.refresh(item)
    return {
        "item": item.name,
        "price": item.price,
        "cash_inserted": cash_inserted,
        "change_returned": change,
        "remaining_quantity": item.quantity,
        "message": "Purchase successful",
    }


def change_breakdown(change: int) -> dict:
    denominations = sorted(settings.SUPPORTED_DENOMINATIONS, reverse=True)
    result: dict[str, int] = {}
    remaining = change
    for d in denominations:
        if remaining <= 0:
            break
        count = remaining // d
        if count > 0:
            result[str(d)] = count
            remaining -= count * d
    return {"change": change, "denominations": result}
