from django.conf import settings
from django.core.mail import send_mail
from celery_tasks.main import celery_app
# import logging


# logger = logging.getLogger('django')

@celery_app.task(name = 'send_verify_url')
def send_verify_url(to_email, verify_url):
    subject = '美多商城邮箱验证'
    html_message = '<p>尊敬的用户你好！</p>' \
                   '<p>感谢使用美多商城</p>' \
                   '<p>您的邮箱是:%s 点击链接激活您的邮箱</p>' \
                   '<p><a href="%s">%s<a></p>' % (to_email, verify_url,verify_url)
    # try:
    send_mail(subject, '', settings.EMAIL_FROM, [to_email], html_message = html_message)
    # except Exception as e:
    #     logger.error(e)
    #     raise self.retry(exc = e, max_retries=3)