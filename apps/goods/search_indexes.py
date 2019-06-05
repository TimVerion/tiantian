# 定义索引类, 此文件名为固定的


import datetime
from haystack import indexes
from apps.goods.models import GoodsSKU

# 指定对于某个类某些数据建立索引
# 索引类名:模型类名+Index
class GoodsSKUIndex(indexes.SearchIndex, indexes.Indexable):
    # 索引类的字段 指定哪些字段建立索引文件
    text = indexes.CharField(document=True, use_template=True)
    # author = indexes.CharField(model_attr='user')
    # pub_date = indexes.DateTimeField(model_attr='pub_date')

    def get_model(self):
        # 返回模型类
        return GoodsSKU

    # 建立索引数据
    def index_queryset(self, using=None):
        return self.get_model().objects.all() # filter(pub_date__lte=datetime.datetime.now())
