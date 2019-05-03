from django.shortcuts import render, HttpResponse, redirect
from django.urls import reverse
from user.models import User
from django.views import View
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.conf import settings
from django.core.mail import send_mail
from celery_tasks.tasks import send_register_active_email
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
		return render(request, 'login.html')
