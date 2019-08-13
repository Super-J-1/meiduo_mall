from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from django.conf import settings




def generate_openid_signature(openid):
    serializer = Serializer(settings.SECRET_KEY, 600)
    data = {'openid': openid}
    openid_sign = serializer.dumps(data)
    return openid_sign.decode()


def check_openid_signature(openid_sign):
    serializer = Serializer(settings.SECRET_KEY, 600)

    try:
        data = serializer.loads(openid_sign)
    except BadData:
        return None
    return data.get('openid')