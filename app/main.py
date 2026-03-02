from fastapi import FastAPI

from app.routers import cart, categories, products, users


app = FastAPI(
    title='FastAPI Online-shop',
    version='0.1.0',
)

# Plug in categories routes
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(users.router)
app.include_router(cart.router)


# Root endpoint for health-check
@app.get('/')
async def root():
    """
    Root route, ensuring API is healthy.
    :return:
    """
    return {'message': 'Welcome!'}
