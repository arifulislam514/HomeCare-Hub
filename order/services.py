from order.models import Cart, CartItem, OrderItem, Order
from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError
from decimal import Decimal


class OrderService:
    @staticmethod
    def create_order(user_id, cart_id):
        with transaction.atomic():
            cart = (
                Cart.objects
                .select_for_update()
                .select_related('user')
                .get(pk=cart_id, user_id=user_id)
            )
            cart_items = list(cart.items.select_related('product'))
            
            if not cart_items:
                raise ValidationError({"detail": "Cart is empty"})

            total_price = sum((item.product.price * item.quantity for item in cart_items), Decimal('0'))

            order = Order.objects.create(
                user_id=user_id, total_price=total_price)

            OrderItem.objects.bulk_create([
                OrderItem(
                    order=order,
                    product=item.product,
                    price=item.product.price,
                    quantity=item.quantity,
                    total_price=item.product.price * item.quantity
                ) for item in cart_items
            ])
            
            # clear cart items instead of deleting the cart row
            CartItem.objects.filter(cart=cart).delete()

            return order

    @staticmethod
    def cancel_order(order, user):
        if user.is_staff:
            order.status = Order.CANCELED
            order.save()
            return order

        if order.user != user:
            raise PermissionDenied(
                {"detail": "You can only cancel your own order"})

        if order.status == Order.DELIVERED:
            raise ValidationError({"detail": "You can not cancel an order"})

        order.status = Order.CANCELED
        order.save()
        return order
