from fastapi import HTTPException, status

from app.models.product import Product


def qty_to_pieces(*, product: Product, qty: int, uom: str) -> int:
    """
    v1 policy: store all inventory quantities internally as integer "pieces".
    Supports converting carton/pallet to pieces when product has conversion factors.
    """
    if qty <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="qty must be > 0")

    uu = (uom or "piece").strip().lower()
    if uu == "piece":
        return int(qty)
    if uu == "carton":
        if not product.carton_qty or int(product.carton_qty) <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product carton_qty not configured")
        return int(qty) * int(product.carton_qty)
    if uu == "pallet":
        if not product.pallet_qty or int(product.pallet_qty) <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product pallet_qty not configured")
        return int(qty) * int(product.pallet_qty)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid uom (piece/carton/pallet)")


