from django import forms

from webapp.models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        exclude = ['in_stock']
