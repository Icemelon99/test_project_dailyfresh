from django.core.files.storage import Storage
from django.conf import settings
from fdfs_client.client import *

class FDFSStorage(Storage):
	'''fdfs文件存储类'''
	def __init__(self, option=None):
		if not option:
			self.option = settings.FDFS_CLIENT_OPTION
		else:
			self.option = option

	def _open(self, name, mode='rb'):
		'''需要返回一个文件对象，用于直接打开文件'''
		pass

	def _save(self, name, content):
		'''保存文件时使用，name为选择上传文件的名字，content为一个包含上传文件内容的File类实例对象'''
		conf = get_tracker_conf(self.option.get('FDFS_CLIENT_CONF'))
		client = Fdfs_client(conf)
		# 上传文件到fdfs中，根据内容上传文件
		res = client.upload_by_buffer(content.read())
		#res是一个字典格式的结果
		if res.get('Status') != 'Upload successed.':
			# 上传失败
			raise Exception('上传文件失败')
		filename = res.get('Remote file_id')
		# 返回的内容即在数据表中保存的内容，由于返回的是bytes，将其解码
		return filename.decode('utf-8')

	def exists(self, name):
		'''判断name在Django中是否可用，由于使用fdfs保存文件，因此直接返回False表示文件名可用'''
		return False

	def url(self, name):
		'''返回访问文件的url路径'''
		return (self.option.get('BASE_URL')+name)

