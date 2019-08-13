from django.contrib.auth import mixins
from django.views import View

class LoginRequired(mixins.LoginRequiredMixin, View):
    '''判断登录视图基类'''
    pass