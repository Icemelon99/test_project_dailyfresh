from django.shortcuts import render, HttpResponse, redirect
from django.urls import reverse
from user.models import User
from django.views import View
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.conf import settings
from celery_tasks.tasks import send_register_active_email
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
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

		if not all([username, password]):
			return render(request, 'login.html', {'errmsg': '信息填写不完整'})

		# 使用Django自带的用户认证系统
		user = authenticate(username=username, password=password)
		if user:
			if user.is_active:
				# 用户已激活
				# 记录用户的登录状态
				login(request, user)
				response = redirect(next_url)
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
		return render(request, 'user_center_info.html', {'page': page})

# /user/order
class UserOrderView(LoginRequiredMixin, View):
	def get(self, request):
		'''显示个人订单'''
		page = 'order'
		return render(request, 'user_center_order.html', {'page': page})

# /user/address
class UserAddressView(LoginRequiredMixin, View):
	def get(self, request):
		'''显示个人地址'''
		page = 'address'
		return render(request, 'user_center_site.html', {'page': page})


