from pydantic import BaseModel, Field, ConfigDict, EmailStr
from decimal import Decimal


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

