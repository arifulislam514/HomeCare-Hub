from django.urls import path, include
from product.views import ProductViewSet, ReviewViewSet, ProductImageViewSet
from order.views import CartViewSet, CartItemViewSet, OrderViewset, initiate_payment, payment_cancel, payment_fail, payment_success
from users.views import UserViewSet
from rest_framework_nested import routers

router = routers.DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register('products', ProductViewSet, basename='products')
router.register('carts', CartViewSet, basename='carts')
router.register('orders', OrderViewset, basename='orders')

product_router = routers.NestedSimpleRouter(
    router, 'products', lookup='product')
product_router.register('reviews', ReviewViewSet, basename='product-review')
product_router.register('images', ProductImageViewSet,
                        basename='product-images')

cart_router = routers.NestedSimpleRouter(router, 'carts', lookup='cart')
cart_router.register('items', CartItemViewSet, basename='cart-item')

# urlpatterns = router.urls

urlpatterns = [
    path('', include(router.urls)),
    path('', include(product_router.urls)),
    path('', include(cart_router.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    path('', include(router.urls)),
    path('payment/initiate/',initiate_payment, name='initiate-payment'),
    path("payment/initiate/", initiate_payment, name="initiate-payment"),
    path("payment/success/", payment_success, name="payment-success"),
    path("payment/fail/", payment_fail, name="payment-fail"),
    path("payment/cancel/", payment_cancel, name="payment-cancel"),
]