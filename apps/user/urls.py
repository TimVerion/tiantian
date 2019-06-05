from django.urls import path
from django.conf.urls import url
from apps.user.views import *

app_name='user'
urlpatterns = [
    # path('register',views.register,name='register'),
    # path('register_handle',views.register_handle,name='register_handle'),
    path('register',RegisterView.as_view(),name='register'),#这里必须使用as_view方法
    path('active/<str:token>',ActiveView.as_view(),name='active'),
    path('login',LoginView.as_view(),name="login"),
    url(r'^logout/$', LogoutView.as_view(), name='logout'),  # 退出登录
    url(r'^$', UserInfoView.as_view(), name='user'),  # 用户中心-信息页
    url(r'^order/(?P<page>\d+)$', UserOrderView.as_view(), name='order'),  # 用户中心-订单页
    path('address/', AddressView.as_view(), name='address'),  # 用户中心-地址页
]
