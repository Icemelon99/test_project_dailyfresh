from django.urls import path, re_path
from goods import views

urlpatterns = [
	path('', views.index, name='index'),
]