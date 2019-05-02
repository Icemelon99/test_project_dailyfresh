from django.db import models

class BaseModel(models.Model):
	'''模型抽象基类，所有的模型类均继承其字段'''
	create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
	update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
	is_delete = models.BooleanField(default=False, verbose_name='删除标记')

	class Meta:
		'''说明是一个抽象模型基类，其本身不迁移生成表'''
		abstract = True