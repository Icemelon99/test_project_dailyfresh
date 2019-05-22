from django.shortcuts import render, redirect, HttpResponse
from django.urls import reverse
from django.http import JsonResponse
from django.views import View
from django_redis import get_redis_connection
from django.conf import settings
from django.db import transaction
from goods.models import GoodsSKU
from order.models import OrderInfo, OrderGoods
from user.models import Address
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import datetime
from alipay import AliPay
import os
import time

class OrderPlaceView(LoginRequiredMixin, View):
	'''提交订单页面展示'''
	def post(self, request):
		user = request.user
		sku_ids = request.POST.getlist('sku_ids')
		# 校验参数
		if not sku_ids:
			# 跳转到购物车页面
			return redirect(reverse('cart:info'))
		# 获取用户要购买的商品信息
		conn = get_redis_connection('default')
		cart_key = 'cart_{}'.format(user.id)
		#要传入的参数
		skus = list()
		total_count = 0
		total_price = 0
		for sku_id in sku_ids:
			# 根据商品的id获取商品信息
			sku = GoodsSKU.objects.get(id=sku_id)
			count = conn.hget(cart_key, sku_id)
			# 计算商品的小计
			amount = sku.price*int(count)
			# 动态增加商品的数量和小计
			sku.count = int(count)
			sku.amount = amount
			skus.append(sku)
			total_count += int(count)
			total_price += amount
		# 运费实际开发中是有一个单独的表/子系统，此处固定
		transit_price = 10
		# 实付款
		total_pay = total_price + transit_price
		# 获取用户的收件地址
		addrs = Address.objects.filter(user=user)
		# 传入选中的sku_ids用于订单提交
		sku_ids = ','.join(sku_ids)
		# 组织上下文
		context = {
			'skus': skus,
			'total_count': total_count,
			'total_price': total_price,
			'transit_price': transit_price,
			'total_pay': total_pay,
			'addrs': addrs,
			'sku_ids': sku_ids,
		}

		return render(request, 'place_order.html', context)


# /order/commit 前端传递的参数有地址，支付方式，商品ID，悲观锁
class OrderCommitView1(View):
	'''订单提交创建'''
	@transaction.atomic
	def post(self, request):
		# 判断用户是否登录
		user = request.user
		if not user.is_authenticated:
			return JsonResponse({'res':0, 'errmsg':'请先登录'})
		# 获取参数
		addr_id = request.POST.get('addr_id')
		pay_method = request.POST.get('pay_method')
		sku_ids = request.POST.get('sku_ids')
		# 校验参数
		if not all([addr_id, pay_method, sku_ids]):
			return JsonResponse({'res':1, 'errmsg':'数据不完整'})
		# 校验支付方式
		if pay_method not in OrderInfo.PAY_METHOD.keys():
			return JsonResponse({'res':2, 'errmsg':'非法的支付方式'})
		# 校验地址
		try:
			addr = Address.objects.get(id=addr_id)
		except Address.DoesNotExist:
			return JsonResponse({'res':3, 'errmsg':'地址不存在'})
		# 创建订单核心业务
		# 创建订单信息缺少的内容
		# 订单ID，使用年月日时分秒+用户ID创建订单编号
		order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)
		# 运费
		transit_price = 10
		# 总数目和总金额,添加记录，先使用默认值，后续修改
		total_count = 0
		total_price = 0
		# 添加数据库事务的保存点
		save_id = transaction.savepoint()
		try:
			# 向订单信息表中添加记录
			order = OrderInfo.objects.create(order_id=order_id,
									 		 user=user,
											 addr=addr,
											 pay_method=pay_method,
											 transit_price=transit_price,
											 total_price=total_price,
											 total_count=total_count)
			# 获取订单商品表的参数
			conn = get_redis_connection('default')
			cart_key = 'cart_{}'.format(user.id)
			sku_ids = sku_ids.split(',')
			for sku_id in sku_ids:
				try:
					# 添加悲观锁
					sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
				except GoodsSKU.DoesNotExist:
					# 回滚到保存点，此处的回滚是为了撤销已创建的表
					transaction.savepoint_rollback(save_id)
					return JsonResponse({'res':4, 'errmsg':'商品不存在'})
				print('user:{} stock:{}'.format(user.id, sku.stock))
				time.sleep(10)
				# 获取商品的数量
				count = conn.hget(cart_key, sku_id)
				# 校验库存值
				if int(count)>sku.stock:
					# 回滚到保存点
					transaction.savepoint_rollback(save_id)
					return JsonResponse({'res':5, 'errmsg':'商品库存不足'})
				# 向订单商品表中添加记录
				OrderGoods.objects.create(order=order,
										  sku=sku,
										  count=count,
										  price=sku.price)
				# 更新相关商品的销量和库存
				sku.stock -= int(count)
				sku.sales += int(count)
				sku.save()
				# 计算订单商品的总数量和总价格
				amount = sku.price*int(count)
				total_count += int(count)
				total_price += amount
			# 更新订单详情表中的总数量和总价格
			order.total_count = total_count
			order.total_price = total_price
			order.save()
			# 清除用户购物车中的记录
			conn.hdel(cart_key, *sku_ids)
		except Exception:
			transaction.savepoint_rollback(save_id)
			return JsonResponse({'res':7, 'errmsg':'订单创建失败'})
		# 提交事务，返回应答
		transaction.savepoint_commit(save_id)
		return JsonResponse({'res':6, 'message':'订单创建成功'})			


# /order/commit 前端传递的参数有地址，支付方式，商品ID，乐观锁
class OrderCommitView(View):
	'''订单提交创建'''
	@transaction.atomic
	def post(self, request):
		# 判断用户是否登录
		user = request.user
		if not user.is_authenticated:
			return JsonResponse({'res':0, 'errmsg':'请先登录'})
		# 获取参数
		addr_id = request.POST.get('addr_id')
		pay_method = int(request.POST.get('pay_method'))
		sku_ids = request.POST.get('sku_ids')
		# 校验参数
		if not all([addr_id, pay_method, sku_ids]):
			return JsonResponse({'res':1, 'errmsg':'数据不完整'})
		# 校验支付方式
		if pay_method not in OrderInfo.PAY_METHOD.keys():
			print(pay_method, type(pay_method))
			return JsonResponse({'res':2, 'errmsg':'非法的支付方式'})
		# 校验地址
		try:
			addr = Address.objects.get(id=addr_id)
		except Address.DoesNotExist:
			return JsonResponse({'res':3, 'errmsg':'地址不存在'})
		# 创建订单核心业务
		# 创建订单信息缺少的内容
		# 订单ID，使用年月日时分秒+用户ID创建订单编号
		order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)
		# 运费
		transit_price = 10
		# 总数目和总金额,添加记录，先使用默认值，后续修改
		total_count = 0
		total_price = 0
		# 添加数据库事务的保存点
		save_id = transaction.savepoint()
		try:
			# 向订单信息表中添加记录
			order = OrderInfo.objects.create(order_id=order_id,
									 		 user=user,
											 addr=addr,
											 pay_method=pay_method,
											 transit_price=transit_price,
											 total_price=total_price,
											 total_count=total_count)
			if order.pay_method == 1:
				order.order_status = 2
				order.save()
			# 获取订单商品表的参数
			conn = get_redis_connection('default')
			cart_key = 'cart_{}'.format(user.id)
			sku_ids = sku_ids.split(',')
			for sku_id in sku_ids:
				for i in range(3):
					try:
						sku = GoodsSKU.objects.get(id=sku_id)
					except GoodsSKU.DoesNotExist:
						# 回滚到保存点，此处的回滚是为了撤销已创建的表
						transaction.savepoint_rollback(save_id)
						return JsonResponse({'res':4, 'errmsg':'商品不存在'})
					# 获取商品的数量
					count = conn.hget(cart_key, sku_id)
					# 校验库存值
					if int(count)>sku.stock:
						# 回滚到保存点
						transaction.savepoint_rollback(save_id)
						return JsonResponse({'res':5, 'errmsg':'商品库存不足'})
					# 保存原库存与新库存
					origin_stock = sku.stock
					new_stock = origin_stock - int(count)
					new_sales = sku.sales + int(count)
					print('user:{} times:{} stock:{}'.format(user.id, i, sku.stock))
					# 返回受影响的行数，0/1
					res = GoodsSKU.objects.filter(id=sku_id, stock=origin_stock).update(stock=new_stock, sales=new_sales)
					if res == 0:
						if i == 2:
							transaction.savepoint_rollback(save_id)
							return JsonResponse({'res':7, 'errmsg':'订单创建失败'})
						continue
					# 向订单商品表中添加记录，由于此处并没有设置保存点，因此将判断放在添加记录的前面，防止重复添加
					OrderGoods.objects.create(order=order,
											  sku=sku,
											  count=count,
											  price=sku.price)
					# 更新相关商品的销量和库存
					sku.stock -= int(count)
					sku.sales += int(count)
					sku.save()
					# 计算订单商品的总数量和总价格
					amount = sku.price*int(count)
					total_count += int(count)
					total_price += amount
					break
			# 更新订单详情表中的总数量和总价格
			order.total_count = total_count
			order.total_price = total_price
			order.save()
			# 清除用户购物车中的记录
			conn.hdel(cart_key, *sku_ids)
		except Exception:
			transaction.savepoint_rollback(save_id)
			return JsonResponse({'res':7, 'errmsg':'订单创建失败'})
		# 提交事务，返回应答
		transaction.savepoint_commit(save_id)
		return JsonResponse({'res':6, 'message':'订单创建成功'})			

# 前端ajax post传递参数
class OrderPayView(View):
	def post(self, request):
		# 校验参数
		user = request.user
		if not user.is_authenticated:
			return JsonResponse({'res':0, 'errmsg':'请先登录'})
		order_id = request.POST.get('order_id')
		if not order_id:
			return JsonResponse({'res':1, 'errmsg':'无订单编号'})
		try:
			order = OrderInfo.objects.get(order_id=order_id,
										  user=user,
										  pay_method=3,
										  order_status=1)
		except OrderInfo.DoesNotExist:
			return JsonResponse({'res':2, 'errmsg':'订单编号无效'})
		# 业务逻辑处理
		# 初始化
		alipay = AliPay(appid='2016092900620771',  # 应用ID
        				app_notify_url=None,  # 默认回调url
        				app_private_key_path=os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem'),  #应用私钥
        				alipay_public_key_path=os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem'), #支付宝公钥
        				sign_type="RSA2",  # RSA 或者 RSA2 -- 这里注意一点：2018年1月5日后创建的应用只支持RSA2的格式；
        				debug=True,)  # 默认False -- 设置为True则是测试模式)
		total_pay = order.total_price+order.transit_price # Decimal类型
		# 调用支付接口
		order_string = alipay.api_alipay_trade_page_pay(
	        out_trade_no=order_id,  # 唯一标识的订单ID
	        total_amount=str(total_pay),  # 支付总金额
	        subject='天天生鲜{}'.format(order_id),  # 标题
	        return_url=None,    # 支付成功后 - 重定向自己的网站
	        notify_url=None,)   # 支付成功后 - 发送的POST订单验证消息
		# 合成跳转地址
		pay_url = "https://openapi.alipaydev.com/gateway.do?{}".format(order_string)
		return JsonResponse({'res':3, 'pay_url':pay_url})

# 前端ajax post传递参数
class OrderCheckView(View):
	def post(self, request):
		# 校验参数
		user = request.user
		if not user.is_authenticated:
			return JsonResponse({'res':0, 'errmsg':'请先登录'})
		order_id = request.POST.get('order_id')
		if not order_id:
			return JsonResponse({'res':1, 'errmsg':'无订单编号'})
		try:
			order = OrderInfo.objects.get(order_id=order_id,
										  user=user,
										  pay_method=3,
										  order_status=1)
		except OrderInfo.DoesNotExist:
			return JsonResponse({'res':2, 'errmsg':'订单编号无效'})
		# 业务逻辑处理
		# 初始化
		alipay = AliPay(appid='2016092900620771',  # 应用ID
        				app_notify_url=None,  # 默认回调url
        				app_private_key_path=os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem'),  #应用私钥
        				alipay_public_key_path=os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem'), #支付宝公钥
        				sign_type="RSA2",  # RSA 或者 RSA2 -- 这里注意一点：2018年1月5日后创建的应用只支持RSA2的格式；
        				debug=True,)  # 默认False -- 设置为True则是测试模式
		while True:
		# 调用支付宝的交易查询接口，其返回值是一个字典
		# 交易状态:WAIT_BUYER_PAY（交易创建，等待买家付款）、
		# TRADE_CLOSED（未付款交易超时关闭，或支付完成后全额退款）、
		# TRADE_SUCCESS（交易支付成功）、
		# TRADE_FINISHED（交易结束，不可退款）
			response = alipay.api_alipay_trade_query(order_id)
			code = response.get('code') # 网关返回码
			trade_status = response.get('trade_status') # 支付状态
			trade_no = response.get('trade_no') # 支付宝交易号
			if code == '10000' and trade_status == 'TRADE_SUCCESS':
				# 支付成功
				order.trade_no = trade_no
				# 更新订单状态，返回应答
				order.order_status = 4
				order.save()
				return JsonResponse({'res':3, 'message':'支付成功'})
			elif code == '40004' or (code == '10000' and trade_status == 'WAIT_BUYER_PAY'):
				# 等待买家付款
				# 限定休眠时间，再次查询
				time.sleep(5)
				continue
			else:
				# 支付出错
				return JsonResponse({'res':4, 'errmsg':'支付失败'})

# 订单评价，每一个商品都有一个评价框
class OrderCommentView(LoginRequiredMixin, View):
	def get(self, request, order_id):
		user = request.user
		# 校验参数
		if not order_id:
			return redirect(reverse('user:order'))
		try:
			order = OrderInfo.objects.get(order_id=order_id, user=user)
		except OrderInfo.DoesNotExist:
			return redirect(reverse('user:order'))
		# 获取订单商品信息
		order_skus = OrderGoods.objects.filter(order_id=order_id)
			# 遍历order_skus计算商品的小计，并动态增加小计
		for order_sku in order_skus:
			amount = order_sku.count*order_sku.price
			order_sku.amount = amount
		order.order_skus = order_skus
			# 将支付状态从对应字典中取出，并赋予属性
		order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
		order.pay_method_name = OrderInfo.PAY_METHOD[order.pay_method]
		return render(request, 'order_comment.html', {'order':order})

	def post(self, request, order_id):
		'''提交评论内容'''
		user = request.user
		# 校验参数
		if not order_id:
			return redirect(reverse('user:order'))
		try:
			order = OrderInfo.objects.get(order_id=order_id, user=user)
		except OrderInfo.DoesNotExist:
			return redirect(reverse('user:order'))
		total_count = int(request.POST.get('total_count'))
		for i in range(1, total_count+1):
			# 获取表单提交的评论内容
			sku_id = request.POST.get('sku_{}'.format(i))
			comment = request.POST.get('comment_{}'.format(i))
			try:
				order_good = OrderGoods.objects.get(order=order, sku_id=sku_id)
			except OrderGoods.DoesNotExist:
				continue
			order_good.comment = comment
			order_good.save()
		order.order_status = 5
		order.save()
		return redirect(reverse('user:order', kwargs={'page':1}))

		