from django.db import models
from django.contrib.auth.models import AbstractUser
from db.base_model import BaseModel

class User(AbstractUser, BaseModel):
	'''用户模型类
	   继承了BaseModel因此无需继承models.Model
	   继承了AbstractUser，是Django自带的用户注册管理系统'''
	class Meta:
		'''指定了表名，指定了该表在admin界面的单/复数显示名'''
		db_table = 'df_user'
		verbose_name = '用户'
		verbose_name_plural = verbose_name


class AddressManager(models.Manager):
	# 重定义继承自默认Manager中的方法，即User.objects.all()，此处自定义的模型管理器类取代的是 User.objects
	# 使用self.model取代模型类名，如此可以将自定义的管理器对象应用于多个模型类中
	def get_default_address(self, user):
		try:
			# self 即模型管理器类对象，直接支持get方法，无需self.model.objects
			# 此处使用的user参数是传入的，由于创建self时已经确定了模型类，因此其中的字段名无需传入
			address = self.get(user=user, is_default=True)
		except self.model.DoesNotExist:
			# 不存在默认收货地址
			address = None
		return address


class Address(BaseModel):
	'''用户收件地址模型类，注意区分字段与Meta中verbose_name不同'''
	user = models.ForeignKey('User', verbose_name='所属账号', on_delete=models.CASCADE)
	receiver = models.CharField(max_length=20, verbose_name='收件人')
	addr = models.CharField(max_length=256, verbose_name='收件地址')
	zip_code = models.CharField(max_length=6, null=True, verbose_name='邮政编码')
	phone = models.CharField(max_length=11, verbose_name='联系电话')
	is_default = models.BooleanField(default=False, verbose_name='是否默认')	
	objects = AddressManager()

	class Meta:
		db_table = 'df_address'
		verbose_name = '地址'
		verbose_name_plural = verbose_name