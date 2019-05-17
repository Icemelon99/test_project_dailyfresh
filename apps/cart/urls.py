from django.urls import path, re_path
from cart.views import CartAddView, CartInfoView, CartUpdateView, CartDeleteView

urlpatterns = [
	path('add/', CartAddView.as_view(), name='add'),
	path('info/', CartInfoView.as_view(), name='info'),
	path('update/', CartUpdateView.as_view(), name='update'),
	path('delete/', CartDeleteView.as_view(), name='delete'),
]