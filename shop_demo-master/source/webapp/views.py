from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.generic.base import View, TemplateView

from webapp.forms import ProductForm, OrderForm, OrderProductForm
from webapp.models import Product, Order, OrderProduct, ORDER_DELIVERED_STATUS, ORDER_NEW_STATUS, ORDER_CANCELLED_STATUS
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
        page_tuple = data.get(page, ())
        page_seconds = page_tuple[0] + seconds if page_tuple else 0 + seconds
        page_transitions = page_tuple[1] + 1 if page_tuple else 1
        data[page] = (page_seconds, page_transitions)

        total_seconds = request.session.get('total_seconds', 0)
        total_transitions = request.session.get('total_transitions', 0)
        request.session['total_seconds'] = total_seconds + seconds
        request.session['total_transitions'] = total_transitions + 1

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
    template_name = 'create.html'
    form_class = ProductForm
    permission_required = 'webapp.add_product'
    permission_denied_message = 'Доступ запрещен'

    def get_success_url(self):
        return reverse('webapp:product_detail', kwargs={'pk': self.object.pk})


class ProductUpdateView(PageTimerMixin,PermissionRequiredMixin, UpdateView):
    form_class = ProductForm
    model = Product
    template_name = 'update.html'
    permission_required = 'webapp.change_product'
    permission_denied_message = 'Доступ запрещен!'

    def get_success_url(self):
        return reverse('webapp:product_detail', kwargs={'pk': self.object.pk})


class ProductDeleteView(PageTimerMixin,PermissionRequiredMixin, DeleteView):
    model = Product
    template_name = 'delete.html'
    success_url = reverse_lazy('webapp:index')
    permission_required = 'webapp.delete_product'
    permission_denied_message = 'Доступ запрещен!'

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
        if self.request.user.is_authenticated:
            self.object.user = self.request.user
            self.object.save()
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


class OrderListView(PageTimerMixin, LoginRequiredMixin, ListView):
    model = Order
    template_name = 'order/order_list.html'

    def get_queryset(self):
        if self.request.user.has_perm('webapp.view_order'):
            return Order.objects.all().order_by('-created_at')
        else:
            return self.request.user.orders.all().order_by('-created_at')


class OrderCreateView(PermissionRequiredMixin, CreateView):
    model = Order
    fields = ('user', 'first_name', 'last_name', 'phone', 'email')
    template_name = 'create.html'
    permission_required = 'webapp.add_order'
    permission_denied_message = 'Доступ запрещен!'

    def get_success_url(self):
        return reverse('webapp:order_detail', kwargs={'pk': self.object.pk})


class OrderDetailView(PageTimerMixin, PermissionRequiredMixin, DetailView):
    model = Order
    template_name = 'order/order.html'
    context_object_name = 'order'
    permission_required = 'webapp.view_order'
    permission_denied_message = 'Доступ запрещен!'

    def has_permission(self):
        return super().has_permission() or self.get_object().user == self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['can_change_or_cancel'] =  self.can_change_or_edit(self.request.user)
        return context

    def can_change_or_edit(self, user):
        return user.has_perm('webapp.change_order') or self.is_creator_of_new_order(user)

    def is_creator_of_new_order(self,user):
        order = self.get_object()
        return order.user == user and order.status == ORDER_NEW_STATUS

class OrderUpdateView(PageTimerMixin,PermissionRequiredMixin, UpdateView):
    model = Order
    template_name = 'update.html'
    form_class = OrderForm
    extra_context = {'title':' Заказа'}

    permission_required = 'webapp.change_order'
    permission_denied_message = 'Доступ запрещен!'

    def has_permission(self):
        return super().has_permission() or self.is_creator_of_new_order(self.request.user)

    def is_creator_of_new_order(self,user):
        order = self.get_object()
        return order.user == user and order.status == ORDER_NEW_STATUS

    def get_success_url(self):
        return reverse('webapp:order_detail', kwargs={'pk': self.object.pk})


class OrderDeliverView(PermissionRequiredMixin, View):
    permission_required = 'webapp.deliver_order'
    permission_denied_message = 'Доступ запрещен!'

    def get(self, request, *args, **kwargs):
        print(kwargs)
        order_pk = kwargs.get('pk')
        order = Order.objects.get(pk=order_pk)
        order.status = ORDER_DELIVERED_STATUS
        order.save()
        return HttpResponseRedirect(reverse('webapp:order_detail', kwargs={"pk": order_pk}))


class OrderCancelView(PermissionRequiredMixin, View):
    permission_required = 'webapp.cancel_order'
    permission_denied_message = 'Доступ запрещен!'

    def has_permission(self):
        return super().has_permission() or self.is_creator_of_new_order(self.request.user)

    def is_creator_of_new_order(self,user):
        order = Order.objects.get(pk=self.kwargs.get('pk'))
        return order.user == user and order.status == ORDER_NEW_STATUS

    def get(self, request, *args, **kwargs):
        order_pk = kwargs.get('pk')
        order = Order.objects.get(pk=order_pk)
        order.status = ORDER_CANCELLED_STATUS
        order.save()
        return HttpResponseRedirect(reverse('webapp:order_detail', kwargs={"pk": order_pk}))


class OrderProductCreateView(PermissionRequiredMixin, CreateView):
    model = OrderProduct
    form_class = OrderProductForm
    template_name = 'create.html'
    permission_required = 'webapp.add_orderproduct'
    permission_denied_message = 'Доступ запрещен!'

    def form_valid(self, form):
        order = self.get_order()
        self.object = form.save(commit=False)
        self.object.order = order

        return super().form_valid(form)

    def get_order(self):
        return Order.objects.get(pk=self.kwargs.get('order_pk'))

    def get_success_url(self):
        return reverse('webapp:order_detail', kwargs={'pk': self.get_order().pk})


class OrderProductUpdateView(PermissionRequiredMixin, UpdateView):
    model = OrderProduct
    form_class = OrderProductForm
    template_name = 'update.html'
    permission_required = 'webapp.change_orderproduct'
    permission_denied_message = 'Доступ запрещен!'


    def get_success_url(self):
        return reverse('webapp:order_detail', kwargs={'pk': self.get_order().pk})

    def get_order(self):
        return Order.objects.get(pk=self.kwargs.get('order_pk'))


class OrderProductDeleteView(PermissionRequiredMixin, DeleteView):
    model = OrderProduct
    template_name = 'delete.html'
    permission_required = 'webapp.delete_orderproduct'
    permission_denied_message = 'Доступ запрещен!'

    def get_success_url(self):
        return reverse('webapp:order_detail', kwargs={'pk': self.get_order().pk})

    def get_order(self):
        return Order.objects.get(pk=self.kwargs.get('order_pk'))