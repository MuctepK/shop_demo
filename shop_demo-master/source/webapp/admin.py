from django.contrib import admin
from webapp.models import Product
from webapp.models import Order
from webapp.models import OrderProduct



class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'price')
    list_filter = ('category',)


class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    fields = ('product', 'amount')
    extra = 1


class OrderAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'phone', 'email', 'created_at')
    list_filter = ('status',)
    inlines = (OrderProductInline,)


admin.site.register(Product, ProductAdmin)

admin.site.register(Order, OrderAdmin)
