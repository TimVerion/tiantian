from django.shortcuts import render, redirect
from django.urls import reverse
import re
from django.views.generic import View  # 类视图
# 千万别忘了是TimedJSONWebSignatureSerializer
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer  # 可以对字符串进行加密解密
from test1 import settings
from itsdangerous import SignatureExpired  # 链接超时的错误
from django.http import HttpResponse
from django.core.mail import send_mail  # 发送邮件
from celery_tasks.tasks import send_register_active_email  # 异步发送信息
from django.contrib.auth import authenticate, login, logout  # 这里使用django自带的用户的权限,登录,登出
from utils.mixin import LoginRequiredMixin
from apps.user.models import *
from apps.order.models import *
from django.core.paginator import Paginator  #分页类
from apps.goods.models import GoodsSKU
from django_redis import get_redis_connection#django提供的可以连接redis的方法
# 这里我们使用request.user是因为django会自动将request.user传过去
# 定义一个类视图  自己会进行分发dispath
class RegisterView(View):
    def get(self, request):
        return render(request, "df_user/register.html")

    def post(self, request):
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 数据校验
        data = {'user_name': username, 'pwd': password, 'email': email}
        if not all([username, password, email]):
            data['errmsg'] = '数据不完整'
            data.pop()
            return render(request, 'df_user/retister.html', data)
            # 检验邮箱

        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            data['errmsg'] = '邮箱格式不正确'
            data.pop("email")
            return render(request, 'df_user/register.html', data)

        if allow != 'on':
            data['errmsg'] = '请同意协议'
            return render(request, 'df_user/register.html', data)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名已经存在
            user = None
        if user:
            data['errmsg'] = '用户名已经存在'
            data.pop("user_name")
            return render(request, 'df_user/register.html', data)
        # 使用管理员自带的注册功能
        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        # 进行保存
        user.save()
        # 设置邮件连接内容 第一个为密钥,第二个为时间
        serializer = Serializer(settings.SECRET_KEY, 3600)
        info = {'confirm': user.id}
        token = serializer.dumps(info)
        token = token.decode()
        # 发送邮件
        send_register_active_email.delay(email, username, token)
        # html_message = "<h1>%s,欢迎您成为天天生鲜注册会员</h1>请点击下面的链接激活您的账户<br/><a href=' http://10.56.22.21:8000/user/active/%s'> http://10.56.22.21:8000/user/active/%s</a>" % (
        # username, token, token)
        # # 发件人邮箱
        # sender = settings.EMAIL_FROM
        # # 收件人列表
        # receiver = [email]
        # # 这时候有延迟,导致用户体验不好
        # send_mail(subject, message, sender, receiver, html_message=html_message)
        # pip install reids
        # celery -A celery_tasks.tasks worker -l info
        # 类似于springmvc的反响解析，这时候我们跳到goods中urls的index
        return redirect(reverse("goods:index"))


from apps.user.models import User


class ActiveView(View):
    def get(self, request, token):
        serializer = Serializer(settings.SECRET_KEY, 3360)
        try:
            # 进行解密
            info = serializer.loads(token)
            user_id = info['confirm']
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            return redirect(reverse("user:login"))
        except SignatureExpired as e:
            return HttpResponse("激活链接已经过期")


class LoginView(View):
    def get(self, request):
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')  # request.COOKIES['username']
            checked = 'checked'
        else:
            username = ''
            checked = ''

        return render(request, 'df_user/login.html', {'username': username, 'checked': checked})

    def post(self, request):
        # 接受数据
        username = request.POST.get('username')
        password = request.POST.get('pwd')

        # 校验数据
        if not all([username, password]):
            return render(request, 'df_user/login.html', {'errmsg': '数据不完整'})

        # 业务处理: 登陆校验
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)  # 登录并记录用户的登录状态
                # 获取登录后所要跳转到的地址, 默认跳转首页
                # reverse('goods:index')可以
                next_url = request.GET.get('next', reverse('goods:index'))
                response = redirect(next_url)
                # 设置cookie, 需要通过HttpReponse类的实例对象, set_cookie
                remember = request.POST.get('remember')
                # 判断是否需要记住用户名
                if remember == 'on':
                    response.set_cookie('username', username, max_age=7 * 24 * 3600)
                else:
                    response.delete_cookie('username')
                return response
            else:
                return render(request, 'df_user/login.html', {'errmsg': '账户未激活'})
        else:
            return render(request, 'df_user/login.html', {'errmsg': '用户名或密码错误'})


# /user/logout
class LogoutView(View):
    """退出登录"""

    def get(self, request):
        logout(request)
        return redirect(reverse('goods:index'))


# 下面三个视图的LoginRequiredMixin对用户登录登出的判断只局限于你用户的登录登出也是使用的django.contrib.auth
# 这里调用as_view方法,从左往右找,所以View不能再LM前面
# /user
class UserInfoView(LoginRequiredMixin, View):
    """用户中心-信息页"""
    def get(self, request):
        user = request.user
        address = Address.objects.get_default_address(user)
        # 获取默认的redis连接
        # from redis import StrictRedis
        # sr = SignatureExpired(host='127.0.0.1',port=6379'',db=9)
        # 通过django-redis获得连接,然后获得后四条浏览记录
        con = get_redis_connection("default")
        history_key = 'history_%d'%(user.id)
        sku_ids = con.lrange(history_key,0,4)
        # goods_li = GoodsSKU.objects.filter(id__in=sku_ids) #可以查出来但是顺序不对
        goods_li = []
        if sku_ids != None:
            for id in sku_ids:
                # 这里先前使用了filter传出的是列表不是对象
                goods_li.append(GoodsSKU.objects.get(id=id))

        # 组织上下文就是不把字典直接写在render方法里面
        context = {
            "page":"user",
            "address":address,
            "goods_list":goods_li
        }
        return render(request, "df_user/user_center_info.html",context)


# /user/order
class UserOrderView(LoginRequiredMixin, View):
    """用户中心-订单页"""
    def get(self, request, page):
        # 获取用户的订单信息
        user = request.user
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')

        # 遍历获取订单商品信息
        for order in orders:
            # 根据order_id查询订单商品信息
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)

            # 遍历Order_skus计算商品的小计
            for order_sku in order_skus:
                amount = order_sku.count * order_sku.price
                # 动态给order_sku增加属性amount,保存订单商品小计
                order_sku.amount = amount

            # 动态给order增加属性, 保存订单状态标题
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
            order.order_skus = order_skus

        # 分页
        paginator = Paginator(orders, 2)  # 单页显示数目2

        try:
            page = int(page)
        except Exception as e:
            page = 1

        if page > paginator.num_pages or page <= 0:
            page = 1

        # 获取第page页的Page实例对象
        order_page = paginator.page(page)

        # todo: 进行页码的控制，页面上最多显示5个页码
        # 1. 总数不足5页，显示全部
        # 2. 如当前页是前3页，显示1-5页
        # 3. 如当前页是后3页，显示后5页
        # 4. 其他情况，显示当前页的前2页，当前页，当前页的后2页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)

        # 组织上下文
        context = {'order_page': order_page,
                   'pages': pages,  # 页面范围控制
                   'page': 'order'}

        return render(request, 'df_user/user_center_order.html', context)


# /user/address
class AddressView(LoginRequiredMixin, View):
    """用户中心-地址页"""

    def get(self, request):
        user= request.user
        address = Address.objects.get_default_address(user)
        return render(request, "df_user/user_center_site.html",{'page':"address","address":address})

    def post(self, request):
        # 接受收件人信息
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        # 这里邮编可以不填
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        # 数据校验
        if not all([receiver, addr, phone]):
            return render(request, "df_user/user_center_site.html", {"errmsg": "数据不完整"})
        if not re.match(r'^1([3-8][0-9]|5[189]|8[6789])[0-9]{8}$', phone):
            return render(request, 'df_user/user_center_site.html', {'errmsg': '手机号格式不合法'})
        # 这里有个逻辑,当用户已经默认收货地址,则该地址不为默认,否则反之
        user = request.user
        address = Address.objects.get_default_address(user)
        if address:
            is_default = False
        else:
            is_default = True
        Address.objects.create(
            user=user,
            addr=addr,
            receiver=receiver,
            zip_code=zip_code,
            phone=phone,
            is_default=is_default)
        return redirect(reverse("user:address"))
