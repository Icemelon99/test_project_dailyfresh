from django.urls import path, re_path
from user.views import RegisterView, ActiveView, LoginView, UserOrderView, UserInfoView, UserAddressView, LogOutView

urlpatterns = [
	path('register/', RegisterView.as_view(), name='register'),
	re_path('^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),
	path('login/', LoginView.as_view(), name='login'),
	path('logout/', LogOutView.as_view(), name='logout'),
	path('', UserInfoView.as_view(), name='user'),
	re_path('order/(?P<page>[0-9]+)', UserOrderView.as_view(), name='order'),
	path('address/', UserAddressView.as_view(), name='address'),
]