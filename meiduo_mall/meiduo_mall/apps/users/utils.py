from django.contrib.auth.backends import ModelBackend
import re
from .models import User

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