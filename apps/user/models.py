from django.db import models
from django.contrib.auth.models import AbstractUser
from db.base_model import BaseModel

class User(AbstractUser, BaseModel):
	'''用户模型类
	   继承了BaseModel因此无需继承models.Model
	   继承了AbstractUser，是Django自带的用户注册管理系统'''
	class Meta:
		'''重置了表名
		   重置了该表在admin界面的单/复数显示名'''
		db_table = 'df_user'
		verbose_name = '用户'
		verbose_name_plural = verbose_name

class Address(BaseModel):
	'''用户收件地址模型类
	   注意区分字段与Meta中verbose_name不同'''
	user = models.ForeignKey('User', verbose_name='所属账号', on_delete=models.CASCADE)
	receiver = models.CharField(max_length=20, verbose_name='收件人')
	addr = models.CharField(max_length=256, verbose_name='收件地址')
	zip_code = models.CharField(max_length=6, null=True, verbose_name='邮政编码')
	phone = models.CharField(max_length=11, verbose_name='联系电话')
	is_default = models.BooleanField(default=False, verbose_name='是否默认')	

	class Meta:
		db_table = 'df_address'
		verbose_name = '地址'
		verbose_name_plural = verbose_name