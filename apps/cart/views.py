from django.shortcuts import render, redirect, HttpResponse
from django.urls import reverse
from django.views import View
from django.urls import reverse
from django.http import JsonResponse
from django_redis import get_redis_connection
from goods.models import GoodsSKU
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin

# 前端采用ajax post传递参数，传递商品id(sku_id),商品数量(count)，并接收Json对象
class CartAddView(View):
	'''添加购物车记录'''
	def post(self, request):
		# 判断用户是否登录
		user = request.user
		if not user.is_authenticated:
			return JsonResponse({'res':0, 'errmsg':'请先登录'})

		# 接收数据，用post方法因此不在定义函数中以形参出现
		sku_id = request.POST.get('sku_id')
		count = request.POST.get('count')

		# 校验数据合法性
		if not all([sku_id, count]):
			return JsonResponse({'res':1, 'errmsg':'数据不完整'})
		# 校验商品数量合法性
		try:
			count = int(count)
		except Exception:
			return JsonResponse({'res':2, 'errmsg':'数目出错'})
		# 校验商品是否存在
		try:
			sku = GoodsSKU.objects.get(id=sku_id)
		except GoodsSKU.DoesNotExist:
			return JsonResponse({'res':3, 'errmsg':'商品不存在'})
		# 添加到购物车，链接到redis数据库
		conn = get_redis_connection('default')
		cart_key = 'cart_{}'.format(user.id)
		# 检索该商品是否已存在，若sku_id在此hash中不存在则返回None
		cart_count = conn.hget(cart_key, sku_id)
		if cart_count:
			count += int(cart_count)
		# 校验库存值，设置对应值
		if count>sku.stock:
			return JsonResponse({'res':4, 'errmsg':'商品库存不足'})
		conn.hset(cart_key, sku_id, count)

		# 计算用户当前购物车条目数
		total_count = conn.hlen(cart_key)

		return JsonResponse({'res':5, 'message':'添加成功', 'total_count':total_count})


class CartInfoView(LoginRequiredMixin, View):
	'''购物车页面显示'''
	def get(self, request):
		# 获取用户购物车中商品的信息
		user = request.user
		conn = get_redis_connection('default')
		cart_key = 'cart_{}'.format(user.id)
		# 从数据库中获取购物车字典，{商品id1:数量, 商品id2:数量}
		cart_dict = conn.hgetall(cart_key)
		skus = list()
		total_count = 0
		total_price = 0
		for sku_id, count in cart_dict.items():
			# 根据商品id获取商品信息
			sku = GoodsSKU.objects.get(id=sku_id)
			# 计算商品的小计价格
			amount = sku.price*int(count)
			# 动态为sku增加属性,小计和数量,并添加到列表中
			sku.amount = amount
			sku.count = int(count)
			skus.append(sku)
			total_count += int(count)
			total_price += amount
		# 组织模板上下文
		context = {
			'skus': skus,
			'total_price': total_price,
			'total_count': total_count,
		}

		return render(request, 'cart.html', context)

# 购物车中数据的更新，因为是ajax post请求，不能使用LoginRequiredMixin，无法跳转
# /cart/update
class CartUpdateView(View):
	'''购物车记录更新'''
	def post(self, request):
		# 判断用户是否登录
		user = request.user
		if not user.is_authenticated:
			return JsonResponse({'res':0, 'errmsg':'请先登录'})
		# 接收数据
		sku_id = request.POST.get('sku_id')
		count = request.POST.get('count')
		# 校验数据合法性
		if not all([sku_id, count]):
			return JsonResponse({'res':1, 'errmsg':'数据不完整'})
		# 校验商品数量合法性
		try:
			count = int(count)
		except Exception:
			return JsonResponse({'res':2, 'errmsg':'数目出错'})
		# 校验商品是否存在
		try:
			sku = GoodsSKU.objects.get(id=sku_id)
		except GoodsSKU.DoesNotExist:
			return JsonResponse({'res':3, 'errmsg':'商品不存在'})
		# 更新redis数据库中记录
		conn = get_redis_connection('default')
		cart_key = 'cart_{}'.format(user.id)
		# 校验库存值，设置对应值
		if count>sku.stock:
			return JsonResponse({'res':4, 'errmsg':'商品库存不足'})
		conn.hset(cart_key, sku_id, count)
		# 更新商品的总件数
		vals = conn.hvals(cart_key)
		total_count = sum([int(x) for x in vals])

		# 返回应答
		return JsonResponse({'res':5, 'total_count':total_count, 'message':'更新成功'})

# /cart/delete
class CartDeleteView(View):
	'''购物车记录删除'''
	def post(self, request):
		# 判断用户是否登录
		user = request.user
		if not user.is_authenticated:
			return JsonResponse({'res':0, 'errmsg':'请先登录'})
		# 接收数据
		sku_id = request.POST.get('sku_id')
		# 数据校验
		if not sku_id:
			return JsonResponse({'res':1, 'errmsg':'无效的商品ID'})
		# 校验商品是否存在
		try:
			sku = GoodsSKU.objects.get(id=sku_id)
		except GoodsSKU.DoesNotExist:
			return JsonResponse({'res':2, 'errmsg':'商品不存在'})
		# 更新redis数据库中记录
		conn = get_redis_connection('default')
		cart_key = 'cart_{}'.format(user.id)
		conn.hdel(cart_key, sku_id)
		# 更新商品的总件数
		vals = conn.hvals(cart_key)
		total_count = sum([int(x) for x in vals])
		# 返回应答
		return JsonResponse({'res':3, 'total_count':total_count, 'message':'删除成功'})