from django import http
from django.shortcuts import render, redirect
from django.views import View
from QQLoginTool.QQtool import OAuthQQ
from django.conf import settings
from django_redis import get_redis_connection
from pymysql import DatabaseError

from meiduo_mall.utils.response_code import RETCODE
import logging
from users.models import User

from .models import OAuthQQUser
from django.contrib.auth import login
from .utils import generate_openid_signature,check_openid_signature
import re

# Create your views here.


logger = logging.getLogger('django')

class QQAuthURLView(View):
    """拼接QQ登录URL"""
    def get(self, request):
        # 获取查询参数中的界面来源
        next = request.GET.get('next') or '/'
        auth_qq = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                          client_secret=settings.QQ_CLIENT_SECRET,
                          redirect_uri=settings.QQ_REDIRECT_URI,
                          state=next)
        login_url = auth_qq.get_qq_url()
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'login_url': login_url})

class QQAuthUserView(View):
    '''登录成功返回处理'''
    def get(self, request):
        code = request.GET.get('code')
        if code is None:
            return http.HttpResponse('缺少code')
        auth_qq = OAuthQQ(client_id=settings.QQ_CLIENT_ID,
                          client_secret=settings.QQ_CLIENT_SECRET,
                          redirect_uri=settings.QQ_REDIRECT_URI,
                          state=next)
        try:
            access_token = auth_qq.get_access_token(code)

            openid = auth_qq.get_open_id(access_token)
        # import logging
        # logger = logging.getLogger('django')
        # logger.info(openid)
        except Exception as e:
            logger.error(e)

            return http.JsonResponse({'code':RETCODE.SERVERERR,'errmsg':'OAuth2.0认证失败'})
        try:
            auth_model = OAuthQQUser.objects.get(openid = openid)
        except OAuthQQUser.DoesNotExist:
            context = {'openid': generate_openid_signature(openid)}
            return render(request, 'oauth_callback.html', context)

        else:
            user = auth_model.user
            login(request, user)
            response = redirect(request.GET.get('state') or '/')
            response.set_cookie('username',user.name, max_age = settings.SESSION_COOKIE_AGE)
            return response


    def post(self, request):
        '''绑定用户逻辑'''
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        sms_code = request.POST.get('sms_code')
        openid = request.POST.get('openid')

        if not all([mobile, password, sms_code]):
            return http.HttpResponseForbidden('缺少必传参数')

        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号码')
        # 判断密码是否合格
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')
        # 判断短信验证码是否一致
        redis_conn = get_redis_connection('verify_codes')
        sms_code_server_bytes = redis_conn.get('sms_%s' % mobile)
        if sms_code_server_bytes is None:
            return http.JsonResponse({'code':RETCODE.SMSCODERR,'errmsg': '输入短信验证码有误'})
        sms_code_server = sms_code_server_bytes.decode()
        if sms_code !=sms_code_server:
            return http.JsonResponse({'code':RETCODE.SMSCODERR,'errmsg': '输入短信验证码有误'})
        openid = check_openid_signature(openid)
        if not openid:
            return http.HttpResponseForbidden('无效的openid')
        try:
            user = User.objects.get(mobile = mobile)
        except User.DoesNotExist:
            user = User.objects.create_user(username = mobile, password = password, mobile = mobile)
        else:
            if not user.check_password(password):
                return http.JsonResponse({'code':RETCODE.SMSCODERR,'errmsg': '用户名错误或密码'})
        try:
            OAuthQQUser.objects.create(openid=openid, user=user)
        except DatabaseError:
            return http.JsonResponse({'code':RETCODE.SMSCODERR,'errmsg': 'QQ登录失败'})

        login(request, user)
        next = request.GET.get('state')
        response = redirect(next)
        response.set_cookie('username', user.username, max_age = settings.SESSION_COOKIE_AGE)
        return response
