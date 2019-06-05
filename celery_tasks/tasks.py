from celery import Celery
from test1 import settings
from django.core.mail import send_mail#发送邮件
# 任务的发出者有可能在其他机子上
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test1.settings")
django.setup()
# celery -A celery_tasks.tasks worker -l info -P eventlet  必须执行这句话,让celery运行
# 这里可能出现导包顺序问题 improperlyConfigured
from apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
from django.template import loader, RequestContext
# 导入Celery类 使用8号数据库
# app = Celery('celery_tasks.tasks',broker='redis://192.168.233.160:6379/8')
app = Celery('celery_tasks.tasks',broker='redis://127.0.0.1:6379/8')
# 定义任务函数  使用app.task进行装饰
@app.task
def send_register_active_email(to_email,username,token):
    # 发送邮件
    subject = "天天生鲜欢迎信息"
    message = ''
    html_message = "<h1>%s,欢迎您成为天天生鲜注册会员</h1>请点击下面的链接激活您的账户<br/><a href=' http://10.56.22.21:8000/user/active/%s'> http://10.56.22.21:8000/user/active/%s</a>" % (username, token, token)
    # 发件人邮箱
    sender = settings.EMAIL_FROM
    # 收件人列表
    receiver = [to_email]
    # 这时候有延迟,导致用户体验不好
    send_mail(subject, message, sender, receiver, html_message=html_message)
"""
win10上运行celery4.x就会出现这个问题
pip install eventlet
celery -A celery_tasks.tasks worker -l info -P eventlet
"""
@app.task
def generate_static_index_html():
    """产生首页静态页面"""
    # 查询商品的种类信息
    types = GoodsType.objects.all()
    # 获取首页轮播的商品的信息
    index_banner = IndexGoodsBanner.objects.all().order_by('index')
    # 获取首页促销的活动信息
    promotion_banner = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类商品信息展示
    for type in types:
        # 查询首页显示的type类型的文字商品信息
        title_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')
        # 查询首页显示的图片商品信息
        image_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
        # 动态给type对象添加两个属性保存数据
        type.title_banner = title_banner
        type.image_banner = image_banner

    # 组织模板上下文
    context = {
        'types': types,
        'index_banner': index_banner,
        'promotion_banner': promotion_banner,
    }

    # 使用模板
    # 1. 加载模板文件，返回模板对象
    temp = loader.get_template('static_index.html')
    # 2. 定义模板上下文
    # context = RequestContext(request, context) # 可省
    # 3. 模板渲染
    static_index_html = temp.render(context)
    # 生成首页对应静态文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w',encoding="utf-8") as f:
        f.write(static_index_html)