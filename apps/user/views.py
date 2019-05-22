from django.shortcuts import render, HttpResponse, redirect
from django.urls import reverse
from user.models import User, Address
from goods.models import GoodsSKU
from order.models import OrderInfo, OrderGoods
from django.views import View
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.conf import settings
from celery_tasks.tasks import send_register_active_email
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django_redis import get_redis_connection
import re


class RegisterView(View):
	def get(self, request):
		# 显示注册页面
		return render(request, 'register.html')

	def post(self, request):
		user_name = request.POST.get('user_name')
		pwd = request.POST.get('pwd')
		email = request.POST.get('email')
		allow = request.POST.get('allow')
		
		# 判断接受的参数是否都存在
		if not all([user_name, pwd, email]):
			return render(request, 'register.html', {'errmsg': '信息填写不完整'})
		
		# 校验邮箱格式
		if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
			return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})
		
		# 校验两次密码一致(在JS中完成)
		# 校验用户是否同意协议
		if allow != 'on':
			return render(request, 'register.html', {'errmsg': '请同意用户协议'})
		
		# 校验用户名是否重复
		try:
			user = User.objects.get(username=user_name)
		except User.DoesNotExist:
			# 用户名不存在，可以进行注册
			user = None

		if user:
			return render(request, 'register.html', {'errmsg': '用户名已存在，请重试'})

		# 进行业务处理:用户注册(在表中添加用户)
		user = User.objects.create_user(user_name, email, pwd)
		# 返回应答
		user.is_active=0
		user.save()

		# 对用户名进行加密处理
		serializer = Serializer(settings.SECRET_KEY, 3600)
		info = {'confirm': user.id}
		token = serializer.dumps(info).decode('utf-8')

		# 发送邮件
		send_register_active_email.delay(email, user_name, token)

		return redirect(reverse('goods:index'))


class ActiveView(View):
	'''用户点击激活链接激活账号'''
	def get(self, request, token):
		serializer = Serializer(settings.SECRET_KEY, 3600)
		try:
			# 获取要激活用户的ID
			info = serializer.loads(token)
			user_id = info['confirm']
			user = User.objects.get(id=user_id)
			user.is_active = 1
			user.save()
			# 跳转到登录页面
			return redirect(reverse('user:login'))

		except SignatureExpired as e:
			return HttpResponse('激活链接已过期')


class LoginView(View):
	def get(self, request):
		'''显示登录页面'''
		# 判断是否记住用户名
		if 'username' in request.COOKIES:
			username = request.COOKIES.get('username')
			checked = 'checked'
		else:
			username = ''
			checked = ''
		
		content = {
			'username': username,
			'checked': checked,
		}
		return render(request, 'login.html', content)

	def post(self, request):
		username = request.POST.get('username')
		password = request.POST.get('pwd')
		remember = request.POST.get('remember')
		# 获取登录后所要跳转到的地址，默认跳转到首页
		next_url = request.GET.get('next', reverse('goods:index'))
		response = redirect(next_url)
		if not all([username, password]):
			return render(request, 'login.html', {'errmsg': '信息填写不完整'})

		# 使用Django自带的用户认证系统
		user = authenticate(username=username, password=password)
		if user:
			if user.is_active:
				# 用户已激活
				# 记录用户的登录状态
				login(request, user)
				
				# 判断是否需要记住用户名
				if remember == 'on':
					response.set_cookie('username', username, max_age=7*24*3600)
				else:
					response.delete_cookie('username')
				# 返回应答
				return response

			else:
				return render(request, 'login.html', {'errmsg': '用户未激活，请重新激活'})
		else:
			# 用户名或密码错误
			return render(request, 'login.html', {'errmsg': '用户名或密码错误'})

# /user/logout
class LogOutView(View):
	def get(self, request):
		logout(request)
		return redirect(reverse('goods:index'))


# /user
class UserInfoView(LoginRequiredMixin, View):
	def get(self, request):
		'''显示个人信息'''
		page = 'user'
		user = request.user
		address	= Address.objects.get_default_address(user)
		# 获取用户的历史浏览记录
		# 是StrictRedis的实例对象，参数为settings中设置的参数
		con = get_redis_connection('default')
		# 在redis中以history_id为key，值为list类型
		history_key = 'history_{}'.format(user.id)
		# 获取最近浏览的5个sku商品id，得到一个sku_id列表，[3,1,2]
		sku_ids = con.lrange(history_key, 0, 4)
		# 从数据库中查询用户浏览的具体信息
		goods_li = list()
		for id in sku_ids:
			goods_li.append(GoodsSKU.objects.get(id=id))

		context = {'page': page, 
				   'address': address,
				   'goods_li': goods_li,}

		return render(request, 'user_center_info.html', context)

# /user/order
class UserOrderView(LoginRequiredMixin, View):
	def get(self, request, page):
		'''显示个人订单'''
		user = request.user
		orders = OrderInfo.objects.filter(user=user).order_by('-create_time')
		# 遍历获取订单商品的信息
		for order in orders:
			# 根据order_id查询订单商品的信息，并动态增加商品信息属性
			order_skus = OrderGoods.objects.filter(order_id=order.order_id)
			# 遍历order_skus计算商品的小计，并动态增加小计
			for order_sku in order_skus:
				amount = order_sku.count*order_sku.price
				order_sku.amount = amount
			order.order_skus = order_skus
			# 将支付状态从对应字典中取出，并赋予属性
			order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
			order.pay_method_name = OrderInfo.PAY_METHOD[order.pay_method]
			order.total_amount = order.total_price+order.transit_price
		paginator = Paginator(orders, 2)
		# 获取要求页码的内容
		try:
			page = int(page)
		except Exception as e:
			page = 1
		# 判断页码是否超出
		if page > paginator.num_pages:
			page = 1

		# 获取指定页码的内容
		order_page = paginator.page(page)
		# 至多显示5个页码，显示当前页的前两页和后两页
		# 1.页面小于5页，页面上显示所有页码
		# 2.当前页是前3页，显示1-5页
		# 3.当前页是后3页，显示后5页
		# 4.其余：显示当前页的前两页和后两页
		# 5.添加跳转到第几页和最后一页的按钮，后续实现
		num_pages = paginator.num_pages
		if num_pages <= 5:
			pages = range(1, num_pages+1)
		elif page <= 3:
			pages = range(1, 6)
		elif num_pages-page <= 2:
			pages = range(num_pages-4, num_pages+1)
		else:
			pages = range(page-2, page+3)
		# 组织上下文
		context = {'order_page': order_page,
				   'pages': pages,
				   'page': 'order',}
		return render(request, 'user_center_order.html', context)

# /user/address
class UserAddressView(LoginRequiredMixin, View):
	def get(self, request):
		'''显示个人地址'''
		page = 'address'
		user = request.user
		# 使用自定义的模型管理器类
		address	= Address.objects.get_default_address(user)
		return render(request, 'user_center_site.html', {'page': page, 'address': address})

	def post(self, request):
		'''地址的添加'''
		receiver = request.POST.get('receiver')
		addr = request.POST.get('addr')
		zipcode = request.POST.get('zipcode')
		phone = request.POST.get('phone')
		if not all([receiver, addr, phone]):
			# 解决直接render时默认地址无法显示的问题，如下手机号不规范直接render后page/address参数都没有传入，因此获取不到，也可使用js在模板上解决
			page = 'address'
			user = request.user
			address	= Address.objects.get_default_address(user)
			return render(request, 'user_center_site.html', {'page': page, 'address': address, 'errmsg': '数据不完整，请重新输入'})
		# 校验手机号
		if not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
			return render(request, 'user_center_site.html', {'errmsg': '手机号不合法，请重新输入'})

		# 获取登录用户对应的User实例对象
		user = request.user
		# 使用自定义的模型管理器类
		address	= Address.objects.get_default_address(user)
		# 判断新添加的地址是否为收货地址
		if address:
			is_default = False
		else:
			is_default = True

		# 添加收货地址
		Address.objects.create(user=user, 
							   receiver=receiver, 
							   addr=addr, 
							   zip_code=zipcode, 
							   phone=phone, 
							   is_default=is_default)
		# 返回应答，刷新地址页面，以get方式再访问当前页面
		return redirect(reverse('user:address'))

		#此处可以添加让用户在多个收货地址中选择默认收货地址的功能，需要在模板中显示用户的所有收货地址
