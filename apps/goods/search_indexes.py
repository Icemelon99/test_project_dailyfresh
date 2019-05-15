from haystack import indexes
from goods.models import GoodsSKU
#指定对于某个类的某些数据建立索引
class GoodsSKUIndex(indexes.SearchIndex, indexes.Indexable):
	# document=True意为是一个索引字段，use_template=True指定根据哪些字段来建立索引，将具体说明置入文件中
    text = indexes.CharField(document=True, use_template=True)
	# 返回模型类
    def get_model(self):
        return GoodsSKU
    # 对哪些数据建立索引,此处为全表
    def index_queryset(self, using=None):
        return self.get_model().objects.all()
