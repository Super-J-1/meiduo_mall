from django.shortcuts import render
from django.views import View
# Create your views here.
from meiduo_mall.utils.response_code import RETCODE
from .models import Area
from django import http
from django.core.cache import cache



class AreasView(View):
    '''省市区数据查询'''
    def get(self, request):
        area_id = request.GET.get('area_id')
        if area_id is None:
            province_list = cache.get('province_list')
            if province_list is None:
                province_qs = Area.objects.filter(parent = None)
                province_list = []
                for province_model in province_qs:
                    province_list.append({
                        'id':province_model.id,
                        'name':province_model.name
                    })

                cache.set('province_list', province_list, 3600)
            return http.JsonResponse({'code':RETCODE.OK, 'errmsg':'OK', 'province_list':province_list})
        else:
            sub_data = cache.get('subs_%s' % area_id)
            if sub_data is None:
                try:
                    parent_model = Area.objects.get(id = area_id)
                except Area.DoesNotExist:
                    return http.HttpResponseForbidden('area_id不存在')
                sub_qs = parent_model.subs.all()

                sub_list = []
                for sub_model in sub_qs:
                    sub_list.append({
                        'id':sub_model.id,
                        'name':sub_model.name
                    })
                sub_data = {
                    'id':parent_model.id,
                    'name':parent_model.name,
                    'subs':sub_list
                }
                cache.set('subs_%s' % area_id, sub_data,3600)
            return http.JsonResponse({'code':RETCODE.OK, 'errmsg':'OK','sub_data':sub_data})
        pass
