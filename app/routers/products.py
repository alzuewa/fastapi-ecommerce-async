import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select, func, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_seller
from app.models.categories import Category as CategoryModel
from app.models.products import Product as ProductModel
from app.models.users import User as UserModel
from app.schemas import Product as ProductSchema, ProductCreate, ProductList
from app.db_depends import get_async_db


BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_ROOT = BASE_DIR / 'media' / 'products'
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2 097 152 bytes


# # Create products router with prefix and tag
router = APIRouter(
    prefix='/products',
    tags=['products'],
)

async def save_product_image(file: UploadFile) -> str:
    """
    Store product image and return a relative URL.
    """

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Only JPG, PNG or WebP images are allowed')

    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Image is too large')

    extension = Path(file.filename or '').suffix.lower() or '.jpg'
    file_name = f'{uuid.uuid4()}{extension}'
    file_path = MEDIA_ROOT / file_name
    file_path.write_bytes(content)

    return f'/media/products/{file_name}'

def remove_product_image(url: str | None) -> None:
    """
    Remove product image if exists.
    """
    if not url:
        return
    relative_path = url.lstrip('/')
    file_path = BASE_DIR / relative_path
    if file_path.exists():
        file_path.unlink()


@router.get('/', response_model=list[ProductSchema])
async def get_all_products(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        category_id: int | None = Query(None, description='Category ID for filtering'),
        search: str | None = Query(None, min_length=1, description='Product search by name'),
        min_price: float | None = Query(None, ge=0, description='Min product price'),
        max_price: float | None = Query(None, ge=0, description='Max product price'),
        in_stock: bool | None = Query(None, description='true — only products available in stock, false — only not in stock'),
        seller_id: int | None = Query(None, description='Seller ID for filtering'),
        db: AsyncSession = Depends(get_async_db)
):
    """
    Return all products list supporting filters.
    """

    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='min_price can not be more than max_price',
        )

    filters = [ProductModel.is_active == True]

    if category_id is not None:
        filters.append(ProductModel.category_id == category_id)
    if min_price is not None:
        filters.append(ProductModel.price >= min_price)
    if max_price is not None:
        filters.append(ProductModel.price <= max_price)
    if in_stock is not None:
        filters.append(ProductModel.stock > 0 if in_stock else ProductModel.stock == 0)
    if seller_id is not None:
        filters.append(ProductModel.seller_id == seller_id)

    total_stmt = select(func.count()).select_from(ProductModel).where(*filters)

    rank_col = None
    if search:
        search_value = search.strip()
        if search_value:
            ts_query = func.websearch_to_tsquery('english', search_value)
            filters.append(ProductModel.tsv.op('@@')(ts_query))
            rank_col = func.ts_rank_cd(ProductModel.tsv, ts_query).label('rank')
            # total with Full Text Search
            total_stmt = select(func.count()).select_from(ProductModel).where(*filters)

    total = await db.scalars(total_stmt) or 0

    if rank_col is not None:
        products_stmt = (
            select(ProductModel, rank_col)
            .where(*filters)
            .order_by(desc(rank_col), ProductModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(products_stmt)
        rows = result.all()
        items = [row[0] for row in rows]  # objects itself
        # a rank can be returned
        # ranks = [row.rank for row in rows]
    else:
        products_stmt = (
            select(ProductModel)
            .where(*filters)
            .order_by(ProductModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await db.scalars(products_stmt)).all()

    return {
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size,
    }


@router.post('/',  response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(
        product: ProductCreate = Depends(ProductCreate.as_form),
        image: UploadFile | None = File(None),
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Create a new product
    """
    category_result = await db.scalars(
        select(CategoryModel).where(CategoryModel.id == product.category_id,
                                    CategoryModel.is_active == True)
    )
    if not category_result.first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Category not found or inactive')

    # Save image if any
    image_url = await save_product_image(image) if image else None

    # Create product
    db_product = ProductModel(
        **product.model_dump(),
        seller_id=current_user.id,
        image_url=image_url,
    )

    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
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
        product: ProductCreate = Depends(ProductCreate.as_form),
        image: UploadFile | None = File(None),
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_seller)
):
    """
    Update product by ID
    """
    result = await db.scalars(select(ProductModel).where(ProductModel.id == product_id))
    db_product = result.first()
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found')
    if db_product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You can only update your own products')
    category_result = await db.scalars(
        select(CategoryModel).where(CategoryModel.id == product.category_id,
                                    CategoryModel.is_active == True)
    )
    if not category_result.first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,  detail='Category not found or inactive')

    await db.execute(
        update(ProductModel).where(ProductModel.id == product_id).values(**product.model_dump())
    )

    if image:
        remove_product_image(db_product.image_url)
        db_product.image_url = await save_product_image(image)

    await db.commit()
    await db.refresh(db_product)
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
    result = await db.scalars(
        select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    )
    product = result.first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found or inactive')
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You can only delete your own products')
    await db.execute(
        update(ProductModel).where(ProductModel.id == product_id).values(is_active=False)
    )
    remove_product_image(product.image_url)

    await db.commit()
    await db.refresh(product)
    return product
