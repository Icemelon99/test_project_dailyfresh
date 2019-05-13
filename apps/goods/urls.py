from django.urls import path, re_path
from goods.views import IndexView, DetailView

urlpatterns = [
	path('index/', IndexView.as_view(), name='index'),
	re_path(r'goods/(?P<goods_id>[0-9]+)', DetailView.as_view(), name='detail'),
]