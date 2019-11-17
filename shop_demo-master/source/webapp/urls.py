from django.urls import path
from .views import IndexView, ProductView, ProductCreateView, BasketChangeView, BasketView, ProductUpdateView, \
    ProductDeleteView, OrderListView, OrderDetailView, OrderUpdateView, OrderDeliverView, OrderCancelView, \
    OrderProductCreateView, OrderProductUpdateView, OrderProductDeleteView, OrderCreateView

app_name = 'webapp'

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('products/<int:pk>/', ProductView.as_view(), name='product_detail'),
    path('products/create/', ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/update/', ProductUpdateView.as_view(), name='product_update'),
    path('products/<int:pk>/delete', ProductDeleteView.as_view(), name='product_delete'),
    path('basket/change/', BasketChangeView.as_view(), name='basket_change'),
    path('basket/', BasketView.as_view(), name='basket'),
    path('orders/', OrderListView.as_view(), name='orders'),
    path('orders/create/', OrderCreateView.as_view(), name='order_create'),
    path('orders/<int:pk>', OrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/update/', OrderUpdateView.as_view(), name='order_update'),
    path('orders/<int:pk>/deliver/', OrderDeliverView.as_view(), name ='order_deliver'),
    path('orders/<int:pk>/cancel/', OrderCancelView.as_view(), name ='order_cancel'),
    path('orders/<int:order_pk>/add', OrderProductCreateView.as_view(), name ='order_product_add'),
    path('orders/<int:order_pk>/change/<int:pk>', OrderProductUpdateView.as_view(), name = 'order_product_update'),
    path('orders/<int:order_pk>/delete/<int:pk>', OrderProductDeleteView.as_view(), name = 'order_product_delete')
]
