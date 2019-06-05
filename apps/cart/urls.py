from django.urls import path
from apps.cart.views import *
app_name='cart'
urlpatterns = [
    path('add', CartAddview.as_view(), name='add'),  # 购物车页面
    path('', CartInfoView.as_view(), name='cart'),  # 显示购物车页
    path('update', CartUpdateView.as_view(), name='update'),  # 购物车数据更新
    path('delete', CartDeleteView.as_view(), name='delete'),  # 删除购物车中的商品记录
]
