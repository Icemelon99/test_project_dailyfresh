from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dailyfresh.settings')
django.setup()

# 创建一个实例对象
app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/2') # (‘路径’， broker)

# 定义任务函数,发送激活邮件
@app.task
def send_register_active_email(to_email, username, token):
	subject = '天天生鲜会员注册信息' # 邮件的主题
	message = '' # 邮件正文，会被html_message覆盖
	from_email = settings.EMAIL_FROM # 邮件的发件人
	reciever = [to_email] # 收件人列表
	html_message = '<h1>{}，欢迎注册</h1> <p>请点击以下链接完成账号激活<a href="http://127.0.0.1:8000/user/active/{}">http://127.0.0.1:8000/user/active/{}</a></p>'.format(username, token, token) # 按照html文档规则解析内容
	send_mail(subject, message, from_email, reciever, html_message=html_message) # 发送邮件