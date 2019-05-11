from django.urls import path, re_path
from goods.views import IndexView

urlpatterns = [
	path('', IndexView.as_view(), name='index'),
]