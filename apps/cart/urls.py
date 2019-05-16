from django.urls import path, re_path
from cart.views import CartAddView, CartInfoView

urlpatterns = [
	path('add/', CartAddView.as_view(), name='add'),
	path('info/', CartInfoView.as_view(), name='info'),
]