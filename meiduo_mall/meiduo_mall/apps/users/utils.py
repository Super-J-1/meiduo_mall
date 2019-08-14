from django.conf import settings
from django.contrib.auth.backends import ModelBackend
import re
from .models import User
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadData


def get_user_by_account(account):
    try:
        if re.match('^1[3-9]\d{9}$', account):
            user = User.objects.get(mobile = account)
        else:
            user = User.objects.get(username = account)
    except User.DoesNotExist:
        return None
    else:
        return user

class UsernameMobileAuthBackend(ModelBackend):
    """自定义用户认证后端"""

    def authenticate(self, request, username=None, password=None, **kwargs):

        # 根据传入的username获取user对象。username可以是手机号也可以是账号
        user = get_user_by_account(username)
        if user and user.check_password(password):
            return user

def generate_email_verify(user):
    '''加密'''
    serializer = Serializer(settings.SECRET_KEY, 3600*24)
    data = {'user_id': user.id, 'email':user.email}
    token = serializer.dumps(data).decode()
    verify_url = settings.EMAIL_VERIFY_URL + '?token=' + token
    return verify_url

def check_verify_email_token(token):
    '''验证token并提取user'''
    serializer = Serializer(settings.SECRET_KEY,3600*24)
    try:
        data = serializer.loads(token)
        user_id = data.get('user_id')
        email = data.get('email')
        try:
            user = User.objects.get(id = user_id, email = email)
            return user
        except User.DoesNotExist:
            return None
    except BadData:
        return None