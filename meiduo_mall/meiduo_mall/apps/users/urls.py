from . import views
from django.conf.urls import url

urlpatterns = [
    # 注册
    url(r'^register/$', views.RegisterView.as_view()),
    url(r'^usernames/(?P<username>[a-zA-Z0-9_-]{5,20})/count/$', views.UsernameCountView.as_view()),
    url(r'^mobiles/(?P<mobile>1[345789]\d{9})/count/$', views.MobileCountView.as_view()),
    url(r'^login/$',views.LoginView.as_view()),
    url(r'^logout/$',views.LogoutView.as_view()),
    url(r'^info/$',views.InfoView.as_view()),
]