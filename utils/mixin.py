from django.contrib.auth.decorators import login_required

# 有些视图需要做用户登陆验证的直接继承
class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        # 调用父类的as_view
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
        return login_required(view)
