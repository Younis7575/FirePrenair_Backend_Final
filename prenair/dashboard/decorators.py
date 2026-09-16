from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from profiles.models import CustomUser
from digi_prenair.models import Product

def admin_not_allowed(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'role') or request.user.role == 'admin':  # Check if user has 'admin' role
            messages.error(request, "You are not allowed to access this page.")
            return redirect('home')  # Redirect to the home page
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_not_allowed_api(view_func):
    """API counterpart of [admin_not_allowed].

    The web version answers with a 302 to the home page. On an API endpoint
    that hands a mobile client an HTML redirect it cannot act on, so this
    returns a JSON 403 instead.
    """
    from rest_framework import status as drf_status
    from rest_framework.response import Response

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'role') or request.user.role == 'admin':
            return Response(
                {'error': 'Admin accounts cannot use the seller dashboard.'},
                status=drf_status.HTTP_403_FORBIDDEN,
            )
        return view_func(request, *args, **kwargs)
    return _wrapped_view



def get_top_sellers(count=10, min_sales=0):
    top_sellers = CustomUser.objects.filter(
        is_digi_seller=True,
        digi_total_sales__gte=min_sales
    ).order_by('-total_earnings', '-digi_total_sales', '-digi_average_rating')[:count]
    
    result = []
    for seller in top_sellers:
        # Calculate seller level based on earnings and sales
        if seller.total_earnings >= 10000:
            level = "Platinum"
        elif seller.total_earnings >= 5000:
            level = "Gold"
        elif seller.total_earnings >= 1000:
            level = "Silver"
        else:
            level = "Bronze"
            
        result.append({
            'id': seller.id,
            'username': seller.username,
            'name': seller.name if seller.name else seller.username,
            'profile_pic': seller.profile_pic.url if seller.profile_pic else None,
            'total_earnings': float(seller.total_earnings),
            'available_earnings': float(seller.available_earnings),
            'digi_total_earnings': float(seller.digi_total_earnings),
            'digi_total_sales': seller.digi_total_sales,
            'digi_total_items': seller.digi_total_items,
            'digi_average_rating': float(seller.digi_average_rating),
            'digi_is_verified': seller.digi_is_verified,
            'digi_is_featured': seller.digi_is_featured,
            'digi_speciality': seller.digi_speciality,
            'country': seller.country,
            'city': seller.city,
            'province': seller.province,
            'is_online': seller.is_online,
            'level': level,
            'join_date': seller.created_at.strftime('%b %Y') if seller.created_at else 'N/A'
        })
    
    return result


def get_top_digi_products(count=10):
    top_products = Product.objects.filter(item_sales__gt=0).order_by('-item_sales')[:count]
    
    result = []
    for rank, product in enumerate(top_products, 1):
        result.append({
            'rank': rank,
            'title': product.title,
            'product_type': product.category.name if product.category else 'General',
            'sales': product.item_sales,
            'revenue': float(product.item_sales * product.price),
            'avg_price': float(product.price),
            'change_vs_prior_period': 0,  # Can be calculated later if needed
        })
    
    return result

