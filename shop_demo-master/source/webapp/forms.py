from django import forms

from webapp.models import Product, Order, OrderProduct


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        exclude = ['in_stock']


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        exclude = ['created_at', 'updated_at', 'products', 'status', 'user']


class OrderProductForm(forms.ModelForm):
    class Meta:
        model = OrderProduct
        exclude = ['order']
