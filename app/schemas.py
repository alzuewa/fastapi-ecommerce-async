from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict, EmailStr



class CategoryCreate(BaseModel):
    """
    Model to create and update category
    """
    name: str = Field(..., min_length=3, max_length=50, description='Category name (3-50 symbols)')
    parent_id: int | None = Field(None, description='Parent category ID if any')


class Category(BaseModel):
    """
    Category response model
    """
    id: int = Field(..., description='Unique category ID')
    name: str = Field(..., description='Category name')
    parent_id: int | None = Field(None, description='Parent category ID if any')
    is_active: bool = Field(..., description='Is the category active')

    model_config = ConfigDict(from_attributes=True)  # ensures compatibility with ORM


class ProductCreate(BaseModel):
    """
    Model to create and update product
    """
    name: str = Field(..., min_length=3, max_length=100, description='Product name (3-100 symbols)')
    description: str | None = Field(None, max_length=500, description='Product description (up to 500 symbols)')
    price: Decimal = Field(..., gt=0, description='Product price', decimal_places=2)
    image_url: str | None = Field(None, max_length=200, description='Product image URL')
    stock: int = Field(..., ge=0, description='Available product items number')
    category_id: int = Field(..., description='Product category ID')


class Product(BaseModel):
    """
    Product response model
    """
    id: int = Field(..., description='Unique product ID')
    name: str = Field(..., description='Product name')
    description: str | None = Field(None, description='Product description')
    price: Decimal = Field(..., description='Product price', gt=0, decimal_places=2)
    image_url: str | None = Field(None, description='Product image URL')
    stock: int = Field(..., description='Available product items number')
    category_id: int = Field(..., description='Category ID')
    is_active: bool = Field(..., description='Is the product active')

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr = Field(description="Email пользователя")
    password: str = Field(min_length=8, description="Пароль (минимум 8 символов)")
    role: str = Field(default="buyer", pattern="^(buyer|seller)$", description="Роль: 'buyer' или 'seller'")


class User(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    role: str
    model_config = ConfigDict(from_attributes=True)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ProductList(BaseModel):
    """
    Products list for pagination
    """
    items: list[Product] = Field(description='Current page products')
    total: int = Field(ge=0, description='Total products number')
    page: int = Field(ge=1, description='Current page number')
    page_size: int = Field(ge=1, description='Items number on the page')

    model_config = ConfigDict(from_attributes=True)  # for reading from ORM-objects


class CartItemBase(BaseModel):
    product_id: int = Field(description='Product ID')
    quantity: int = Field(ge=1, description='Product items number')


class CartItemCreate(CartItemBase):
    """
    Model to add a new product to a cart.
    """
    pass


class CartItemUpdate(BaseModel):
    """
    Model to update product quantity in a cart.
    """
    quantity: int = Field(..., ge=1, description='Updated quantity')


class CartItem(BaseModel):
    """
    Product in cart with product data.
    """
    id: int = Field(..., description='Cart item ID')
    quantity: int = Field(..., ge=1, description='Item quantity')
    product: Product = Field(..., description='Item data')

    model_config = ConfigDict(from_attributes=True)


class Cart(BaseModel):
    """
    Full user cart data
    """
    user_id: int = Field(..., description='User ID')
    items: list[CartItem] = Field(default_factory=list, description='Cart contents')
    total_quantity: int = Field(..., ge=0, description='Total products amount')
    total_price: Decimal = Field(..., ge=0, description='Total cart price')

    model_config = ConfigDict(from_attributes=True)


class OrderItem(BaseModel):
    id: int = Field(..., description='Item position ID')
    product_id: int = Field(..., description='Product ID')
    quantity: int = Field(..., ge=1, description='Quantity')
    unit_price: Decimal = Field(..., ge=0, description='Price per item')
    total_price: Decimal = Field(..., ge=0, description='Total price for item')
    product: Product | None = Field(None, description='Full item data')

    model_config = ConfigDict(from_attributes=True)


class Order(BaseModel):
    id: int = Field(..., description='Order ID')
    user_id: int = Field(..., description='User ID')
    status: str = Field(..., description='Current order status')
    total_amount: Decimal = Field(..., ge=0, description='Total price')
    created_at: datetime = Field(..., description='Order created at')
    updated_at: datetime = Field(..., description='Order last updated at')
    items: list[OrderItem] = Field(default_factory=list, description='Order items list')

    model_config = ConfigDict(from_attributes=True)


class OrderList(BaseModel):
    items: list[Order] = Field(..., description='Orders on the current page')
    total: int = Field(ge=0, description='Total orders amount')
    page: int = Field(ge=1, description='Current page')
    page_size: int = Field(ge=1, description='Page size')

    model_config = ConfigDict(from_attributes=True)