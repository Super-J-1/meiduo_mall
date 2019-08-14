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
    url(r'^emails/$',views.EmailView.as_view()),
    url(r'^emails/verification/$',views.VerifyEmailView.as_view()),
    url(r'^addresses/$',views.AddressView.as_view()),
    url(r'^addresses/create/$',views.CreateAddressView.as_view()),
    url(r'^addresses/(?P<address_id>\d+)/$', views.UpdateDestroyAddressView.as_view()),
    url(r'^addresses/(?P<address_id>\d+)/default/$', views.DefaultAddressView.as_view()),
]