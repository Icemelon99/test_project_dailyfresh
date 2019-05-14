from django.urls import path, re_path
from django.conf.urls import url
from goods.views import IndexView, DetailView, ListView

urlpatterns = [
	path('index/', IndexView.as_view(), name='index'),
	re_path(r'goods/(?P<goods_id>[0-9]+)$', DetailView.as_view(), name='detail'),
	re_path(r'list/(?P<type_id>[0-9]+)/(?P<page>[0-9]+)', ListView.as_view(), name='list'),

]