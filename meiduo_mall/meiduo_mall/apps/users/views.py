import json
import re
import logging
from django.conf import settings
from django.contrib.auth import login, authenticate, mixins
# from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth.views import logout
from django.urls import reverse
from django_redis import get_redis_connection

from meiduo_mall.utils.response_code import RETCODE
from .utils import generate_email_verify, check_verify_email_token
from .models import User, Address
from django.db import DatabaseError
from django.shortcuts import render, redirect
from django import http
# Create your views here.
# from django.utils import http
from django.views.generic.base import View
from meiduo_mall.utils.views import LoginRequiredView
from celery_tasks.email.tasks import send_verify_url


logger = logging.getLogger('django')

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


class EmailView(LoginRequiredView):
    '''用户📫📫📫邮箱'''
    def put(self, request):
        json_dict = json.loads(request.body.decode())
        email = json_dict.get('email')

        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return http.HttpResponseForbidden('邮箱格式不正确')

        user = request.user
        user.email = email
        user.save()
        # from django.core.mail import send_mail
        # send_mail(subject = '美多商城', message = '', from_email = '美多商城<itcast99@163.com>', recipient_list = [email],html_message = '<a href="http://www.baidu.com">百度<a>')
        verify_url = generate_email_verify(user)

        send_verify_url.delay(email, verify_url)

        return http.JsonResponse({'code':RETCODE.OK, 'errmsg':'OK'})


class VerifyEmailView(View):
    '''激活邮箱'''
    def get(self, request):
        token = request.GET.get('token')

        if token is None:
            return http.HttpResponseBadRequest('缺少token')

        user = check_verify_email_token(token)

        if user is None:
            return http.HttpResponseForbidden('无效的token')

        try:
            user.email_active = True
            user.save()
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError('激活邮箱失败')
        return redirect('/info/')

class AddressView(LoginRequiredView):
    """用户收货地址"""
    def get(self, request):
        """提供收货地址界面"""
        user = request.user

        address_qs = Address.objects.filter(user = user, is_deleted = False)
        # print(address_qs)
        addresses = []

        for address in address_qs:
            addresses.append({
                'id': address.id,
                'title': address.title,
                'receiver': address.receiver,
                'province_id': address.province_id,
                'province': address.province.name,
                'city_id': address.city_id,
                'city': address.city.name,
                'district_id': address.district_id,
                'district': address.district.name,
                'place': address.place,
                'mobile': address.mobile,
                'tel': address.tel,
                'email': address.email,
            })
        context = {
            'addresses': addresses,
            'default_address_id': user.default_address_id

        }
        return render(request, 'user_center_site.html', context)


class CreateAddressView(LoginRequiredView):

    '''添加收货地址'''
    def post(self, request):
        user = request.user
        count = Address.objects.filter(user=user, is_deleted = False).count()
        if count >20:
            return http.JsonResponse({'code':RETCODE.THROTTLINGERR, 'errmsg':'地址收货已超过上限'})

        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        if all([title, receiver, province_id, city_id, district_id, place, mobile]) is False:
            return http.HttpResponseForbidden('缺少参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')
        try:
            address = Address.objects.create(
                user=user,
                title=title,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
        except DatabaseError as e:
            logger.error(e)
            return http.HttpResponseForbidden('收货地址数据有误')
        if user.default_address is None:
            user.default_address = address
            user.default_address.save()

        address_dict = {
            'id': address.id,
            'title': address.title,
            'receiver': address.receiver,
            'province_id': address.province_id,
            'province': address.province.name,
            'city_id': address.city_id,
            'city': address.city.name,
            'district_id': address.district_id,
            'district': address.district.name,
            'place': address.place,
            'mobile': address.mobile,
            'tel': address.tel,
            'email': address.email,
        }

        return http.JsonResponse({'code':RETCODE.OK, 'errmsg':'添加地址成功', 'address':address_dict})


class UpdateDestroyAddressView(LoginRequiredView):
    '''修改收货地址'''
    def put(self, request, address_id):
        try:
            address = Address.objects.get(id=address_id, user=request.user, is_deleted=False)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden('address_id不存在')
        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 2.校验
        if all([title, receiver, province_id, city_id, district_id, place, mobile]) is False:
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')

        # 3. 修改Address模型对象
        try:
            Address.objects.filter(id=address_id).update(
                title=title,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
        except DatabaseError as e:
            logger.error(e)
            return http.HttpResponseForbidden('收货地址数据有误')

        address = Address.objects.get(id=address_id)

        address_dict = {
            'id': address.id,
            'title': address.title,
            'receiver': address.receiver,
            'province_id': address.province_id,
            'province': address.province.name,
            'city_id': address.city_id,
            'city': address.city.name,
            'district_id': address.district_id,
            'district': address.district.name,
            'place': address.place,
            'mobile': address.mobile,
            'tel': address.tel,
            'email': address.email,
        }

        return http.JsonResponse({'code':RETCODE.OK, 'errmsg':'OK', 'address': address_dict})
    def delete(self, request, address_id):
        """删除指定收货地址"""
        # 校验
        try:
            address = Address.objects.get(id=address_id, user=request.user, is_deleted=False)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden('address_id不存在')
        # 修改
        address.is_deleted = True
        address.save()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '删除地址成功'})

class DefaultAddressView(LoginRequiredView):
    '''默认地址'''
    def put(self, request, address_id):
        try:
            address = Address.objects.get(id=address_id, user=request.user, is_deleted=False)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden('address_id不存在')
        user = request.user
        user.default_address = address
        user.save()
        return http.JsonResponse({'code':RETCODE.OK,'errmsg':'设置默认地址成功'})