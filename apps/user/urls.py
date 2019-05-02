from django.urls import path, re_path
from user import views

urlpatterns = [
	path('register/', views.register, name='register'),
]