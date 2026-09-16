"""
Missing REST API endpoints V3 for FirePrenair.
- Profile recovery (forgot password, forgot username, password reset confirm)
- Check username/email availability
- Admin sales analytics (digi_sales, work_sales)
- Send tag email for funnels
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, Count
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.utils.html import escape
from datetime import timedelta
import json
import re

from .serializers import *
from profiles.models import CustomUser
from home.models import PricingPlan, UserPlan
from work_prenair.models import Order as WorkOrder, Gig, Category as WorkCategory
from digi_prenair.models import Product, Order as DigiOrder, OrderItem
from dashboard.models import Funnel, FunnelLead


# =============================================================================
# PROFILE RECOVERY APIs
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password_api_v2(request):
    """Send password reset instructions"""
    email = (request.data.get('email') or '').strip().lower()
    if not email:
        return Response({'success': False, 'error': 'Please enter your email address.'},
                        status=status.HTTP_400_BAD_REQUEST)
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return Response({'success': True,
                         'message': 'If an account exists for that email, you will receive password reset instructions shortly.'})
    try:
        user = CustomUser.objects.get(email__iexact=email)
    except CustomUser.DoesNotExist:
        return Response({'success': True,
                         'message': 'If an account exists for that email, you will receive password reset instructions shortly.'})

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    tok = default_token_generator.make_token(user)
    reset_url = f"https://fireprenair.com/?recover=reset&uid={uid}&token={tok}"

    inner = f"""
<p style="color:#333;font-size:16px;line-height:1.6;margin:0 0 20px;">Hi <strong>{escape(user.name or 'there')}</strong>,</p>
<p style="color:#333;font-size:16px;line-height:1.6;margin:0 0 24px;">We received a request to reset your FirePrenair password. Click the link below to choose a new password.</p>
<div style="text-align:center;margin:28px 0;">
<a href="{reset_url}" style="display:inline-block;background:linear-gradient(135deg,#ff6f61 0%,#ff8e53 100%);color:#fff;text-decoration:none;padding:14px 32px;border-radius:999px;font-weight:700;font-size:15px;">Reset your password</a>
</div>
<p style="color:#666;font-size:14px;margin:0;">If you did not request this, you can ignore this email.</p>
"""
    try:
        from work_prenair.views import send_email
        send_email(user.email, 'Reset your FirePrenair password',
                   f"<!DOCTYPE html><html><body>{inner}</body></html>",
                   f"Reset your FirePrenair password:\n{reset_url}\n")
    except Exception:
        pass

    return Response({'success': True,
                     'message': 'If an account exists for that email, you will receive password reset instructions shortly.',
                     'uid': uid, 'token': tok})


@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_username_api_v2(request):
    """Send username reminder"""
    email = (request.data.get('email') or '').strip().lower()
    if not email:
        return Response({'success': False, 'error': 'Please enter your email address.'},
                        status=status.HTTP_400_BAD_REQUEST)
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return Response({'success': True,
                         'message': 'If an account exists for that email, we sent your username there.'})
    try:
        user = CustomUser.objects.get(email__iexact=email)
    except CustomUser.DoesNotExist:
        return Response({'success': True,
                         'message': 'If an account exists for that email, we sent your username there.'})

    inner = f"""
<p style="color:#333;font-size:16px;line-height:1.6;margin:0 0 20px;">Hi <strong>{escape(user.name or 'there')}</strong>,</p>
<div style="background:#f8f9fa;padding:24px;border-radius:14px;text-align:center;border:2px dashed #dee2e6;margin:24px 0;">
<p style="color:#ff6f61;font-size:22px;font-weight:700;margin:0;word-break:break-all;">{escape(user.username)}</p>
</div>
"""
    try:
        from work_prenair.views import send_email
        send_email(user.email, 'Your FirePrenair username',
                   f"<!DOCTYPE html><html><body>{inner}</body></html>",
                   f"Your FirePrenair username: {user.username}\n")
    except Exception:
        pass

    return Response({'success': True,
                     'message': 'If an account exists for that email, we sent your username there.'})


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm_api_v2(request):
    """Confirm password reset with uid, token, new password"""
    uid = (request.data.get('uid') or '').strip()
    token = (request.data.get('token') or '').strip()
    password1 = request.data.get('password1') or ''
    password2 = request.data.get('password2') or ''

    if not uid or not token:
        return Response({'success': False, 'error': 'This reset link is invalid or has expired.'},
                        status=status.HTTP_400_BAD_REQUEST)
    if not password1 or not password2:
        return Response({'success': False, 'error': 'Please enter and confirm your new password.'},
                        status=status.HTTP_400_BAD_REQUEST)
    if password1 != password2:
        return Response({'success': False, 'error': 'The two passwords do not match.'},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        pk = force_str(urlsafe_base64_decode(uid))
        user = CustomUser.objects.get(pk=pk)
    except Exception:
        return Response({'success': False, 'error': 'This reset link is invalid or has expired.'},
                        status=status.HTTP_400_BAD_REQUEST)
    if not default_token_generator.check_token(user, token):
        return Response({'success': False, 'error': 'This reset link is invalid or has expired.'},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        validate_password(password1, user)
    except ValidationError as e:
        return Response({'success': False, 'error': ' '.join(e.messages)},
                        status=status.HTTP_400_BAD_REQUEST)
    user.set_password(password1)
    user.save()
    return Response({'success': True, 'message': 'Your password has been updated. You can sign in now.'})


# =============================================================================
# CHECK AVAILABILITY APIs
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def check_username_availability_api(request):
    """Check if username is available"""
    username = (request.data.get('username') or '').strip()
    if not username:
        return Response({'available': False, 'message': 'Username is required'})
    if len(username) < 3:
        return Response({'available': False, 'message': 'Username must be at least 3 characters'})
    if not username.replace('_', '').isalnum():
        return Response({'available': False, 'message': 'Username can only contain letters, numbers, and underscores'})
    exists = CustomUser.objects.filter(username=username).exists()
    if exists:
        return Response({'available': False, 'message': 'This username is already taken'})
    return Response({'available': True, 'message': 'Username is available'})


@api_view(['POST'])
@permission_classes([AllowAny])
def check_email_availability_api(request):
    """Check if email is available"""
    email = (request.data.get('email') or '').strip()
    if not email:
        return Response({'available': False, 'message': 'Email is required'})
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return Response({'available': False, 'message': 'Please enter a valid email address'})
    exists = CustomUser.objects.filter(email=email).exists()
    if exists:
        return Response({'available': False, 'message': 'An account with this email already exists'})
    return Response({'available': True, 'message': 'Email is available'})


# =============================================================================
# ADMIN SALES APIs
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def digi_sales_api(request):
    """Admin: Digiprenair sales analytics"""
    if request.user.role != 'admin' and not request.user.is_staff:
        return Response({'error': 'Access Denied!'}, status=status.HTTP_403_FORBIDDEN)

    from digi_prenair.models import Order as DigiOrder, Product

    orders = DigiOrder.objects.all().order_by('-created_at')[:50]
    total_sales = DigiOrder.objects.filter(is_paid=True).aggregate(total=Sum('total_amount'))['total'] or 0
    total_orders = DigiOrder.objects.filter(is_paid=True).count()
    thirty_days_ago = timezone.now() - timedelta(days=30)
    monthly_sales = DigiOrder.objects.filter(is_paid=True, created_at__gte=thirty_days_ago).aggregate(total=Sum('total_amount'))['total'] or 0
    seven_days_ago = timezone.now() - timedelta(days=7)
    weekly_sales = DigiOrder.objects.filter(is_paid=True, created_at__gte=seven_days_ago).aggregate(total=Sum('total_amount'))['total'] or 0
    today = timezone.now().date()
    daily_sales = DigiOrder.objects.filter(is_paid=True, created_at__date=today).aggregate(total=Sum('total_amount'))['total'] or 0

    # Sales chart (last 30 days)
    sales_data = []
    dates = []
    for i in range(30):
        date = timezone.now().date() - timedelta(days=29 - i)
        daily_total = DigiOrder.objects.filter(is_paid=True, created_at__date=date).aggregate(total=Sum('total_amount'))['total'] or 0
        sales_data.append(float(daily_total))
        dates.append(date.strftime('%Y-%m-%d'))

    # Top selling products
    top_products = Product.objects.annotate(
        total_sold=Sum('orderitem__quantity'),
        total_revenue=Sum('orderitem__price')
    ).filter(total_sold__gt=0).order_by('-total_sold')[:10]

    top_products_data = [{'title': p.title, 'sales': p.total_sold or 0, 'revenue': float(p.total_revenue or 0)} for p in top_products]

    orders_data = [{'id': o.id, 'user': {'username': o.user.username}, 'created_at': o.created_at.isoformat(), 'total_amount': float(o.total_amount), 'is_paid': o.is_paid} for o in orders]

    return Response({
        'total_sales': float(total_sales),
        'total_orders': total_orders,
        'monthly_sales': float(monthly_sales),
        'weekly_sales': float(weekly_sales),
        'daily_sales': float(daily_sales),
        'sales_chart': {'dates': dates, 'amounts': sales_data},
        'top_products': top_products_data,
        'orders': orders_data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def work_sales_api(request):
    """Admin: Workprenair sales analytics"""
    if request.user.role != 'admin' and not request.user.is_staff:
        return Response({'error': 'Access Denied!'}, status=status.HTTP_403_FORBIDDEN)

    orders = WorkOrder.objects.all().order_by('-created_at')[:50]
    total_sales = WorkOrder.objects.filter(is_paid=True).aggregate(total=Sum('price'))['total'] or 0
    total_orders = WorkOrder.objects.filter(is_paid=True).count()
    completed_orders = WorkOrder.objects.filter(is_paid=True, status='completed').count()
    active_orders = WorkOrder.objects.filter(is_paid=True, status='active').count()
    thirty_days_ago = timezone.now() - timedelta(days=30)
    monthly_sales = WorkOrder.objects.filter(is_paid=True, created_at__gte=thirty_days_ago).aggregate(total=Sum('price'))['total'] or 0
    seven_days_ago = timezone.now() - timedelta(days=7)
    weekly_sales = WorkOrder.objects.filter(is_paid=True, created_at__gte=seven_days_ago).aggregate(total=Sum('price'))['total'] or 0
    today = timezone.now().date()
    daily_sales = WorkOrder.objects.filter(is_paid=True, created_at__date=today).aggregate(total=Sum('price'))['total'] or 0

    # Sales chart
    sales_data = []
    dates = []
    for i in range(30):
        date = timezone.now().date() - timedelta(days=29 - i)
        daily_total = WorkOrder.objects.filter(is_paid=True, created_at__date=date).aggregate(total=Sum('price'))['total'] or 0
        sales_data.append(float(daily_total))
        dates.append(date.strftime('%Y-%m-%d'))

    # Top gigs
    top_gigs = Gig.objects.annotate(
        total_orders_count=Count('orders', filter=Q(orders__is_paid=True)),
        total_revenue=Sum('orders__price', filter=Q(orders__is_paid=True))
    ).filter(total_orders_count__gt=0).order_by('-total_revenue')[:10]

    top_gigs_data = [{'title': g.title, 'seller': g.user.username, 'orders': g.total_orders_count or 0, 'revenue': float(g.total_revenue or 0)} for g in top_gigs]

    orders_data = [{'id': o.id, 'user': {'username': o.user.username}, 'gig': {'title': o.gig.title}, 'package_type': o.package_type, 'created_at': o.created_at.isoformat(), 'price': float(o.price), 'is_paid': o.is_paid, 'status': o.status} for o in orders]

    return Response({
        'total_sales': float(total_sales),
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'active_orders': active_orders,
        'monthly_sales': float(monthly_sales),
        'weekly_sales': float(weekly_sales),
        'daily_sales': float(daily_sales),
        'sales_chart': {'dates': dates, 'amounts': sales_data},
        'top_gigs': top_gigs_data,
        'orders': orders_data,
    })


# =============================================================================
# SEND TAG EMAIL API
# =============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_tag_email_api_v2(request):
    """Send email to all leads with a specific tag"""
    tag = request.data.get('tag', '')
    subject = request.data.get('subject', '')
    body = request.data.get('body', '')

    if not tag or not subject or not body:
        return Response({'error': 'tag, subject, and body are required.'},
                        status=status.HTTP_400_BAD_REQUEST)

    funnels = Funnel.objects.filter(user=request.user, tag=tag)
    emails = set()
    for funnel in funnels:
        emails.update(funnel.visitors.values_list('email', flat=True))

    if not emails:
        return Response({'error': 'No leads found for this tag.'},
                        status=status.HTTP_404_NOT_FOUND)

    try:
        email_msg = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[],
            bcc=list(emails)
        )
        email_msg.send(fail_silently=False)
        return Response({'status': 'success', 'message': f'Email sent to {len(emails)} contacts'})
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
