from django.urls import path, re_path
from order.views import OrderPlaceView, OrderCommitView

urlpatterns = [
	path('place/', OrderPlaceView.as_view(), name='place'),
	path('commit/', OrderCommitView.as_view(), name='commit'),
]