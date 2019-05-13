from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.core.cache import cache
from goods.models import GoodsType, GoodsSKU, GoodsSPU, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
from order.models import OrderGoods
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


class DetailView(View):
	'''商品详情页面'''
	def get(self, request, goods_id):
		# 尝试获取ID
		try:
			sku = GoodsSKU.objects.get(id=goods_id)
		except GoodsSKU.DoesNotExit:
			# 所查商品不存在，返回一个页面
			return redirect(reverse(' goods:index '))

		# 获取商品的分类信息
		types = GoodsType.objects.all()

		# 获取商品的评论信息，[对评论内容进行筛选]
		sku_orders = OrderGoods.objects.filter(sku=sku)

		# 获取该种类新品，通过创建时间排序，并切片取前两个
		new_skus = GoodsSKU.objects.filter(types=sku.types).order_by('-create_time')[:2]
		# 获取同一个SPU其他规格的商品
		same_spu_skus = GoodsSKU.objects.filter(spu=sku.spu).exclude(id=goods_id)

		# 获取用户购物车中商品数量
		user = request.user
		# 判断用户已登录
		if user.is_authenticated:
			conn = get_redis_connection('default')
			cart_key = 'cart_{}'.format(user.id)
			cart_count = conn.hlen(cart_key)
			# 添加历史浏览记录
			history_key = 'history_{}'.format(user.id)
			# 对历史浏览记录是否重复进行判断和移除
			conn.lrem(history_key, 0, goods_id)
			# 添加当前的商品ID
			conn.lpush(history_key, goods_id)
			# 设置只保存用户最新浏览的5条信息
			conn.ltrim(history_key, 0, 4)

		else:
			cart_count = 0
		# 此处应该设置登录后跳转回原链接

		# 组织模板上下文
		context = {
			'sku': sku,
			'types': types,
			'sku_orders': sku_orders,
			'new_skus': new_skus,
			'cart_count': cart_count,
			'same_spu_skus': same_spu_skus,
		}

		return render(request, 'detail.html', context)