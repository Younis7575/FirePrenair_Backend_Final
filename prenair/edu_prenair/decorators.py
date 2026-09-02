from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def authenticated_user_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "You must be logged in to access this page.")
            return redirect("edu_home") 
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def authenticated_user_required_commu(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "You must be logged in to access Commuprenair.")
            return redirect("home") 
        return view_func(request, *args, **kwargs)
    return _wrapped_view


###### decorator for rest api  ##############
from functools import wraps
from rest_framework.response import Response
from rest_framework import status

def authenticated_user_required_commu_api(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {"error": "You must be logged in to access Commuprenair."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def authenticated_user_required_work(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "You must be logged in to access this page.")
            return redirect("work_home") 
        return view_func(request, *args, **kwargs)
    return _wrapped_view