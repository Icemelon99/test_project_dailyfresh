from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
from django.template import loader
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dailyfresh.settings')
django.setup()

# 在Django项目初始化之后再进行导入
from goods.models import GoodsType, GoodsSKU, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
from django_redis import get_redis_connection

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

@app.task
def generate_static_index_html():
	'''产生首页的静态页面'''
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

	# 组织模板上下文
	context = {
		'types': types,
		'goods_banners': goods_banners,
		'promotion_banners': promotion_banners,
	}
	# 加载模板文件
	temp = loader.get_template('static_index.html')
	# 渲染模板生成一个大字符串
	static_index_html = temp.render(context)
	# 生成文件，拼接路径
	save_path = os.path.join(settings.BASE_DIR, 'index.html')
	with open(save_path, 'w') as f:
		f.write(static_index_html)

