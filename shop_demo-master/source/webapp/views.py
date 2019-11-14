from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.generic.base import View, TemplateView

from webapp.forms import ProductForm
from webapp.models import Product, Order, OrderProduct
from datetime import datetime, timedelta


class PageTimerMixin:

    def get_previous_page(self, request):
        return request.session.get('timer')

    def set_timer(self, request):
        request.session['timer'] = request.path, self.get_current_time()

    def get_current_time(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def find_difference(self, time):
        time_str = time
        old_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        diff = datetime.now() - old_time
        return diff.total_seconds()

    def update_stats(self, request, page, seconds):
        data = request.session.get('stats', {})
        page = page
        page_seconds = data.get(page, 0)
        data[page] = page_seconds + seconds

        total = request.session.get('total_seconds', 0)
        request.session['total_seconds'] = total + seconds

        request.session['stats'] = data

    def dispatch(self, request, *args, **kwargs):
        if request.session.get('timer'):
            page, time = self.get_previous_page(request)
            seconds = self.find_difference(time)
            self.update_stats(request, page, seconds)
        self.set_timer(request)
        print(request.session.get('stats'))
        return super().dispatch(request)


class IndexView(PageTimerMixin, ListView):
    model = Product
    template_name = 'index.html'
    page_name = 'Главная'

    def get_queryset(self):
        return super().get_queryset().filter(in_stock=True)


class ProductView(PageTimerMixin, DetailView):
    model = Product
    template_name = 'product/detail.html'


class ProductCreateView(PageTimerMixin,PermissionRequiredMixin, CreateView):
    model = Product
    template_name = 'product/create.html'
    form_class = ProductForm
    success_url = reverse_lazy('webapp:index')
    permission_required = 'webapp.add_product'
    permission_denied_message = 'Доступ запрещен'


class ProductUpdateView(PageTimerMixin, UpdateView):
    form_class = ProductForm
    model = Product
    template_name = 'update.html'
    success_url = reverse_lazy('webapp:index')


class ProductDeleteView(PageTimerMixin, DeleteView):
    model = Product
    template_name = 'delete.html'
    success_url = reverse_lazy('webapp:index')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.in_stock = False
        self.object.save()
        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)


class BasketChangeView(View):
    def get(self, request, *args, **kwargs):
        products = request.session.get('products', [])

        pk = request.GET.get('pk')
        action = request.GET.get('action')
        next_url = request.GET.get('next', reverse('webapp:index'))

        if action == 'add':
            products.append(pk)
        else:
            for product_pk in products:
                if product_pk == pk:
                    products.remove(product_pk)
                    break

        request.session['products'] = products
        request.session['products_count'] = len(products)

        return redirect(next_url)


class BasketView(PageTimerMixin, CreateView):
    model = Order
    fields = ('first_name', 'last_name', 'phone', 'email')
    template_name = 'product/basket.html'
    success_url = reverse_lazy('webapp:index')

    def get_context_data(self, **kwargs):
        basket, basket_total = self._prepare_basket()
        kwargs['basket'] = basket
        kwargs['basket_total'] = basket_total
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        if self._basket_empty():
            form.add_error(None, 'В корзине отсутствуют товары!')
            return self.form_invalid(form)
        response = super().form_valid(form)
        self._save_order_products()
        self._clean_basket()
        return response

    def _prepare_basket(self):
        totals = self._get_totals()
        basket = []
        basket_total = 0
        for pk, qty in totals.items():
            product = Product.objects.get(pk=int(pk))
            total = product.price * qty
            basket_total += total
            basket.append({'product': product, 'qty': qty, 'total': total})
        return basket, basket_total

    def _get_totals(self):
        products = self.request.session.get('products', [])
        totals = {}
        for product_pk in products:
            if product_pk not in totals:
                totals[product_pk] = 0
            totals[product_pk] += 1
        return totals

    def _basket_empty(self):
        products = self.request.session.get('products', [])
        return len(products) == 0

    def _save_order_products(self):
        totals = self._get_totals()
        for pk, qty in totals.items():
            OrderProduct.objects.create(product_id=pk, order=self.object, amount=qty)

    def _clean_basket(self):
        if 'products' in self.request.session:
            self.request.session.pop('products')
        if 'products_count' in self.request.session:
            self.request.session.pop('products_count')


class OrderListView(PageTimerMixin, ListView):
    model = Order
    template_name = 'order/order_list.html'


class OrderDetailView(PageTimerMixin, DetailView):
    model = Order
    template_name = 'order/order.html'
    context_object_name = 'order'