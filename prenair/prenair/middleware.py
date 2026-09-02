from django.utils.translation import activate
from django.conf import settings
import pytz 
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.urls import resolve
from django.shortcuts import redirect
from dashboard.models import TrafficLog
import geoip2.database
from django.db.models import Q
import os
from dashboard.models import UserWebsite, Funnel
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseBadRequest


class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'language'):
            activate(request.user.language)
        elif 'django_language' in request.session:
            activate(request.session['django_language'])
        else:
            activate(settings.LANGUAGE_CODE)  # Default fallback

        response = self.get_response(request)
        return response



class UserTimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            tzname = request.user.timezone
            if tzname:
                try:
                    timezone.activate(pytz.timezone(tzname))
                except pytz.exceptions.UnknownTimeZoneError:
                    timezone.activate(pytz.timezone('UTC'))
        response = self.get_response(request)        
        timezone.deactivate()
        return response
    

class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        resolved_url = resolve(request.path_info)
        
        if resolved_url.app_name == 'admin' and not request.user.is_authenticated:
            return redirect('home') 
            
        if resolved_url.app_name == 'admin' and not request.user.is_superuser:
            return redirect('home')  
        
        return None



class AnalyticsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.reader = geoip2.database.Reader(
            os.path.join(settings.GEOIP_PATH, 'GeoLite2-Country.mmdb')
        )

    def __call__(self, request):
        # Skip admin and staff traffic
        if not request.path.startswith('/admin/') and not request.user.is_staff and request.path == '/':
            ip = self.get_client_ip(request)
            
            TrafficLog.objects.create(
                url=request.path,
                referrer=request.META.get('HTTP_REFERER', ''),
                country=self.get_country(ip),
                device_type=self.get_device_type(request),
                is_staff=request.user.is_staff,
                client_ip=ip
            )

        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

    def get_country(self, ip):
        print(ip)
        print(self.reader)
        try:
            return self.reader.country(ip).country.name
        except:
            return 'Unknown'

    def get_device_type(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        print(user_agent)
        if 'mobile' in user_agent: return 'Mobile'
        if 'tablet' in user_agent: return 'Tablet'
        return 'Desktop'
    

class SubdomainRoutingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        host = request.get_host().split(':')[0].lower()

        # First try to match UserWebsite
        try:
            website = UserWebsite.objects.get(
                Q(subdomain=host) | Q(custom_domain=host),
                is_published=True
            )
            request.website = website
            request.is_funnel = False
            return
        except UserWebsite.DoesNotExist:
            request.website = None

        # Then try to match Funnel
        try:
            funnel = Funnel.objects.get(
                Q(subdomain=host) | Q(custom_domain=host),
                is_published=True
            )
            request.funnel = funnel
            request.is_funnel = True
        except Funnel.DoesNotExist:
            request.funnel = None
            request.is_funnel = False


class AllowCustomDomainMiddleware(MiddlewareMixin):
    def process_request(self, request):
        host = request.get_host().split(':')[0].lower()

        allowed_base = ['fireprenair.com', 'www.fireprenair.com']
        if host.endswith('.fireprenair.com') or host in allowed_base:
            return

        if UserWebsite.objects.filter(custom_domain=host, is_published=True).exists():
            return

        return HttpResponseBadRequest(f"Invalid Host: {host}")
