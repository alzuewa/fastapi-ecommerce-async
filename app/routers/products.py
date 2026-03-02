from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_seller
from app.models.categories import Category as CategoryModel
from app.models.products import Product as ProductModel
from app.models.users import User as UserModel
from app.schemas import Product as ProductSchema, ProductCreate
from app.db_depends import get_async_db


# # Create products router with prefix and tag
router = APIRouter(
    prefix='/products',
    tags=['products'],
)


@router.get('/', response_model=list[ProductSchema])
async def get_all_products(db: AsyncSession = Depends(get_async_db)):
    """
    Return all products list.
    """
    result = await db.scalars(select(ProductModel).where(ProductModel.is_active == True))
    return result.all()


@router.post('/',  response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(
        product: ProductCreate,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Create a new product
    """
    category_result = await db.scalars(
        select(CategoryModel).where(CategoryModel.id == product.category_id, CategoryModel.is_active == True)
    )
    if not category_result.first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Category not found or inactive')

    db_product = ProductModel(**product.model_dump(), seller_id=current_user.id)
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)  # to get `id` and `is_active` from DB
    return db_product


@router.get('/category/{category_id}', response_model=list[ProductSchema])
async def get_products_by_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Return products list by category_id
    """
    result = await db.scalars(
        select(CategoryModel).where(CategoryModel.id == category_id,CategoryModel.is_active == True)
    )
    category = result.first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Category not found or inactive')

    product_result = await db.scalars(
        select(ProductModel).where(ProductModel.category_id == category_id, ProductModel.is_active == True)
    )
    return product_result.all()


@router.get('/{product_id}', response_model=ProductSchema)
async def get_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Return detailed info about product by its ID
    """
    product_result = await db.scalars(
        select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    )
    product = product_result.first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found or inactive')

    category_result = await db.scalars(
        select(CategoryModel).where(CategoryModel.id == product.category_id, CategoryModel.is_active == True)
    )
    category = category_result.first()
    if not category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Category not found or inactive')

    return product


@router.put('/{product_id}', response_model=ProductSchema)
async def update_product(
        product_id: int,
        product: ProductCreate,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Update product by ID
    """
    product_result = await db.scalars(select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True))
    db_product = product_result.first()
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found or inactive')
    if db_product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You can only update your own products')

    category_result = await db.scalars(
        select(CategoryModel).where(CategoryModel.id == product.category_id, CategoryModel.is_active == True)
    )
    category = category_result.first()
    if not category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Category not found or inactive')

    await db.execute(
        update(ProductModel).where(ProductModel.id == product_id).values(**product.model_dump())
    )
    await db.commit()
    await db.refresh(db_product)  # for data consistency
    return db_product


@router.delete('/{product_id}')
async def delete_product(
        product_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Delete product by ID
    """
    product_result = await db.scalars(
        select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    )
    product = product_result.first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found or inactive')
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You can only delete your own products')

    await db.execute(
        update(ProductModel).where(ProductModel.id == product_id).values(is_active=False)
    )
    await db.commit()
    await db.refresh(product)  # to return `is_active = False`
    return product
