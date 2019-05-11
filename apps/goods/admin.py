from django.contrib import admin
from django.core.cache import cache
from goods.models import GoodsType, GoodsSKU, GoodsSPU, GoodsImage, IndexGoodsBanner, IndexTypeGoodsBanner, IndexPromotionBanner

# Register your models here.

class BaseModelAdmin(admin.ModelAdmin):
	def save_model(self, request, obj, form, change):
		'''在新增或修改模型类表时应用'''
		super().save_model(request, obj, form, change)
		from celery_tasks.tasks import generate_static_index_html
		generate_static_index_html.delay()
		# 删除缓存，由于view中缓存若不存在会生成，因此无需在此生成
		cache.delete('index_page_data')

	def delete_model(self, request, obj):
		'''在删除模型类表中数据时使用'''
		super().delete_model(request, obj)
		from celery_tasks.tasks import generate_static_index_html
		generate_static_index_html.delay()
		# 删除缓存
		cache.delete('index_page_data')

class GoodsTypeAdmin(BaseModelAdmin):
	pass

class GoodsSKUAdmin(BaseModelAdmin):
	pass

class GoodsSPUAdmin(BaseModelAdmin):
	pass

class GoodsImageAdmin(BaseModelAdmin):
	pass

class IndexGoodsBannerAdmin(BaseModelAdmin):
	pass

class IndexTypeGoodsBannerAdmin(BaseModelAdmin):
	pass

class IndexPromotionBannerAdmin(BaseModelAdmin):
	pass

admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(GoodsSKU, GoodsSKUAdmin)
admin.site.register(GoodsSPU, GoodsSPUAdmin)
admin.site.register(GoodsImage, GoodsImageAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)