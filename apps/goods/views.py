from django.shortcuts import render
from django.views import View
from django.core.cache import cache
from goods.models import GoodsType, GoodsSKU, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
from django_redis import get_redis_connection



class IndexView(View):
	'''首页'''
	def get(self, request):

		# 尝试先从缓存中读取数据
		context = cache.get('index_page_data')
		if context is None:
			print(context, '设置缓存')
			# 获取商品的种类信息
			types = GoodsType.objects.all()

			# 获取首页轮播商品信息
			goods_banners = IndexGoodsBanner.objects.all().order_by('index')

			# 获取首页促销活动信息
			promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

			# 获取首页分类商品展示信息，由于不同种类的商品展示信息存储在同一个表中，因此需要对其进行分类，并对每一个种类的商品信息进行查询
			for type in types:
				title_banners = IndexTypeGoodsBanner.objects.filter(types=type, display_type=0)
				image_banners = IndexTypeGoodsBanner.objects.filter(types=type, display_type=1)
				# 将获取到的每个种类的商品信息添加到种类的实例属性中，此中type是GoodType的实例，因此可以随意添加实例属性
				type.title_banners = title_banners
				type.image_banners = image_banners

			# 设置缓存，上述信息对每个用户都适用
			context = {
				'types': types,
				'goods_banners': goods_banners,
				'promotion_banners': promotion_banners,
			}
			cache.set('index_page_data', context, 60*15)

		# 获取用户购物车中商品数量
		user = request.user
		# 判断用户已登录
		if user.is_authenticated:
			conn = get_redis_connection('default')
			print(conn)
			cart_key = 'cart_{}'.format(user.id)
			cart_count = conn.hlen(cart_key)
		else:
			cart_count = 0

		# 组织模板上下文
		context.update(cart_count=cart_count) 
		return render(request, 'index.html', context)