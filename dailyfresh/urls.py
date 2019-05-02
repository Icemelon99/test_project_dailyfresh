
from django.contrib import admin
from django.urls import path, re_path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('tinymce/', include('tinymce.urls')),
    path('user/', include(('user.urls', 'user'), namespace='user')),
    path('cart/', include(('cart.urls', 'cart'), namespace='cart')),
    path('order/', include(('order.urls', 'order'), namespace='order')),
    re_path(r'^', include(('goods.urls', 'goods'), namespace='goods')), # 匹配商品模块(不加前缀并且由于匹配顺序放置在末端)
]
# 注意include()中元组