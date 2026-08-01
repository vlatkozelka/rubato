from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import require_staff
from models.auth_principal import AuthPrincipal
from models.product import Product
from services.product_service import list_products, update_product

router = APIRouter(prefix="/products", tags=["products"])


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    size: Optional[str] = None
    stock: Optional[int] = None


@router.get("", response_model=List[Product])
def get_products(_: AuthPrincipal = Depends(require_staff)) -> List[Product]:
    return list_products()


@router.patch("/{product_id}", response_model=Product)
def patch_product(
    product_id: str,
    payload: ProductUpdate,
    _: AuthPrincipal = Depends(require_staff),
) -> Product:
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    product = update_product(product_id, fields)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
