from django.urls import path, re_path
from order.views import OrderPlaceView, OrderCommitView, OrderPayView, OrderCheckView, OrderCommentView

urlpatterns = [
	path('place/', OrderPlaceView.as_view(), name='place'),
	path('commit/', OrderCommitView.as_view(), name='commit'),
	path('pay/', OrderPayView.as_view(), name='pay'),
	path('check/', OrderCheckView.as_view(), name='check'),
	re_path('comment/(?P<order_id>[0-9]+)', OrderCommentView.as_view(), name='comment'),
]