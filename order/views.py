from django.http import HttpResponseRedirect
from django.shortcuts import render
from decouple import config
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, DestroyModelMixin
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from order import serializers as orderSz
from order.serializers import CartSerializer, CartItemSerializer, AddCartItemSerializer, UpdateCartItemSerializer
from order.models import Cart, CartItem, Order, OrderItem
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from order.services import OrderService
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from sslcommerz_lib import SSLCOMMERZ 
# from django.conf import settings
from django.conf import settings as django_settings
from decimal import Decimal, InvalidOperation


class CartViewSet(CreateModelMixin, RetrieveModelMixin, DestroyModelMixin, GenericViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        Cart.objects.get_or_create(user=self.request.user)

    def create(self, request, *args, **kwargs):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(cart)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code)
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Cart.objects.none()
        return Cart.objects.prefetch_related('items__product').filter(user=self.request.user)


class CartItemViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AddCartItemSerializer
        elif self.request.method == 'PATCH':
            return UpdateCartItemSerializer
        return CartItemSerializer

    def get_serializer_context(self):
        print("Getting serializer context", self.kwargs)
        ctx = super().get_serializer_context()
        if getattr(self, 'swagger_fake_view', False):
            return ctx
        ctx.update({'cart_id': self.kwargs.get('cart__pk')})
        return ctx

    def get_queryset(self):
        return (CartItem.objects
                .select_related('product','cart')
                .filter(cart_id=self.kwargs.get('cart__pk'),
                        cart__user=self.request.user))

class OrderViewset(ModelViewSet):
    http_method_names = ['get', 'post', 'delete', 'patch', 'head', 'options']

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        OrderService.cancel_order(order=order, user=request.user)
        return Response({'status': 'Order canceled'})

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        order = self.get_object()
        serializer = orderSz.UpdateOrderSerializer(
            order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        new_status = serializer.validated_data.get('status', order.status)
        return Response({"status": f"Order status updated to {new_status}"})

    def get_permissions(self):
        if self.action in ['update_status', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'cancel':
            return orderSz.EmptySerializer
        if self.action == 'create':
            return orderSz.CreateOrderSerializer
        elif self.action == 'update_status':
            return orderSz.UpdateOrderSerializer
        return orderSz.OrderSerializer

    def get_serializer_context(self):
        if getattr(self, 'swagger_fake_view', False):
            return super().get_serializer_context()
        return {'user_id': self.request.user.id, 'user': self.request.user}

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        if self.request.user.is_staff:
            return Order.objects.prefetch_related('items__product').all()
        return Order.objects.prefetch_related('items__product').filter(user=self.request.user)
    
    
@api_view(['POST'])
def initiate_payment(request):
    if not request.user.is_authenticated:
        return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    
    user = request.user
    
    order_id     = request.data.get("order_id") or request.data.get("orderId")
    raw_amount   = request.data.get("amount")
    raw_numitems = request.data.get("num_items") or request.data.get("numItems")
    
    if not order_id:
        return Response({"error": "Missing order_id"}, status=status.HTTP_400_BAD_REQUEST)
    
    # 1) Fetch order FIRST (so we can safely refer to it later)
    try:
        order = Order.objects.prefetch_related('items').get(
            pk=order_id, user=user, status=Order.UNPAID
        )
    except Order.DoesNotExist:
        return Response({"error": "Invalid order"}, status=status.HTTP_400_BAD_REQUEST)

    # 2) Validate amount
    try:
        amount = Decimal(str(raw_amount))
    except (InvalidOperation, TypeError):
        return Response({"error": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

    if amount != order.total_price:
        return Response({"error": "Amount mismatch"}, status=status.HTTP_400_BAD_REQUEST)

    # 3) Validate num_items
    try:
        num_items = int(raw_numitems)
    except (TypeError, ValueError):
        return Response({"error": "Invalid or missing num_items"}, status=status.HTTP_400_BAD_REQUEST)

    if num_items != order.items.count():
        return Response({"error": "Item count mismatch"}, status=status.HTTP_400_BAD_REQUEST)

    # 4) SSLCommerz settings (you’re using decouple.config — keep it)
    ssl_settings = {
        'store_id':  config('store_id'),
        'store_pass': config('store_pass'),
        'issandbox': True
    }
    
    sslcz = SSLCOMMERZ(ssl_settings)
    
    # post_body = {}
    # post_body['total_amount'] = amount
    # post_body['currency'] = "BDT"
    # post_body['success_url'] = f"{settings.BACKEND_URL}/api/v1/payment/success/"
    # post_body['fail_url'] = f"{settings.BACKEND_URL}/api/v1/payment/fail/"
    # post_body['cancel_url'] = f"{settings.BACKEND_URL}/api/v1/payment/cancel/"
    # post_body['cancel_url'] = f"{settings.BACKEND_URL}/api/v1/payment/cancel/"
    # post_body['emi_option'] = 0
    # post_body['cus_name'] = f"{user.first_name} {user.last_name}"
    # post_body['cus_email'] = user.email
    # post_body['cus_phone'] = user.phone_number
    # post_body['cus_add1'] = user.address
    # post_body['cus_city'] = "Dhaka"
    # post_body['cus_country'] = "Bangladesh"
    # post_body['shipping_method'] = "Courier"
    # post_body['multi_card_name'] = ""
    # post_body['num_of_item'] = num_items
    # post_body['product_name'] = "E-commerce Products"
    # post_body['product_category'] = "General"
    # post_body['product_profile'] = "general"
    
     # 5) Build session payload (SSLCommerz likes strings for amounts)
    post_body = {
        'total_amount': str(order.total_price),
        'currency': "USD",
        'success_url': f"{django_settings.BACKEND_URL}/api/v1/payment/success/",
        'fail_url':    f"{django_settings.BACKEND_URL}/api/v1/payment/fail/",
        'cancel_url':  f"{django_settings.BACKEND_URL}/api/v1/payment/cancel/",
        'emi_option': 0,
        'cus_name':  (f"{user.first_name} {user.last_name}".strip() or user.username),
        'cus_email': user.email,
        'cus_phone': getattr(user, 'phone_number', '') or 'N/A',
        'cus_add1':  getattr(user, 'address', '') or 'N/A',
        'cus_city': "Dhaka",
        'cus_country': "Bangladesh",
        'shipping_method': "NO",
        'multi_card_name': "",
        'num_of_item': order.items.count(),
        'product_name': "E-commerce Products",
        'product_category': "General",
        'product_profile': "general",
        'tran_id': f"order_{order.id}",
    }

    # 6) Create session and return the redirect URL
    response = sslcz.createSession(post_body)
    if response.get("status") == "SUCCESS":
        return Response({"payment_url": response.get("GatewayPageURL")})
    return Response({"error": "Payment initiation failed"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def payment_success(request):
    print("Request Data:", request.data.get("tran_id"))
    order_id = request.data.get("tran_id").split('_')[1]
    order = Order.objects.get(id=order_id)
    order.status = "Pending"
    order.save()
    return HttpResponseRedirect(f"{django_settings.FRONTEND_URL}dashboard")


@api_view(['POST'])
def payment_cancel(request):
    return HttpResponseRedirect(f"{django_settings.FRONTEND_URL}dashboard")


@api_view(['POST'])
def payment_fail(request):
    print("Inside fail")
    return HttpResponseRedirect(f"{django_settings.FRONTEND_URL}dashboard")


# class HasOrderedProduct(api_view):
#     permission_classes = [IsAuthenticated]

#     def get(self, request, product_id):
#         user = request.user
#         has_ordered = OrderItem.objects.filter(
#             order__user=user, product_id=product_id).exists()
#         return Response({"hasOrdered": has_ordered})