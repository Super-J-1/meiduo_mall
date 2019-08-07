from django.shortcuts import render

# Create your views here.
from django.views.generic.base import View


class RegisterView(View):
    """用户注册"""

    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        pass