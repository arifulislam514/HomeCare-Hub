from django.forms import ValidationError
from django.shortcuts import get_object_or_404
from product.models import Product, Review, ProductImage
from product.serializers import ProductSerializer, ReviewSerializer, ProductImageSerializer
from django.db.models import Count
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from product.filters import ProductFilter
from rest_framework.filters import SearchFilter, OrderingFilter
from api.permissions import IsAdminOrReadOnly
from product.permissions import IsReviewAuthorOrReadonly
from drf_yasg.utils import swagger_auto_schema


class ProductViewSet(ModelViewSet):
    """
    API endpoint for managing products in the e-commerce store
     - Allows authenticated admin to create, update, and delete products
     - Allows users to browse and filter product
     - Support searching by name, description, and category
     - Support ordering by price and updated_at
    """
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'updated_at']
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        return Product.objects.prefetch_related('images').all()

    @swagger_auto_schema(
        operation_summary='Retrive a list of products'
    )
    def list(self, request, *args, **kwargs):
        """Retrive all the Services"""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a product by admin",
        operation_description="This allow an admin to create a product",
        request_body=ProductSerializer,
        responses={
            201: ProductSerializer,
            400: "Bad Request"
        }
    )
    def create(self, request, *args, **kwargs):
        """Only authenticated admin can create Service"""
        return super().create(request, *args, **kwargs)


class ProductImageViewSet(ModelViewSet):
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminOrReadOnly]

    def _product_id(self):
        return (
            self.kwargs.get("product__pk")   # <-- your router’s kwarg
            or self.kwargs.get("product_pk") # other router variants
            or self.kwargs.get("product_id") # plain path variant
        )

    def get_queryset(self):
        pid = self._product_id()
        return ProductImage.objects.filter(product_id=pid) if pid else ProductImage.objects.none()

    def perform_create(self, serializer):
        pid = self._product_id()
        if not pid:
            raise ValidationError({"detail": "Missing product id in URL."})
        get_object_or_404(Product, pk=pid)
        serializer.save(product_id=pid)


class ReviewViewSet(ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [IsReviewAuthorOrReadonly]

    def _product_id(self):
        return (
            self.kwargs.get("product__pk")
            or self.kwargs.get("product_pk")
            or self.kwargs.get("product_id")
        )

    def get_queryset(self):
        pid = self._product_id()
        return Review.objects.filter(product_id=pid) if pid else Review.objects.none()

    def get_serializer_context(self):
        return {"product_id": self._product_id()}

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, product_id=self._product_id())

    def perform_update(self, serializer):
        serializer.save(user=self.request.user, product_id=self._product_id())