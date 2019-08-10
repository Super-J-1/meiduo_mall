import random

from django import http
from django.shortcuts import render
from django_redis import get_redis_connection
# Create your views here.
from django.views.generic.base import View
from meiduo_mall.libs.captcha.captcha import captcha
from meiduo_mall.libs.yuntongxun.sms import CCP
from meiduo_mall.utils.response_code import RETCODE
from verifications.constants import IMAGE_CODE_EXPIRE


class ImageCodeView(View):
    '''图形验证'''
    def get(self,request,uuid):
        # 图形验证码的图片bytes类型数据
        name, text, image_code = captcha.generate_captcha()
        # 连接redis
        redis_conn = get_redis_connection('verify_codes')
        # 将图形验证码字符串存储到redis数据库
        redis_conn.setex(uuid, IMAGE_CODE_EXPIRE, text)
        return http.HttpResponse(image_code, content_type = 'image/jpg')

class SMSCodeView(View):
    def get(self, request, mobile):
        redis_conn = get_redis_connection('verify_codes')
        if redis_conn.get('send_%s' % mobile):
            return http.JsonResponse({'code':RETCODE.THROTTLINGERR,'errmsg':'频繁发送验证码'})
        query_dict = request.GET
        image_code_client = query_dict.get('image_code')
        uuid = query_dict.get('uuid')
        print(uuid)
        # 校验
        if not all([image_code_client, uuid]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 创建redis连接

        print(redis_conn)
        # 获取图片验证码
        image_code_server_bytes = redis_conn.get(uuid)
        print(image_code_server_bytes)
        # 从redis数据库删除
        redis_conn.delete(uuid)
        # 判断redis中是否取到图形验证码
        if image_code_server_bytes is None:
            return http.JsonResponse({'code':RETCODE.IMAGECODEERR, 'errmsg':'图形验证码失效'})

        image_code_server = image_code_server_bytes.decode()
        # 转换字母大小写问题
        if image_code_client.lower() != image_code_server.lower():
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码输入错误'})

        # 随机短信验证码
        sms_code = '%06d' % random.randint(0,999999)
        # 创建管道
        pl = redis_conn.pipeline()
        # 将短信验证码缓存到redis
        # redis_conn.setex('sms_%s' % mobile, 300, sms_code)
        pl.setex('sms_%s' % mobile, 300, sms_code)
        # redis标识符
        # redis_conn.setex('send_%s' % mobile, 60, 1)
        pl.setex('send_%s' % mobile, 60, 1)
        # 执行
        pl.execute()
        # 发送短信
        CCP().send_template_sms(mobile,[sms_code, 5], 1)
        return http.JsonResponse({'code':RETCODE.OK, 'errmsg':'OK'})
