import re

from django.conf import settings
from django.contrib.auth import login, authenticate, mixins
# from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth.views import logout
from django.urls import reverse
from django_redis import get_redis_connection

from meiduo_mall.utils.response_code import RETCODE
from .models import User
from django.db import DatabaseError
from django.shortcuts import render, redirect
from django import http
# Create your views here.
# from django.utils import http
from django.views.generic.base import View


class RegisterView(View):
    """用户注册"""

    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        request_dict = request.POST
        username = request_dict.get('username')
        password = request_dict.get('password')
        password2 = request_dict.get('password2')
        mobile = request_dict.get('mobile')
        sms_code = request_dict.get('sms_code')
        allow = request_dict.get('allow')
        if not all([username, password, password2, mobile, sms_code, allow]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$',username):
            return http.HttpResponseForbidden('请输入5-20个字符的用户名')
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')
        if password != password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')
        if not re.match(r'^1[3-9]\d{9}$',mobile):
            return http.HttpResponseForbidden('请输入正确的手机号码')
        if allow != 'on':
            return http.HttpResponseForbidden('🙏请勾选用户协议')
            # 创建redis连接
        redis_conn = get_redis_connection('verify_codes')
        print(redis_conn)
        # # 获取短信验证码
        sms_code_server_bytes = redis_conn.get('sms_%s' % mobile)
        print(sms_code_server_bytes)
        # # 从redis数据库删除
        redis_conn.delete('sms_%s' % mobile)
        # # 判断redis中是否取到短信证码
        if sms_code_server_bytes is None:
            return http.JsonResponse({'code': RETCODE.SMSCODERR, 'errmsg': '图形验证码失效'})
        #
        sms_code_server = sms_code_server_bytes.decode()
        # # 判断短信验证码
        if sms_code != sms_code_server:
            return http.JsonResponse({'code': RETCODE.SMSCODERR, 'errmsg': '图形验证码输入错误'})
        # try:
        user = User.objects.create_user(username = username, password = password, mobile = mobile)

        # except DatabaseError:
        #     return render(request,'register.html',{'register_errmsg': '注册失败'})
        login(request, user)
        response = redirect('/')
        response.set_cookie('username', username, max_age = settings.SESSION_COOKIE_AGE)
        return response

class UsernameCountView(View):
    '''判断用户名是否存在'''
    def get(self, request, username):
        count = User.objects.filter(username = username).count()
        return http.JsonResponse({'count': count})


class MobileCountView(View):
    """判断手机号是否重复注册"""
    def get(self, request, mobile):
        count = User.objects.filter(mobile=mobile).count()
        return http.JsonResponse({'count': count})


class LoginView(View):
    '''用户登录'''
    def get(self, request):
        '''提供登录界面'''
        return render(request, 'login.html')
    '''
    def post(self, request):
        
        request_dict = request.POST
        username = request_dict.get('username')
        password = request_dict.get('password')
        remembered = request_dict.get('remembered')
        if re.match(r'^1[3-9]\d{9}$', username):
            User.USERNAME_FIELD = 'mobile'
        user = authenticate(request, username = username, password = password)
        User.USERNAME_FIELD = 'username'
        if user is None:
            return render(request, 'login.html', {'account_errmsg': '用户名或密码错误'})
        login(request, user)
        if remembered is None:
            request.session.set_expiry(0)
        return redirect('/')

    '''

    def post(self, request):
        '''登录功能'''
        request_dict = request.POST
        username = request_dict.get('username')
        password = request_dict.get('password')
        remembered = request_dict.get('remembered')

        user = authenticate(request, username = username, password = password)

        if user is None:
            return render(request, 'login.html', {'account_errmsg': '用户名或密码错误'})
        login(request, user)
        if remembered is None:
            request.session.set_expiry(0)
        next = request.GET.get('next')
        response = redirect(next or '/')
        response.set_cookie('username', username, max_age = (None if remembered is None else settings.SESSION_COOKIE_AGE))

        return response


class LogoutView(View):
    '''退出登录'''
    def get(self, request):

        logout(request)
        response = redirect('/login/')
        response.delete_cookie('username')
        return response

# class InfoView(View):
#     '''用户中心'''
#     def get(self, request):
#         if request.user.is_authenticated:
#             return render(request, 'user_center_info.html')
#         else:
#             return redirect('/login/?next=/info/')

class InfoView(mixins.LoginRequiredMixin, View):
# class InfoView(View):
    '''用户中心'''
    def get(self, request):
        return render(request, 'user_center_info.html')
