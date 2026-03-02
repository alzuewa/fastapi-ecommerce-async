import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth import hash_password, verify_password, create_access_token, create_refresh_token
from app.config import SECRET_KEY, ALGORITHM
from app.db_depends import get_async_db
from app.models.users import User as UserModel
from app.schemas import UserCreate, User as UserSchema, RefreshTokenRequest


router = APIRouter(prefix='/users', tags=['users'])

@router.post('/', response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Register new user with 'buyer' or 'seller' role
    """

    # Check email for uniqueness
    result = await db.scalars(select(UserModel).where(UserModel.email == user.email))
    if result.first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email already registered')

    # Create user object with hashed pass
    db_user = UserModel(
        email=user.email,
        hashed_password=hash_password(user.password),
        role=user.role
    )

    # Adding to DB session and storing in DB
    db.add(db_user)
    await db.commit()
    return db_user

@router.post('/token')
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_async_db)):
    """
    Authenticates user and return JWT access and refresh token.
    """
    result = await db.scalars(
        select(UserModel).where(UserModel.email == form_data.username, UserModel.is_active == True))
    user = result.first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect email or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    access_token = create_access_token(data={'sub': user.email, 'role': user.role, 'id': user.id})
    refresh_token = create_refresh_token(data={'sub': user.email, 'role': user.role, 'id': user.id})
    return {'access_token': access_token, 'refresh_token': refresh_token, 'token_type': 'bearer'}

@router.post('/refresh-token')
async def refresh_token(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Updates refresh-token accepting current refresh-token in request body
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate refresh token',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    old_refresh_token = body.refresh_token

    try:
        payload = jwt.decode(old_refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get('sub')
        token_type: str | None = payload.get('token_type')

        # Check that token has refresh type
        if email is None or token_type != 'refresh':
            raise credentials_exception

    except jwt.ExpiredSignatureError:
        # refresh-token expired
        raise credentials_exception
    except jwt.PyJWTError:
        # signature is invalid or token is corrupted
        raise credentials_exception

    # Check that user exists and active
    result = await db.scalars(
        select(UserModel).where(
            UserModel.email == email,
            UserModel.is_active == True
        )
    )
    user = result.first()
    if user is None:
        raise credentials_exception

    # Generate new refresh-token
    new_refresh_token = create_refresh_token(
        data={'sub': user.email, 'role': user.role, 'id': user.id}
    )

    return {
        'refresh_token': new_refresh_token,
        'token_type': 'bearer',
    }
