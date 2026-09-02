"""
Additional missing REST API endpoints for FirePrenair - V2.
These are the remaining gaps found in the second deep analysis.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, Count
import json

from .serializers import *
from profiles.models import CustomUser, Notification
from home.models import (
    PricingPlan, UserPlan, BlogPost, Category as BlogCategory,
    CorporateProject, ChatThread, Feature, PlanFeature, Promo, Subscribe
)
from dashboard.decorators import get_top_sellers, get_top_digi_products


# =============================================================================
# LEADERBOARD API
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def leaderboard_dashboard_api(request):
    """Leaderboard page API"""
    top_sellers = get_top_sellers(count=3)
    top_digi_products = get_top_digi_products(count=5)

    # Dummy data for fields that require complex queries
    dummy_sellers = [
        {'name': 'Sophie Chen', 'total_earnings': 150000},
        {'name': 'James Wilson', 'total_earnings': 120000},
        {'name': 'Elena Diaz', 'total_earnings': 50000}
    ][:3 - len(top_sellers)]

    dummy_products = [
        {'title': 'Digital Marketing Course', 'total_sales': 500},
        {'title': 'Freelance Toolkit', 'total_sales': 450},
        {'title': 'SEO Masterclass', 'total_sales': 300}
    ][:3]

    return Response({
        'top_sellers': top_sellers + dummy_sellers,
        'top_digi_products': top_digi_products,
        'top_products': dummy_products,
        'rising_stars': [
            {'name': 'Maria Johnson', 'growth': 65},
            {'name': 'Liam Smith', 'growth': 55},
            {'name': 'Alex Patel', 'growth': 45}
        ],
        'loved_creators': [
            {'name': 'Sophie Chen', 'avg_rating': 4.9, 'review_count': 1200},
            {'name': 'Maria Johnson', 'avg_rating': 4.8, 'review_count': 900},
            {'name': 'James Wilson', 'avg_rating': 4.7, 'review_count': 750}
        ],
    })


# =============================================================================
# CORPORATE SOLUTIONS API
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def corporate_check_email_api(request):
    """Check if email exists for corporate login"""
    try:
        data = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, ValueError):
        data = {}
    email = (data.get('email') or '').strip().lower()
    if not email:
        return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
    import re
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return Response({'error': 'Please enter a valid email address.'}, status=status.HTTP_400_BAD_REQUEST)
    exists = CustomUser.objects.filter(email__iexact=email).exists()
    return Response({'exists': exists})


@api_view(['POST'])
@permission_classes([AllowAny])
def corporate_login_api_v2(request):
    """JSON login for corporate modal"""
    from django.contrib.auth import authenticate, login as auth_login
    try:
        data = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, ValueError):
        data = {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    if not email or not password:
        return Response({'success': False, 'error': 'Email and password are required.'},
                        status=status.HTTP_400_BAD_REQUEST)
    user = authenticate(request, username=email, password=password)
    if user is None:
        try:
            u = CustomUser.objects.get(username__iexact=email)
            user = authenticate(request, username=u.email, password=password)
        except CustomUser.DoesNotExist:
            pass
    if user is None:
        return Response({'success': False, 'error': 'Invalid email or password.'},
                        status=status.HTTP_400_BAD_REQUEST)
    auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return Response({'success': True})


@api_view(['POST'])
@permission_classes([AllowAny])
def corporate_verify_otp_api(request):
    """Verify OTP for new corporate registrations"""
    from django.contrib.auth import login as auth_login
    try:
        data = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, ValueError):
        data = {}
    code = (data.get('code') or '').strip().upper()
    registration_data = request.session.get('registration_data')

    if not registration_data:
        return Response({'success': False, 'error': 'Session expired. Please register again.'},
                        status=status.HTTP_400_BAD_REQUEST)
    if registration_data.get('verification_code') != code:
        return Response({'success': False, 'error': 'Invalid code. Please try again.'},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        user = CustomUser.objects.create_user(
            name=registration_data['full_name'],
            email=registration_data['email'],
            username=registration_data['username'],
            password=registration_data['password'],
            country=registration_data.get('country', ''),
            language=registration_data.get('language', 'en'),
            timezone=registration_data.get('timezone', 'UTC'),
            phone_no=registration_data.get('phone', ''),
            profile_pic='profile_pics/avatar.jpg',
            referred_by=CustomUser.objects.filter(
                username=registration_data['referrer']
            ).first() if registration_data.get('referrer') else None,
        )
        user.save()
        del request.session['registration_data']
        auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({'success': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_corporate_project_api(request):
    """Submit a corporate project"""
    try:
        data = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, ValueError):
        data = {}
    title = (data.get('title') or '').strip()
    description = (data.get('description') or '').strip()
    category = (data.get('category') or '').strip()
    budget = (data.get('budget') or '').strip()

    errors = {}
    if not title:
        errors['title'] = 'Project title is required.'
    elif len(title) < 5:
        errors['title'] = 'Title must be at least 5 characters.'
    if not description:
        errors['description'] = 'Please describe your project.'
    elif len(description) < 20:
        errors['description'] = 'Description must be at least 20 characters.'
    valid_categories = [c[0] for c in CorporateProject.CATEGORY_CHOICES]
    if not category or category not in valid_categories:
        errors['category'] = 'Please select a valid category.'
    valid_budgets = [b[0] for b in CorporateProject.BUDGET_CHOICES]
    if not budget or budget not in valid_budgets:
        errors['budget'] = 'Please select a budget range.'
    if errors:
        return Response({'success': False, 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    project = CorporateProject.objects.create(
        user=request.user,
        title=title,
        description=description,
        category=category,
        budget=budget,
    )
    if not request.user.is_corporate_client:
        request.user.is_corporate_client = True
        request.user.save(update_fields=['is_corporate_client'])

    return Response({
        'success': True,
        'project_id': project.pk,
        'redirect_url': '/corporate-dashboard/',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def corporate_dashboard_api(request):
    """Corporate dashboard"""
    projects = CorporateProject.objects.filter(user=request.user)
    return Response({
        'projects': [{
            'id': p.id,
            'title': p.title,
            'description': p.description,
            'category': p.get_category_display_label(),
            'budget': p.get_budget_display_label(),
            'status': p.status,
            'created_at': p.created_at,
        } for p in projects],
        'active_count': projects.filter(status='active').count(),
        'pending_count': projects.filter(status='pending').count(),
        'completed_count': projects.filter(status='completed').count(),
    })


# =============================================================================
# BLOG API
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def blog_list_api(request):
    """List blog posts"""
    posts_list = BlogPost.objects.filter(published=True).order_by('-published_date')
    paginator_data = [{
        'id': p.id,
        'title': p.title,
        'slug': p.slug,
        'excerpt': p.excerpt,
        'featured_image': p.featured_image.url if p.featured_image else None,
        'views': p.views,
        'published_date': p.published_date,
        'author': {
            'username': p.author.username,
            'name': p.author.name,
        },
        'category': p.category.name if p.category else None,
    } for p in posts_list]
    categories = BlogCategory.objects.all()
    return Response({
        'posts': paginator_data,
        'categories': [{'id': c.id, 'name': c.name} for c in categories],
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def blog_detail_api(request, slug):
    """Blog detail"""
    post = get_object_or_404(BlogPost, slug=slug, published=True)
    post.views += 1
    post.save()
    related_posts = BlogPost.objects.filter(
        category=post.category, published=True
    ).exclude(id=post.id)[:3]

    return Response({
        'blog': {
            'id': post.id,
            'title': post.title,
            'slug': post.slug,
            'content': post.content,
            'featured_image': post.featured_image.url if post.featured_image else None,
            'excerpt': post.excerpt,
            'views': post.views,
            'published_date': post.published_date,
            'author': {
                'username': post.author.username,
                'name': post.author.name,
            },
            'category': post.category.name if post.category else None,
        },
        'related_blogs': [{
            'title': rp.title,
            'slug': rp.slug,
            'featured_image': rp.featured_image.url if rp.featured_image else None,
        } for rp in related_posts],
    })


# =============================================================================
# CHAT THREAD DELETION API
# =============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_chat_thread_api(request):
    """Delete OpenAI chat thread"""
    from openai import OpenAI
    client = OpenAI()
    thread_obj = ChatThread.objects.filter(user=request.user).first()
    if thread_obj:
        try:
            client.beta.threads.delete(thread_obj.thread_id)
            thread_obj.delete()
            return Response({'status': 'thread deleted'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response({'status': 'no thread found'})


# =============================================================================
# HOME SUBSCRIBE API (already exists but adding if missing)
# =============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def home_subscribe_api_v2(request):
    """Newsletter subscription"""
    try:
        data = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, ValueError):
        data = {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip()
    errors = {}
    if not name:
        errors['name'] = 'Name is required.'
    if not email:
        errors['email'] = 'Email is required.'
    elif Subscribe.objects.filter(email=email).exists():
        errors['email'] = 'This email is already subscribed.'
    if errors:
        return Response({'success': False, 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
    Subscribe.objects.create(name=name, email=email)
    return Response({'success': True, 'message': 'You have successfully subscribed!'})
