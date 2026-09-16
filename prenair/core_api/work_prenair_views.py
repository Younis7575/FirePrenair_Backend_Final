from django.shortcuts import render, redirect, get_object_or_404, reverse
from .models import *
from commu_prenair.models import Message, PrivateChat
from django.contrib.auth.decorators import login_required
from django.conf import settings
# Nine views in this module call send_mail and none of them imported it.
# Every one raised NameError *after* saving its changes, so the database was
# mutated and the client still got a 500 — submit_requirements_api left orders
# active while telling the app the request had failed.
from django.core.mail import send_mail as _django_send_mail
# Same story as send_mail: used by the delivery and revision views and never
# imported. Both templates it is asked for -- emails/order_delivery_client.html
# and emails/revision_request_seller.html -- do not exist in this project
# either, so once the import was added the views swapped NameError for
# TemplateDoesNotExist. Delivering work and requesting a revision could never
# have succeeded. A missing notification template must not sink the request
# that already saved the delivery.
from django.template.loader import render_to_string as _django_render_to_string


def render_to_string(*args, **kwargs):
    """render_to_string that degrades to an empty body instead of raising."""
    try:
        return _django_render_to_string(*args, **kwargs)
    except Exception as exc:  # missing template, bad context…
        print(f"render_to_string failed (continuing): {exc}")
        return ""


def send_mail(*args, **kwargs):
    """send_mail that cannot fail the request it is called from.

    Every call site here fires *after* the order has already been saved, so
    letting an SMTP error escape rolls nothing back — it just reports failure
    for work the server actually did, and leaves the client's view stale.
    The module's own `send_email` helper already swallows errors this way.
    """
    try:
        return _django_send_mail(*args, **kwargs)
    except Exception as exc:  # SMTP down, refused sender, bad credentials…
        print(f"send_mail failed (continuing): {exc}")
        return 0
from django.views.decorators.csrf import csrf_exempt
import stripe
from django.http import JsonResponse
from .models import *
from django.db.models import Q
from django.utils.text import slugify
import uuid
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
import json
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from profiles.models import Notification

from django.db.models import Count
from django.db.models.functions import ExtractMonth, ExtractYear
from calendar import month_name
from django.utils.timezone import now, timedelta
from django.db.models import Avg
import re
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from django.views.decorators.http import require_http_methods

# ai 
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.safestring import mark_safe
import markdown
from groq import Groq
from openai import OpenAI
client = OpenAI(api_key=settings.OPENAI_API_KEY)
from django.views.decorators.http import require_POST
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes




from commu_prenair.models import *
from django.views.decorators.csrf import csrf_exempt
from django.utils.text import slugify
import uuid
import json
from edu_prenair.decorators import authenticated_user_required_commu,authenticated_user_required_commu_api
from django.conf import settings
from django.contrib.auth.decorators import login_required
from profiles.models import Notification

# ai 
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.safestring import mark_safe
import markdown
from groq import Groq

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login,logout
from django.contrib import messages
from profiles.models import CustomUser
from rest_framework.exceptions import AuthenticationFailed
from profiles.models import *
from home.models import *
from django.shortcuts import redirect
from work_prenair.views import send_email
import string
from django.utils.crypto import get_random_string
from django.conf import settings
from django.urls import reverse
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework.decorators import parser_classes

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .serializers import *
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view  # <-- Add this import
from rest_framework.decorators import permission_classes  # Import permission_classes decorator
from django.db.models import Q
import os










knowledge_base = {
    "workprenair": {
        "description": (
            "Workprenair is a platform where freelancers and clients connect. Freelancers can offer "
            "their services, and clients can hire them for various projects in fields like web development, graphic design, writing, and more."
        ),
        "faq": {
            "What is Workprenair?": (
                "Workprenair is a freelancing platform that connects clients with skilled freelancers for various projects."
            ),
            "How can I become a freelancer on Workprenair?": (
                "To become a freelancer, sign up on Workprenair, create a profile highlighting your skills, and start offering services in your niche."
            ),
            "How do I hire a freelancer?": (
                "To hire a freelancer, browse the available services, review freelancer profiles, and place an order for the service you need."
            ),
            "Can I negotiate the price of a service?": (
                "Yes, freelancers can set their own prices, and clients can discuss terms directly with freelancers before placing an order."
            ),
            "What types of services can I offer as a freelancer?": (
                "Freelancers can offer services in various categories such as web development, graphic design, writing, digital marketing, and more."
            ),
            "How do I get paid as a freelancer?": (
                "Freelancers receive payments through the platform after the client approves the work. Payments can be withdrawn via different methods available on Workprenair."
            ),
            "Is Workprenair safe to use?": (
                "Yes, Workprenair offers a secure platform with features like dispute resolution, reviews, and a secure payment system to ensure a safe experience for both freelancers and clients."
            ),
            "How can I leave a review for a freelancer?": (
                "Once a project is completed, clients can leave a review for the freelancer based on their experience, which helps build credibility on the platform."
            ),
            "How do I resolve disputes?": (
                "In case of a dispute, Workprenair provides a resolution process to mediate between the freelancer and client, ensuring both parties are satisfied."
            ),
            "Can I cancel an order as a client?": (
                "Clients can cancel an order before the freelancer starts working on it. After the work has started, cancellation may not be possible."
            ),
            "Do I need to pay upfront for services?": (
                "Workprenair requires clients to deposit funds into an escrow account before the freelancer starts working. The funds are released once the project is completed successfully."
            ),
        },
    }
}


@csrf_exempt
def workprenair_chatbot_view_api(request):
    if request.method == 'POST':
        user_message = request.POST.get('message', '').lower()
        
        # Predefined responses for quick replies
        predefined_responses = {
            "name": "I am your customer support assistant, here to help you with any questions about Workprenair.",
            "who_created_you": "I was created by the development team of Fireprenair.",
            "what_can_you_do": "I can help you navigate our platform, answer questions about our services, and provide consultation details.",
        }

        for key, response in predefined_responses.items():
            if key in user_message:
                return JsonResponse({"message": response})

        # Interact with Groq API
        client = Groq(api_key=settings.GROQ_API_KEY)
        groq_response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": json.dumps({
                    "knowledge_base": knowledge_base,
                    "instruction": "Please generate short, clear, and professional responses. "
                                   "Limit unnecessary details, ensure the tone is formal, and provide concise answers. "
                                   "Avoid elaboration and keep responses to the point."
                                   "Give answer according to question."
                })},
                {"role": "user", "content": user_message},
            ],
            model="llama3-8b-8192",
        )

        # Process the Groq response
        bot_reply = groq_response.choices[0].message.content.strip()
        bot_reply_html = markdown.markdown(bot_reply)
        bot_reply_html = mark_safe(bot_reply_html)

        return JsonResponse({"message": bot_reply_html})

    return JsonResponse({"message": "Only POST requests are allowed."}, status=400)


# @api_view(['GET'])
# @permission_classes([AllowAny])
# def work_home_api(request):
#     web_dev_gigs = Gig.objects.filter(category_level_1__name='Programming & Tech')[:8]
#     design_gigs = Gig.objects.filter(category_level_1__name='Graphics & Design')[:8]
#     ai_gigs = Gig.objects.filter(category_level_1__name='AI')[:8]
#     writing_gigs = Gig.objects.filter(category_level_1__name='Writing')[:8]
#     marketing_gigs = Gig.objects.filter(category_level_1__name='Digital Marketing')[:8]

#     top_categories = Category.objects.filter(is_featured=True, parent=None)

#     data = {
#         'web_dev_gigs': GigSerializer(web_dev_gigs, many=True).data,
#         'design_gigs': GigSerializer(design_gigs, many=True).data,
#         'ai_gigs': GigSerializer(ai_gigs, many=True).data,
#         'writing_gigs': GigSerializer(writing_gigs, many=True).data,
#         'marketing_gigs': GigSerializer(marketing_gigs, many=True).data,
#         'top_categories': WorkCategorySerializer(top_categories, many=True).data,
#     }

#     return Response(data)

from itertools import chain
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# How many gigs the home screen shows per top-level category, and overall.
HOME_GIGS_PER_CATEGORY = 8
HOME_GIGS_LIMIT = 40


@api_view(['GET'])
@permission_classes([AllowAny])
def work_home_api(request):
    """Gigs and featured categories for the WorkPrenair home screen.

    Gigs are grouped by whatever top-level categories actually exist rather
    than a hardcoded list of five names: previously a gig filed under any
    other category — including featured ones — never reached the home screen
    at all, and renaming a category silently emptied its row.
    """
    gigs = (
        Gig.objects.select_related(
            'user', 'category_level_1', 'category_level_2', 'category_level_3'
        )
        .prefetch_related('tags')
        .order_by('-featured', '-top_rated', '-created_at')
    )

    # Spread the selection across categories so one busy category can't fill
    # the whole screen, then top up with the newest gigs if there's room.
    per_category = {}
    picked, picked_ids = [], set()
    for gig in gigs[: HOME_GIGS_LIMIT * 4]:
        key = gig.category_level_1_id
        if per_category.get(key, 0) >= HOME_GIGS_PER_CATEGORY:
            continue
        per_category[key] = per_category.get(key, 0) + 1
        picked.append(gig)
        picked_ids.add(gig.pk)
        if len(picked) >= HOME_GIGS_LIMIT:
            break

    if len(picked) < HOME_GIGS_LIMIT:
        for gig in gigs.exclude(pk__in=picked_ids)[: HOME_GIGS_LIMIT - len(picked)]:
            picked.append(gig)

    top_categories = Category.objects.filter(
        is_featured=True, parent=None
    ).prefetch_related('subcategories')

    return Response({
        'all_gigs': GigSerializer(picked, many=True).data,
        'top_categories': CategoryWithSubcategoriesSerializer(
            top_categories, many=True
        ).data,
    })


# ------------------- DASHBOARD -------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sellor_dashboard_api(request):
    user = request.user

    if not user.is_work_freelancer:
        return Response({'detail': 'User is not a freelancer'}, status=403)

    user_gigs = user.gigs.all()
    gig_ids = user_gigs.values_list('id', flat=True)

    monthly_orders = (
        Order.objects.filter(gig__in=user_gigs)
        .annotate(month=ExtractMonth('created_at'), year=ExtractYear('created_at'))
        .values('month', 'year')
        .annotate(order_count=Count('id'))
        .order_by('year', 'month')
    )

    formatted_monthly_orders_data = [
        {
            "month_name": f"{month_name[data['month']]} {data['year']}",
            "order_count": data["order_count"]
        }
        for data in monthly_orders
    ]

    yearly_orders_data = list(
        Order.objects.filter(gig__in=user_gigs)
        .annotate(year=ExtractYear('created_at'))
        .values('year')
        .annotate(order_count=Count('id'))
        .order_by('year')
    )

    active_orders = Order.objects.filter(gig__in=user_gigs, is_completed=False, is_delivered=False)
    delivered_orders = Order.objects.filter(gig__in=user_gigs, is_delivered=True, is_completed=False)
    completed_orders = Order.objects.filter(gig__in=user_gigs, is_completed=True)

    notifications = Notification.objects.filter(user=user, app_name="workprenair")

    response_data = {
        'user_gigs': GigSerializer(user_gigs, many=True).data,
        'active_orders': OrderSerializer(active_orders, many=True).data,
        'delivered_orders': OrderSerializer(delivered_orders, many=True).data,
        'completed_orders': OrderSerializer(completed_orders, many=True).data,
        'active_orders_count': active_orders.count(),
        'delivered_orders_count': delivered_orders.count(),
        'completed_orders_count': completed_orders.count(),
        'notifications': NotificationSerializer(notifications, many=True).data,
        'formatted_monthly_orders_data': formatted_monthly_orders_data,
        'yearly_orders_data': yearly_orders_data,
        # The dashboard's four counters, as sellor_dashboard.html draws them.
        # `active_gigs_count` and `total_work_earnings` were missing, so the
        # app had no figure for the "Total Work Earnings" tile at all.
        'active_gigs_count': user_gigs.count(),
        'total_work_earnings': float(user.work_total_earnings or 0),
        # Which profile the account is on, so the client can offer the same
        # "Switch to Buyer" the website puts in its user menu.
        'is_work_freelancer': user.is_work_freelancer,
        'is_work_profile_approved': user.is_work_profile_approved,
    }

    return Response(response_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_orders_api(request):
    if request.user.is_work_freelancer:
        orders = Order.objects.filter(gig__user=request.user)
    else:
        orders = Order.objects.filter(user=request.user)
    active_orders = orders.filter(is_completed=False, is_delivered=False)
    completed_orders = orders.filter(is_completed=True)
    delivered_orders = orders.filter(is_delivered=True, is_completed=False)
    active_orders = OrderSerializer(active_orders, many=True).data
    completed_orders = OrderSerializer(completed_orders, many=True).data
    delivered_orders = OrderSerializer(delivered_orders, many=True).data
    context = {
        'active_orders': active_orders,
        'delivered_orders': delivered_orders,
        'completed_orders': completed_orders,
    }
    return Response(context)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def buyer_dashboard_api(request):
    user = request.user

    if user.is_work_freelancer:
        return Response({'detail': 'User is a freelancer'}, status=403)

    active_orders = Order.objects.filter(user=user, is_completed=False, is_delivered=False)
    completed_orders = Order.objects.filter(user=user, is_completed=True)
    delivered_orders = Order.objects.filter(user=user, is_delivered=True, is_completed=False)
    notifications = Notification.objects.filter(user=user, app_name="workprenair")
    reviews = Review.objects.filter(order__user=user, is_client_review=False)

    monthly_orders = (
        Order.objects.filter(user=user)
        .annotate(month=ExtractMonth('created_at'), year=ExtractYear('created_at'))
        .values('month', 'year')
        .annotate(order_count=Count('id'))
        .order_by('year', 'month')
    )

    chart_data = [
        {
            "month_name": f"{month_name[data['month']]} {data['year']}",
            "order_count": data["order_count"]
        }
        for data in monthly_orders
    ]

    response_data = {
        'active_orders': OrderSerializer(active_orders, many=True).data,
        'completed_orders': OrderSerializer(completed_orders, many=True).data,
        'delivered_orders': OrderSerializer(delivered_orders, many=True).data,
        'notifications': NotificationSerializer(notifications, many=True).data,
        'reviews': ReviewSerializer(reviews, many=True).data,
        'chart_data': chart_data,
    }

    return Response(response_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def workprenair_notifications_api(request):
    user = request.user

    # Mark unread notifications as read
    Notification.objects.filter(user=user, is_read=False, app_name='workprenair').update(is_read=True)

    # Fetch all notifications
    notifications = Notification.objects.filter(user=user, app_name='workprenair').order_by("-created_at")
    serializer = NotificationSerializer(notifications, many=True)

    return Response({
        "user": user.username,
        "notifications": serializer.data
    })



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile_api(request, username):
    try:
            
        user = get_object_or_404(CustomUser, username=username)

        data = {
            'user': UserSerializer(user).data,
            'user_gigs': [],
            'user_orders': [],
            'user_reviews_as_client': [],
            'user_reviews_as_seller': [],
            'rating_range': list(range(1, 6))
        }

        if user.is_work_freelancer:
            gigs = Gig.objects.filter(user=user)
            reviews_as_seller = Review.objects.filter(gig__user=user, is_client_review=True)
            data['user_gigs'] = GigSerializer(gigs, many=True).data
            data['user_reviews_as_seller'] = ReviewSerializer(reviews_as_seller, many=True).data
        else:
            orders = Order.objects.filter(user=user)
            order_ids = orders.values_list('id', flat=True)
            reviews_as_client = Review.objects.filter(order_id__in=order_ids, is_client_review=False)
            data['user_orders'] = OrderSerializer(orders, many=True).data
            data['user_reviews_as_client'] = ReviewSerializer(reviews_as_client, many=True).data

        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])  # for handling file uploads
def edit_profile_api(request):
    user = request.user
    serializer = EditUserProfileSerializer(user, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Profile updated successfully.", "user": serializer.data}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)





@api_view(['GET'])
@permission_classes([IsAuthenticated])
def todos_api(request):
    todos = Todo.objects.filter(user=request.user)
    serializer = TodoSerializer(todos, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_todo_api(request):
    if not request.user.is_work_freelancer:
        return Response({'status': 'error', 'message': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    title = request.POST.get('title')
    description = request.POST.get('description')
    if not title or not description:
        return Response({'status': 'error', 'message': 'enter the title adn desctiption'}, status=status.HTTP_403_FORBIDDEN)

    serializer = TodoSerializer(data=request.data)
    if serializer.is_valid():
        todo = serializer.save(user=request.user)
        return Response(TodoSerializer(todo).data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_todo_api(request, pk):
    try:
        todo = Todo.objects.get(pk=pk, user=request.user)
    except Todo.DoesNotExist:
        return Response({'error': 'Todo not found or you do not have permission to update it.'}, status=status.HTTP_404_NOT_FOUND)

    # Update fields
    title = request.data.get('title')
    description = request.data.get('description')
    is_completed = request.data.get('is_completed')

    if title:
        todo.title = title
    if description:
        todo.description = description
    if is_completed is not None:
        todo.is_completed = is_completed == 'true'
        if todo.is_completed:
            todo.completed_at = timezone.now()
        else:
            todo.completed_at = None

    todo.save()

    # Serialize and return the updated todo
    serializer = TodoSerializer(todo)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_todo_api(request, pk):
    try:
        todo = Todo.objects.get(pk=pk, user=request.user)
        todo.delete()
        return Response({'status': 'success'}, status=status.HTTP_204_NO_CONTENT)
    except Todo.DoesNotExist:
        return Response({'error': 'Todo not found or you do not have permission to delete it.'}, status=status.HTTP_404_NOT_FOUND)



from rest_framework.pagination import PageNumberPagination

@api_view(['GET'])
def gigs_api(request):
    try:
        keyword = request.GET.get('keyword', '').strip()
        category_id = request.GET.get('category', '').strip()
        min_price = request.GET.get('min_price', '0').strip()
        max_price = request.GET.get('max_price', '3000').strip()
        delivery_time = request.GET.get('delivery_time', '').strip()
        location_filter = request.GET.get('location', '').strip()
        sort_by = request.GET.get('sort_by', 'relevance')

        gigs = Gig.objects.all()

        # Filtering by keyword
        if keyword:
            gigs = gigs.filter(
                Q(title__icontains=keyword) |
                Q(description__icontains=keyword) |
                Q(tags__name__icontains=keyword)
            ).distinct()

        # Filtering by category
        if category_id and category_id.isdigit():
            try:
                category_id = int(category_id)
                gigs = gigs.filter(
                    Q(category_level_1_id=category_id) |
                    Q(category_level_2_id=category_id) |
                    Q(category_level_3_id=category_id)
                ).distinct()
            except ValueError:
                pass

        # Filtering by price
        def is_valid_price(value):
            try:
                float(value)
                return True
            except:
                return False

        if is_valid_price(min_price) and is_valid_price(max_price):
            min_val = float(min_price)
            max_val = float(max_price)
            gigs = gigs.filter(
                Q(basic_price__gte=min_val, basic_price__lte=max_val) |
                Q(standard_price__gte=min_val, standard_price__lte=max_val) |
                Q(premium_price__gte=min_val, premium_price__lte=max_val)
            ).distinct()

        # Filtering by delivery time
        delivery_days = {
            "1 Day": 1,
            "2-4 Days": 4,
            "1 Week": 7,
            "Above One Month": 30
        }
        if delivery_time:
            max_days = delivery_days.get(delivery_time, 30)
            gigs = gigs.filter(
                Q(basic_delivery_time__lte=max_days) |
                Q(standard_delivery_time__lte=max_days) |
                Q(premium_delivery_time__lte=max_days)
            ).distinct()

        # Filtering by location
        country_mapping = {
            'United States': 'United States',
            'Canada': 'Canada',
            'United Kingdom': 'United Kingdom',
            'India': 'India',
            'Pakistan': 'Pakistan',
            'Bangladesh': 'Bangladesh',
        }
        if location_filter:
            location_filter = country_mapping.get(location_filter, location_filter)
            gigs = gigs.filter(user__country__iexact=location_filter)

        # Sorting
        if sort_by == "price_low":
            gigs = gigs.order_by('basic_price')
        elif sort_by == "price_high":
            gigs = gigs.order_by('-basic_price')
        elif sort_by == "rating":
            gigs = gigs.annotate(avg_rating=Avg('gig_fivestar_reviews__rating')).order_by('-avg_rating')
        elif sort_by == "newest":
            gigs = gigs.order_by('-created_at')

        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = 20  # Customize the page size if needed
        result_page = paginator.paginate_queryset(gigs, request)
        serializer = GigSerializer(result_page, many=True)

        # Get categories for filter options
        categories = WorkCategory.objects.filter(parent=None)
        category_serializer = WorkCategorySerializer(categories, many=True)

        # Return response with filtered, paginated gigs
        return paginator.get_paginated_response({
            'gigs': serializer.data,
            'categories': category_serializer.data,
            'keyword': keyword,
            'min_price': min_price,
            'max_price': max_price,
            'delivery_time': delivery_time,
            'location': location_filter,
            'sort_by': sort_by,
            'selected_category': category_id,
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
@api_view(['GET'])
def get_child_categories_api(request, parent_id):
    categories = Category.objects.filter(parent_id=parent_id).values('id', 'name')
    return Response({'status': 'success', 'categories': list(categories)}, status=status.HTTP_200_OK)


@api_view(['GET'])
def search_tags_api(request):
    query = request.GET.get('q', '').strip()
    if query:
        tags = Tag.objects.filter(name__icontains=query).values('id', 'name')
        return Response({'status': 'success', 'tags': list(tags)}, status=status.HTTP_200_OK)
    return Response({'status': 'success', 'tags': []}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gig_tags_api(request, gig_slug):
    try:
        gig = Gig.objects.get(slug=gig_slug)
        tags = gig.tags.all().values('id', 'name')
        return Response({'status': 'success', 'tags': list(tags)}, status=status.HTTP_200_OK)
    except Gig.DoesNotExist:
        return Response({'status': 'error', 'message': 'Gig not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_tag_api(request):
    name = request.data.get('name', '').strip()

    if not name:
        return Response({'status': 'error', 'error': 'Name is required'}, status=status.HTTP_400_BAD_REQUEST)

    tag = Tag.objects.filter(name__iexact=name).first()
    if tag:
        created = False
    else:
        tag = Tag.objects.create(name=name)
        created = True

    return Response({
        'status': 'success',
        'created': created,
        'tag': {'id': tag.id, 'name': tag.name}
    }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_gigs_api(request):
    if not request.user.is_work_freelancer:
        return Response({'status': 'error', 'message': 'User is not a freelancer.'}, status=status.HTTP_403_FORBIDDEN)

    gigs = Gig.objects.filter(user=request.user)
    serializer = GigSerializer(gigs, many=True)
    return Response({'status': 'success', 'gigs': serializer.data}, status=status.HTTP_200_OK)




@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, JSONParser])  # Handles image + JSON in multipart form
def create_gig_api(request):
    if not request.user.is_work_freelancer:
        # Optional: Allow creation and promote to freelancer inside serializer
        pass

    serializer = GigCreateSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        gig = serializer.save()
        return Response({
            'status': 'success',
            'gig_slug': gig.slug,
            'gig_id': gig.id
        }, status=status.HTTP_201_CREATED)
    return Response({'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, JSONParser])
def edit_gig_api(request, slug):
    try:
        gig = Gig.objects.get(slug=slug, user=request.user)
    except Gig.DoesNotExist:
        return Response({'status': 'error', 'message': 'Gig not found or unauthorized.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = GigUpdateSerializer(gig, data=request.data, partial=True, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response({'status': 'success', 'gig_slug': gig.slug}, status=status.HTTP_200_OK)

    return Response({'status': 'error', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def gig_detail_api(request, slug):
    try:
        gig = Gig.objects.get(slug=slug)
    except Gig.DoesNotExist:
        return Response({'status': 'error', 'message': 'Gig not found'}, status=status.HTTP_404_NOT_FOUND)

    prev_gig = Gig.objects.filter(created_at__lt=gig.created_at).order_by('-created_at').first()
    next_gig = Gig.objects.filter(created_at__gt=gig.created_at).order_by('created_at').first()

    serializer = GigSerializer(gig)

    return Response({
        'status': 'success',
        'gig': serializer.data,
        'rating_range': list(range(1, 6)),
        'prev_gig': {
            'id': prev_gig.id,
            'slug': prev_gig.slug,
            'title': prev_gig.title
        } if prev_gig else None,
        'next_gig': {
            'id': next_gig.id,
            'slug': next_gig.slug,
            'title': next_gig.title
        } if next_gig else None
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
def optimize_gig_api(request, slug):
    # Check if the user is authenticated
    if not request.user.is_authenticated:
        return Response({'error': 'Unauthorized access'}, status=status.HTTP_403_FORBIDDEN)

    # Retrieve the gig by slug
    gig = get_object_or_404(Gig, slug=slug)

    # Check if the logged-in user owns the gig
    if request.user != gig.user:
        return Response({'error': 'Unauthorized access'}, status=status.HTTP_403_FORBIDDEN)

    try:
        prompt = f"""
        Act as a professional gig optimizer for a freelancing platform. Analyze this gig data and suggest improvements:

        Current Title: {gig.title}
        Current Description: {gig.description}
        Current Tags: {', '.join([tag.name for tag in gig.tags.all()])}
        Categories: {gig.category_level_1}, {gig.category_level_2}, {gig.category_level_3}
        Packages:
        - Basic: {gig.basic_description} (Delivery: {gig.basic_delivery_time} days)
        - Standard: {gig.standard_description} (Delivery: {gig.standard_delivery_time} days)
        - Premium: {gig.premium_description} (Delivery: {gig.premium_delivery_time} days)

        Provide:
        1. 5 improved titles focusing on clarity and SEO
        2. 3 enhanced descriptions (300-500 characters each)
        3. 15 relevant keywords/tags considering the categories
        Return ONLY a JSON response with keys: 'titles', 'descriptions', 'keywords'
        """

        # Request to OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": prompt
            }],
            temperature=0.7,
            max_tokens=1000
        )

        ai_content = response.choices[0].message.content
        cleaned_content = ai_content.strip()

        # Clean and parse the AI response
        if cleaned_content.startswith('```json'):
            cleaned_content = cleaned_content[7:-3].strip()
        elif cleaned_content.startswith('```'):
            cleaned_content = cleaned_content[3:-3].strip()

        cleaned_content = re.sub(r',\s*}', '}', cleaned_content)
        cleaned_content = re.sub(r',\s*]', ']', cleaned_content)
        suggestions = json.loads(cleaned_content)

        # Ensure the correct structure of the response
        required_keys = ['titles', 'descriptions', 'keywords']
        if not all(key in suggestions for key in required_keys):
            raise ValueError("Invalid AI response structure")

        return Response(suggestions)

    except json.JSONDecodeError as e:
        return Response({'error': f'Invalid JSON format from AI: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
def apply_gig_ai_suggestion_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"status": "error", "message": "Authentication required"},status=401)

    try:
        data = request.data
        gig_slug = data.get('gig_slug')
        suggestion_type = data.get('type')
        value = data.get('value')

        if not all([gig_slug, suggestion_type, value]):
            return JsonResponse({"status": "error", "message": "Missing required fields"},status=400)

        try:
            gig = Gig.objects.get(slug=gig_slug)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Gig not found"},
                status=404
            )

        if gig.user != request.user:
            return JsonResponse({"status": "error", "message": "Permission denied"},status=403)

        if suggestion_type == 'title':
            if len(value) > 255:
                return JsonResponse({"status": "error", "message": "Title too long (max 255 characters)"},status=400)
            gig.title = value
            gig.save(update_fields=['title'])

        elif suggestion_type == 'description':
            gig.description = value
            gig.save(update_fields=['description'])

        elif suggestion_type == 'keyword':
            tag_name = value.strip().lower()
            if not tag_name:
                return JsonResponse({"status": "error", "message": "Invalid tag name"},status=400)
            
            if gig.tags_count() >= 10:
                return JsonResponse({"status": "error", "message": "You can only have up to 10 tags"},status=400)
        
            if len(tag_name) > 50:
                return JsonResponse({"status": "error", "message": "Tag name too long (max 50 characters)"},status=400)
            
            tag, created = Tag.objects.get_or_create(name=tag_name)
            if not created and tag in gig.tags.all():
                return JsonResponse({"status": "error", "message": "Tag already exists"},status=400)
            gig.tags.add(tag)

        else:
            return JsonResponse({"status": "error", "message": "Invalid suggestion type"},status=400)

        return JsonResponse({
            "status": "success",
            "message": "Suggestion applied successfully",
            "type": suggestion_type,
            "value": value
        })

    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "message": "Invalid JSON format"},
            status=400
        )
    except IntegrityError as e:
        return JsonResponse(
            {"status": "error", "message": f"Database error: {str(e)}"},
            status=500
        )
    except ValidationError as e:
        return JsonResponse(
            {"status": "error", "message": str(e)},
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {"status": "error", "message": f"Unexpected error: {str(e)}"},
            status=500
        )



@api_view(['DELETE'])
def delete_gig_api(request, slug):
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({'error': 'Unauthorized access'}, status=status.HTTP_403_FORBIDDEN)
    
    # Retrieve the gig object
    gig = get_object_or_404(Gig, slug=slug)

    # Check if the authenticated user is the owner of the gig
    if request.user != gig.user:
        return Response({'error': 'You are not authorized to perform this action.'}, status=status.HTTP_403_FORBIDDEN)

    # Delete the gig
    gig.delete()

    # Return a success message
    return Response({'message': 'Gig deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def order_detail_api(request, order_slug):
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({'error': 'Unauthorized access'}, status=status.HTTP_403_FORBIDDEN)

    # Retrieve the order by slug
    order = get_object_or_404(Order, slug=order_slug)

    # Check if the authenticated user is authorized to view the order
    if request.user != order.user and request.user != order.gig.user:
        return Response({'error': 'You are not authorized to view this order.'}, status=status.HTTP_403_FORBIDDEN)

    def _user(u):
        return {
            'id': u.id,
            'username': u.username,
            'name': u.name,
            'slug': u.slug,
            'email': u.email,
            'profile_pic': u.profile_pic.url if u.profile_pic else None,
        }

    # order_detail.html renders far more than this endpoint used to return:
    # the requirements, the deliveries and their revision requests, the
    # reviews, and the flags that decide which of Submit Requirements /
    # Submit Work / Request Revision / Complete / Leave A Review is offered.
    # Without them a client could show the page but none of its actions.
    deliveries = []
    for delivery in order.deliveries():
        deliveries.append({
            'slug': delivery.slug,
            'message': delivery.message,
            'file': delivery.file.url if delivery.file else None,
            'created_at': delivery.created_at,
            'developer': _user(delivery.developer),
            'revisions': [
                {
                    'slug': revision.slug,
                    'message': revision.message,
                    'is_resolved': revision.is_resolved,
                    'created_at': revision.created_at,
                    'client': _user(revision.client),
                }
                for revision in delivery.revisions()
            ],
        })

    # `order_review()`, `client_reviews()` and `seller_review()` all return
    # querysets despite two of them reading as singular, so every one of them
    # is serialised as a list.
    def _review(review):
        return {
            'rating': review.rating,
            'review': review.review,
            'is_client_review': review.is_client_review,
            'created_at': review.created_at,
            'user': _user(review.user),
        }

    is_buyer = request.user == order.user

    order_data = {
        # submit_requirements_api is keyed on the numeric id, not the slug.
        'id': order.id,
        'order_slug': order.slug,
        'gig_title': order.gig.title,
        'gig_slug': order.gig.slug,
        'gig_image': order.gig.image.url if getattr(order.gig, 'image', None) else None,
        'gig_description': order.gig.description,
        'order_status': order.status,
        'order_date': order.created_at,
        'package_type': order.package_type,
        'price': float(order.price or 0),
        'requirements': order.requirements,
        'delivery_date': order.delivery_date,
        'delivery_days': order.delivery_days,
        'completed_on': order.completed_on,
        'is_paid': order.is_paid,
        'is_delivered': order.is_delivered,
        'is_completed': order.is_completed,
        'has_client_reviewed': order.has_client_reviewed,
        'has_seller_reviewed': order.has_seller_reviewed,
        # Which side of the order the caller is on, so the client does not have
        # to compare usernames to decide what to show.
        'is_buyer': is_buyer,
        'is_seller': request.user == order.gig.user,
        'deliveries': deliveries,
        'order_review': [_review(r) for r in order.order_review()],
        'client_reviews': [_review(r) for r in order.client_reviews()],
        'seller_review': [_review(r) for r in order.seller_review()],
        'user': _user(order.user),
        'gig_user': _user(order.gig.user),
        'rating_range': list(range(1, 6)),  # Rating range from 1 to 5
    }

    return Response(order_data, status=status.HTTP_200_OK)

@api_view(['POST'])
def submit_requirements_api(request, order_id):
    # Check if the user is authenticated
    if not request.user.is_authenticated:
        return Response({"message": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

    # Get the order
    order = get_object_or_404(Order, id=order_id)

    # Ensure the current user is the one who placed the order
    if request.user != order.user:
        return Response({"message": "You are not authorized to perform this action."}, status=status.HTTP_403_FORBIDDEN)

    # Get the requirements from the request data
    requirements = request.data.get('requirements')

    if not requirements:
        return Response({"message": "Requirements are required."}, status=status.HTTP_400_BAD_REQUEST)

    # Update the order with new requirements and set its status to active
    order.requirements = requirements
    order.status = "active"
    order.delivery_date = now() + timedelta(days=order.delivery_days)
    order.save()

    # Send notification to the seller (gig user)
    Notification.objects.create(
        user=order.gig.user,
        app_name="workprenair",
        message=f"Requirements submitted for Order #{order.id}. Start working on it now."
    )

    # Send email to the buyer
    buyer_url = request.build_absolute_uri(f"/orders/{order.slug}/")  # Assuming the URL structure
    buyer_email_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
            <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                    <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                </div>
                <div style="padding: 20px;">
                    <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">Your Order #{order.id} is Now Active!</h2>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {request.user.username},</p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                        Your requirements for Order #{order.id} have been submitted successfully. The seller has been notified and will begin working on your order.
                    </p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Click below to view your order details:</p>
                    <p style="text-align: center; margin: 20px 0;">
                        <a href="{buyer_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">View Order Details</a>
                    </p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Need help? Our support team is always here for you.</p>
                </div>
                <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                    <p style="margin: 0; font-size: 14px;">Thank you for choosing FirePrenair! 🚀</p>
                </div>
            </div>
        </body>
        </html>
    """
    send_mail(
        subject=f"Order #{order.id} is Now Active!",
        message="",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[request.user.email],
        html_message=buyer_email_content
    )

    # Send email to the seller
    seller_email_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
            <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                    <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                </div>
                <div style="padding: 20px;">
                    <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">Order #{order.id} is now Active!</h2>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {order.gig.user.username},</p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                        The buyer has submitted the requirements for Order #{order.id}. You can now start working on it.
                    </p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Log in to your dashboard to view the details and manage the order:</p>
                    <p style="text-align: center; margin: 20px 0;">
                        <a href="{buyer_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">View Order Details</a>
                    </p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Thank you for your dedication to providing excellent service!</p>
                </div>
                <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                    <p style="margin: 0; font-size: 14px;">Best Regards, The FirePrenair Team</p>
                </div>
            </div>
        </body>
        </html>
    """
    send_mail(
        subject=f"Order #{order.id} is now Active!",
        message="",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.gig.user.email],
        html_message=seller_email_content
    )

    # Return success response
    return Response({
        "message": "Requirements submitted successfully, Order is now active!",
        "order_id": order.id
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def order_delivery_api(request, order_slug):
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"message": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

    # Get the order
    order = get_object_or_404(Order, slug=order_slug)

    # Ensure that the current user is the seller of the gig
    if request.user != order.gig.user:
        return Response({"message": "You are not authorized to perform this action."}, status=status.HTTP_403_FORBIDDEN)

    # Get data from the request
    message = request.data.get('message')
    file = request.FILES.get('file')

    if not file:
        return Response({"message": "File is required."}, status=status.HTTP_400_BAD_REQUEST)

    # Validate the file type (must be a .zip file)
    if not file.name.endswith('.zip'):
        return Response({"message": "Please upload a ZIP file."}, status=status.HTTP_400_BAD_REQUEST)

    # Generate a unique slug for the delivery
    u_id = uuid.uuid4()
    slug = f"Delivery-for-Order-{order.slug}-{u_id}"

    # Check if there was a previous delivery and delete it
    prev_delivery = Delivery.objects.filter(order=order).first()
    if prev_delivery:
        prev_delivery.delete()

    # Create the new delivery entry
    delivery = Delivery.objects.create(
        order=order,
        developer=request.user,
        message=message,
        file=file,
        slug=slug
    )

    # Update order status to "delivered"
    order.is_delivered = True
    order.status = "delivered"
    order.save()

    # Create a notification for the buyer
    Notification.objects.create(
        user=order.user,
        app_name="workprenair",
        message=f"Your order has been delivered by {request.user.username}."
    )

    # Build the URL for the order details page
    delivery_review_url = request.build_absolute_uri(f"/orders/{order.slug}/")

    # Send email to the client
    client_email_content = render_to_string('emails/order_delivery_client.html', {
        'order': order,
        'delivery_review_url': delivery_review_url,
        'user': request.user
    })

    send_mail(
        subject=f"📦 Order Delivered! #{order.id}",
        message="",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.user.email],
        html_message=client_email_content
    )

    return Response({
        "message": "Delivery submitted successfully.",
        "order_id": order.id
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
def request_revision_api(request, delivery_slug):
    # Get the delivery object
    delivery = get_object_or_404(Delivery, slug=delivery_slug)
    order = delivery.order

    # Check if the user is the client (buyer)
    if request.user != order.user:
        return Response({"message": "You are not authorized to request a revision."}, status=status.HTTP_403_FORBIDDEN)

    # Check if the order is completed
    if order.is_completed:
        return Response({"message": "Order has already been completed."}, status=status.HTTP_400_BAD_REQUEST)

    # Check if the order is delivered
    if not order.is_delivered:
        return Response({"message": "Order is not yet delivered."}, status=status.HTTP_400_BAD_REQUEST)

    # Get the message from the request body
    message = request.data.get('message')

    if not message:
        return Response({"message": "Message is required."}, status=status.HTTP_400_BAD_REQUEST)

    # Create a unique slug for the revision request
    u_id = uuid.uuid4()
    slug = f"Revision-Request-for-Delivery-{delivery.slug}-{u_id}"

    # Create the revision request
    revision_request = RevisionRequest.objects.create(
        delivery=delivery,
        client=order.user,
        message=message,
        slug=slug
    )

    # Reset the order status to "active" and set it back to not delivered
    order.is_completed = False
    order.is_delivered = False
    order.status = "active"
    order.completed_on = None
    order.save()

    # Create a notification for the developer (seller)
    Notification.objects.create(
        user=delivery.developer,
        app_name="workprenair",
        message=f"Revision request received for Order #{order.id}."
    )

    # Build the URL for the order details page
    revision_request_url = f"/orders/{order.slug}/"  # You can adjust this based on your domain settings

    # Send email to the seller (developer)
    seller_revision_email_content = render_to_string('emails/revision_request_seller.html', {
        'order': order,
        'delivery': delivery,
        'revision_request_url': revision_request_url,
        'user': request.user
    })

    send_mail(
        subject=f"🔄 Revision Requested for Order #{order.id}",
        message="",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[delivery.developer.email],
        html_message=seller_revision_email_content
    )

    # Return success response
    return Response({
        "message": "Revision request sent successfully.",
        "revision_request_id": revision_request.id
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
def complete_order_api(request, order_slug):
    # Get the order or return 404 if not found
    order = get_object_or_404(Order, slug=order_slug)
    
    # Check if the user is authorized to complete the order
    if request.user != order.user and request.user != order.gig.user:
        return Response({"detail": "You are not authorized to complete this order."}, status=status.HTTP_403_FORBIDDEN)

    # Mark the order as completed
    order.is_completed = True
    order.completed_on = timezone.now()
    order.status = "completed"
    
    # Calculate the order amount after commission
    order_amount = order.price - (order.price * Decimal('0.17'))

    # Update the gig's user earnings
    order.gig.user.work_total_earnings += order_amount
    order.gig.user.total_earnings += order_amount
    order.gig.user.available_earnings += order_amount
    order.gig.user.save()

    # Save the order after updating it
    order.save()

    # Create a notification for the gig user (seller)
    Notification.objects.create(
        user=order.gig.user,
        app_name="workprenair",
        message=f"Order completed by {order.user.username}."
    )

    # Build the client email content
    client_email_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
        <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
            <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
            </div>
            <div style="padding: 20px;">
                <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🎉 Order Completed Successfully! #{order.id}</h2>
                <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {order.user.username},</p>
                <p style="color: #333; font-size: 16px; line-height: 1.6;">
                    Your order for <strong>{order.gig.title}</strong> has been successfully completed on <strong>FirePrenair</strong>. Thank you for trusting us!
                </p>
                <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                    <li><strong>Order ID:</strong> {order.id}</li>
                    <li><strong>Product/Service:</strong> {order.gig.title}</li>
                    <li><strong>Amount Paid:</strong> ${order.price}</li>
                    <li><strong>Completion Date:</strong> {order.completed_on.strftime('%B %d, %Y')}</li>
                </ul>
                <p style="color: #333; font-size: 16px; line-height: 1.6;">We hope to see you again for your future needs. 🚀</p>
            </div>
            <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                <p style="margin: 0; font-size: 14px;">Thank you for choosing FirePrenair!</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Send email to the client
    send_mail(
        subject=f"🎉 Order #{order.id} Completed Successfully!",
        message=client_email_content,
        from_email='no-reply@fireprenair.com',
        recipient_list=[order.user.email],
        html_message=client_email_content
    )

    # Build the seller email content
    seller_email_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
        <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
            <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
            </div>
            <div style="padding: 20px;">
                <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🎉 Order Completed and Earnings Added! #{order.id}</h2>
                <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {order.gig.user.username},</p>
                <p style="color: #333; font-size: 16px; line-height: 1.6;">
                    Great job! Your order for <strong>{order.gig.title}</strong> has been marked as completed by the client on <strong>FirePrenair</strong>.
                </p>
                <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                    <li><strong>Order ID:</strong> {order.id}</li>
                    <li><strong>Client:</strong> {order.user.username}</li>
                    <li><strong>Product/Service:</strong> {order.gig.title}</li>
                    <li><strong>Earnings Added:</strong> ${order_amount}</li>
                    <li><strong>Completion Date:</strong> {order.completed_on.strftime('%B %d, %Y')}</li>
                </ul>
                <p style="color: #333; font-size: 16px; line-height: 1.6;">
                    Your earnings have been added to your account and are now available. Thank you for delivering excellence!
                </p>
            </div>
            <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                <p style="margin: 0; font-size: 14px;">Thank you for being an amazing seller on FirePrenair!</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Send email to the seller
    send_mail(
        subject=f"🎉 Order #{order.id} Completed and Earnings Added!",
        message=seller_email_content,
        from_email='no-reply@fireprenair.com',
        recipient_list=[order.gig.user.email],
        html_message=seller_email_content
    )

    # Return success response
    return Response({"detail": "Order completed successfully."}, status=status.HTTP_200_OK)

@api_view(['POST'])
def review_order_api(request, order_slug):
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

    # Get the order or return 404 if not found
    order = get_object_or_404(Order, slug=order_slug)

    # Check if the user is authorized to review this order (either client or seller)
    if request.user != order.user and request.user != order.gig.user:
        return Response({"detail": "You are not authorized to review this order."}, status=status.HTTP_403_FORBIDDEN)

    # Handle the review submission
    if request.method == 'POST':
        rating = request.data.get('rating')
        review = request.data.get('review')

        # Ensure rating and review are provided
        if not rating or not review:
            return Response({"detail": "Rating and review are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Determine if the review is from the client or seller
        is_client_review = True if request.user == order.user else False

        # Create the review
        Review.objects.create(
            order=order,
            gig=order.gig,
            user=request.user,
            rating=rating,
            review=review,
            is_client_review=is_client_review
        )

        # Update the order status
        order.has_client_reviewed = True
        order.has_seller_reviewed = True if request.user == order.gig.user else False
        order.save()

        # Create notification for the respective user
        if is_client_review:
            Notification.objects.create(
                user=order.gig.user,
                app_name="workprenair",
                message=f"Order reviewed by {request.user.username}."
            )
        else:
            Notification.objects.create(
                user=order.user,
                app_name="workprenair",
                message=f"Order reviewed by {request.user.username}."
            )

        # Return success response
        return Response({"detail": "Review submitted successfully."}, status=status.HTTP_200_OK)

    # If method is not POST, return bad request
    return Response({"detail": "Invalid method."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


# ------------------- Stripe -------------------

stripe.api_key = settings.STRIPE_SECRET_KEY
from decimal import Decimal

@api_view(['POST'])
def gig_checkout_api(request, gig_slug, package_type):
    user = request.user
    gig = get_object_or_404(Gig, slug=gig_slug)

    # Determine price based on package_type
    if package_type == "basic":
        price = gig.basic_price + (gig.basic_price * Decimal('0.05'))  # Adding 5% fee
    elif package_type == "standard":
        price = gig.standard_price + (gig.standard_price * Decimal('0.05'))
    elif package_type == "premium":
        price = gig.premium_price + (gig.premium_price * Decimal('0.05'))
    else:
        return Response({"error": "Invalid package type selected."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        success_url = request.build_absolute_uri(reverse("buyer_dashboard"))
        cancel_url = request.build_absolute_uri(reverse("gig_detail", args=[gig.slug]))

        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"{gig.title} - {package_type.capitalize()} \n Price: ${price} With 5% Processing Fee"
                        },
                        "unit_amount": int(price * 100),  # Convert to cents
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_slug": user.slug,
                "gig_slug": gig.slug,
                "package_type": package_type,
            },
        )

        return Response({"checkout_url": checkout_session.url}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def custom_offer_checkout_api(request, offer_id):
    user = request.user
    offer = get_object_or_404(CustomOffer, id=offer_id, recipient=user)

    # Check if the offer has already been accepted
    if offer.is_accepted:
        return Response({"error": "This offer has already been paid for."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Build the success and cancel URLs
        success_url = request.build_absolute_uri(reverse("buyer_dashboard"))
        cancel_url = request.build_absolute_uri(reverse("custom_offers_list"))

        # Create the Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"Custom Offer - {offer.description[:50]}... \n Price: ${offer.price} + 5% Processing Fee"
                        },
                        "unit_amount": int((offer.price + offer.price * Decimal('0.05')) * 100),  # Price in cents
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "offer_id": offer.id,
                "user_slug": user.slug,
            },
        )

        # Return the checkout session URL to the client
        return Response({"checkout_url": checkout_session.url}, status=status.HTTP_200_OK)

    except Exception as e:
        # Handle errors and return a response
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ------------------- Email Notifications -------------------
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
def send_email(to_email, subject, html_content):
    message = Mail(
        from_email='support@fireprenair.com',
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )
    try:
        sg = SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        sg.send(message)
    except Exception as e:
        print(f"Error sending email: {e}")
    
# ------------------- Stripe Webhooks -------------------

class StripeWebhookView(APIView):
    """
    Webhook view for handling Stripe events
    """

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        event = None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET_GIG_ORDER
            )
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            user_slug = session.get("metadata", {}).get("user_slug")
            gig_slug = session.get("metadata", {}).get("gig_slug")
            package_type = session.get("metadata", {}).get("package_type")
            offer_id = session.get("metadata", {}).get("offer_id")

            if user_slug and gig_slug and package_type:
                user = get_object_or_404(User, slug=user_slug)
                gig = get_object_or_404(Gig, slug=gig_slug)

                price = (
                    gig.basic_price if package_type == "basic" else
                    gig.standard_price if package_type == "standard" else
                    gig.premium_price
                )
                delivery = gig.basic_delivery_time if package_type == "basic" else gig.standard_delivery_time if package_type == "standard" else gig.premium_delivery_time
                order = Order.objects.create(user=user, gig=gig, package_type=package_type, price=price, is_paid=True, delivery_days=delivery)

                Notification.objects.create(
                    user=gig.user,
                    app_name="workprenair",
                    message=f"You have received a new order from {user.username}. The order is awaiting requirements submission."
                )

                buyer_url = request.build_absolute_uri(reverse("order_detail", args=[order.slug]))
                
                # Send Email to Buyer
                buyer_email_content = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
                        <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                            <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                                <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                            </div>
                            <div style="padding: 20px;">
                                <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🛒 Order Confirmed! Your Purchase #{order.id} is Ready</h2>
                                <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {user.username},</p>
                                <p style="color: #333; font-size: 16px; line-height: 1.6;">Thank you for your purchase on <strong>FirePrenair</strong>! 🎉 Your order has been successfully processed.</p>
                                <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Important:</strong> To activate your order, please submit the required details at the earliest.</p>
                                <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Order Details:</strong></p>
                                <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                                    <li style="margin-bottom: 10px;"><strong>Order ID:</strong> {order.id}</li>
                                    <li style="margin-bottom: 10px;"><strong>Product/Service:</strong> {gig.title}</li>
                                    <li style="margin-bottom: 10px;"><strong>Total Amount:</strong> ${order.price}</li>
                                </ul>
                                <p style="color: #333; font-size: 16px; line-height: 1.6;">Click below to submit your requirements and activate your order:</p>
                                <p style="text-align: center; margin: 20px 0;">
                                    <a href="{buyer_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">Submit Requirements</a>
                                </p>
                                <p style="color: #333; font-size: 16px; line-height: 1.6;">Need help? Our support team is always here for you.</p>
                            </div>
                            <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                                <p style="margin: 0; font-size: 14px;">Thank you for choosing FirePrenair! 🚀</p>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                send_email(user.email, f"🛒 Order Confirmed! Your Order #{order.id} is Awaiting your requirements!", buyer_email_content)

                manage_orders_url = request.build_absolute_uri(reverse('sellor_dashboard'))
                # Send Email to Seller
                seller_email_content = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
                        <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                            <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                                <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                            </div>
                            <div style="padding: 20px;">
                                <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🎉 New Order Received! #{order.id}</h2>
                                <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {gig.user.username},</p>
                                <p style="color: #333; font-size: 16px; line-height: 1.6;">Great news! You’ve received a new order for your service on <strong>FirePrenair</strong>.</p>
                                <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Important:</strong> This order is awaiting the buyer's requirements. Please be ready to start as soon as they are submitted.</p>
                                <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Order Details:</strong></p>
                                <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                                    <li style="margin-bottom: 10px;"><strong>Order ID:</strong> {order.id}</li>
                                    <li style="margin-bottom: 10px;"><strong>Buyer:</strong> {user.username}</li>
                                    <li style="margin-bottom: 10px;"><strong>Product/Service:</strong> {gig.title}</li>
                                    <li style="margin-bottom: 10px;"><strong>Amount:</strong> ${order.price}</li>
                                </ul>
                                <p style="text-align: center; margin: 20px 0;">
                                    <a href="{manage_orders_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">📂 Manage My Orders</a>
                                </p>
                            </div>
                            <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                                <p style="margin: 0; font-size: 14px;">Let’s keep delivering excellence!</p>
                                <p style="margin: 0; font-size: 14px;">The FirePrenair Team</p>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                send_email(gig.user.email, f"🎉 New Order Received! #{order.id}", seller_email_content)

            elif user_slug and offer_id:
                user = get_object_or_404(User, slug=user_slug)
                offer = get_object_or_404(CustomOffer, id=offer_id, recipient=user)

                offer.is_accepted = True
                offer.save()

                order = Order.objects.create(
                    user=user,
                    gig=offer.gig,
                    package_type="custom_offer",
                    price=offer.price,
                    is_paid=True,
                    delivery_days=offer.delivery_time
                )
                Notification.objects.create(
                    user=offer.sender,
                    app_name="workprenair",
                    message=f"You have received a new order from {user.username}. The order is awaiting requirements submission."
                )

                buyer_url = request.build_absolute_uri(reverse("order_detail", args=[order.slug]))
                
                # Send Email to Buyer
                buyer_email_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
                    <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                        <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                            <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                        </div>
                        <div style="padding: 20px;">
                            <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🛒 Order Confirmed! Your Purchase #{order.id} is Ready</h2>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {user.username},</p>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">
                                Thank you for your purchase on <strong>FirePrenair</strong>! 🎉 Your order has been successfully processed.
                            </p>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">
                                <strong>Important:</strong> To activate your order, please submit the required details at the earliest.
                            </p>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Order Details:</strong></p>
                            <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                                <li style="margin-bottom: 10px;"><strong>Order ID:</strong> {order.id}</li>
                                <li style="margin-bottom: 10px;"><strong>Product/Service:</strong> {offer.gig.title}</li>
                                <li style="margin-bottom: 10px;"><strong>Total Amount:</strong> ${order.price}</li>
                            </ul>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">Click below to submit your requirements and activate your order:</p>
                            <p style="text-align: center; margin: 20px 0;">
                                <a href="{buyer_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">Submit Requirements</a>
                            </p>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">Need help? Our support team is always here for you.</p>
                        </div>
                        <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                            <p style="margin: 0; font-size: 14px;">Thank you for choosing FirePrenair! 🚀</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                send_email(request.user.email, f"🛒 Order Confirmed! Your Order #{order.id} is Awaiting your requirements!", buyer_email_content)

                manage_orders_url = request.build_absolute_uri(reverse('sellor_dashboard'))
                # Send Email to Seller
                seller_email_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
                    <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                        <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                            <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                        </div>
                        <div style="padding: 20px;">
                            <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🎉 New Order Received! #{order.id}</h2>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {offer.gig.user.username},</p>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">Great news! You’ve received a new order for your service on <strong>FirePrenair</strong>.</p>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Important:</strong> This order is awaiting the buyer's requirements. Please be ready to start as soon as they are submitted.</p>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Order Details:</strong></p>
                            <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                                <li style="margin-bottom: 10px;"><strong>Order ID:</strong> {order.id}</li>
                                <li style="margin-bottom: 10px;"><strong>Buyer:</strong> {offer.recipient.username}</li>
                                <li style="margin-bottom: 10px;"><strong>Product/Service:</strong> {offer.gig.title}</li>
                                <li style="margin-bottom: 10px;"><strong>Amount:</strong> ${order.price}</li>
                            </ul>
                            <p style="text-align: center; margin: 20px 0;">
                                <a href="{manage_orders_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">📂 Manage My Orders</a>
                            </p>
                        </div>
                        <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                            <p style="margin: 0; font-size: 14px;">Let’s keep delivering excellence!</p>
                            <p style="margin: 0; font-size: 14px;">The FirePrenair Team</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                send_email(offer.gig.user.email, f"🎉 New Order Received! #{order.id}", seller_email_content)

        return Response(status=status.HTTP_200_OK)
    


# ------------------- PayPal Checkouts -------------------
import paypalrestsdk

# Configure PayPal SDK
paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})

@api_view(['POST'])
def paypal_checkout_api(request, gig_slug, package_type):
    user = request.user
    gig = get_object_or_404(Gig, slug=gig_slug)

    # Determine the price based on package type
    if package_type == "basic":
        price = gig.basic_price + (gig.basic_price * Decimal('0.05'))
    elif package_type == "standard":
        price = gig.standard_price + (gig.standard_price * Decimal('0.05'))
    elif package_type == "premium":
        price = gig.premium_price + (gig.premium_price * Decimal('0.05'))
    else:
        return Response({"error": "Invalid package type selected."}, status=status.HTTP_400_BAD_REQUEST)

    # PayPal payment creation
    success_url = request.build_absolute_uri(reverse("paypal_success"))
    cancel_url = request.build_absolute_uri(reverse("paypal_cancel"))

    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"
        },
        "redirect_urls": {
            "return_url": success_url,
            "cancel_url": cancel_url
        },
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": f"{gig.title} - {package_type.capitalize()}",
                    "sku": f"{gig.slug}%{package_type}",
                    "price": f"{price:.2f}",
                    "currency": "USD",
                    "quantity": 1
                }]
            },
            "amount": {
                "total": f"{price:.2f}",
                "currency": "USD"
            },
            "description": f"Purchase {gig.title} - {package_type.capitalize()} Package"
        }]
    })

    if payment.create():
        # Redirect user to PayPal for approval
        approval_url = next((link.href for link in payment.links if link.rel == "approval_url"), None)
        if approval_url:
            return Response({"approval_url": approval_url}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Approval URL not found in PayPal response."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response({"error": "Failed to create PayPal payment."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PayPalSuccessAPIView(APIView):

    def get(self, request):
        payment_id = request.GET.get("paymentId")
        payer_id = request.GET.get("PayerID")

        # Validate if paymentId and payerId are present
        if not payment_id or not payer_id:
            return Response({"error": "Invalid PayPal payment details."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the payment object
        payment = Payment.find(payment_id)

        # Attempt to execute the payment
        if payment.execute({"payer_id": payer_id}):
            transactions = payment.transactions[0]
            item = transactions.item_list["items"][0]
            gig_slug = item["sku"].split("%")[0]
            package_type = item["sku"].split("%")[1]

            gig = get_object_or_404(Gig, slug=gig_slug)
            price = Decimal(item["price"])
            delivery_date = (
                gig.basic_delivery_time if package_type == "basic" else
                gig.standard_delivery_time if package_type == "standard" else
                gig.premium_delivery_time
            )

            # Create the order
            order = Order.objects.create(
                user=request.user,
                gig=gig,
                package_type=package_type,
                price=price,
                is_paid=True,
                delivery_days=delivery_date
            )

            # Send notification to seller
            Notification.objects.create(
                user=gig.user,
                app_name="workprenair",
                message=f"You have received a new order from {request.user.username}. Let's Wait for client's Requirements"
            )

            # Prepare URLs for the buyer and seller
            buyer_url = request.build_absolute_uri(reverse("order_detail", args=[order.slug]))
            manage_orders_url = request.build_absolute_uri(reverse('sellor_dashboard'))

            # Send email to the buyer
            buyer_email_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
                    <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                        <!-- Header -->
                        <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                            <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                        </div>

                        <!-- Body -->
                        <div style="padding: 20px;">
                            <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🛒 Order Confirmed! Your Purchase #{order.id} is Ready</h2>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {request.user.username},</p>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">
                                Thank you for your purchase on <strong>FirePrenair</strong>! 🎉 Your order has been successfully processed.
                            </p>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">
                                <strong>Important:</strong> To activate your order, please submit the required details at the earliest.
                            </p>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Order Details:</strong></p>
                            <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                                <li style="margin-bottom: 10px;"><strong>Order ID:</strong> {order.id}</li>
                                <li style="margin-bottom: 10px;"><strong>Product/Service:</strong> {gig.title}</li>
                                <li style="margin-bottom: 10px;"><strong>Total Amount:</strong> ${order.price}</li>
                            </ul>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">Click below to submit your requirements and activate your order:</p>
                            <p style="text-align: center; margin: 20px 0;">
                                <a href="{buyer_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">Submit Requirements</a>
                            </p>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">Need help? Our support team is always here for you.</p>
                        </div>

                        <!-- Footer -->
                        <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                            <p style="margin: 0; font-size: 14px;">Thank you for choosing FirePrenair! 🚀</p>
                        </div>
                    </div>
                </body>
                </html>
                """

            send_mail(
                subject=f"🛒 Order Confirmed! Your Order #{order.id} is Awaiting your requirements!",
                message=buyer_email_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
                html_message=buyer_email_content
            )

            # Send email to the seller
            seller_email_content = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
                        <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                            <!-- Header -->
                            <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                                <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                            </div>

                            <!-- Body -->
                            <div style="padding: 20px;">
                                <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🎉 New Order Received! #{order.id}</h2>
                                <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {gig.user.username},</p>
                                <p style="color: #333; font-size: 16px; line-height: 1.6;">
                                    Great news! You’ve received a new order for your service on <strong>FirePrenair</strong>.
                                </p>
                                <p style="color: #333; font-size: 16px; line-height: 1.6;">
                                    <strong>Important:</strong> This order is awaiting the buyer's requirements. Please be ready to start as soon as they are submitted.
                                </p>
                                <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Order Details:</strong></p>
                                <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                                    <li style="margin-bottom: 10px;"><strong>Order ID:</strong> {order.id}</li>
                                    <li style="margin-bottom: 10px;"><strong>Buyer:</strong> {request.user.username}</li>
                                    <li style="margin-bottom: 10px;"><strong>Product/Service:</strong> {gig.title}</li>
                                    <li style="margin-bottom: 10px;"><strong>Amount:</strong> ${order.price}</li>
                                </ul>
                                <p style="text-align: center; margin: 20px 0;">
                                    <a href="{manage_orders_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">📂 Manage My Orders</a>
                                </p>
                            </div>

                            <!-- Footer -->
                            <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                                <p style="margin: 0; font-size: 14px;">Let’s keep delivering excellence!</p>
                                <p style="margin: 0; font-size: 14px;">The FirePrenair Team</p>
                            </div>
                        </div>
                    </body>
                    </html>
                    """

            send_mail(
                subject=f"🎉 New Order Received! #{order.id}",
                message=seller_email_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[gig.user.email],
                html_message=seller_email_content
            )

            # Send success response
            return Response({
                "message": "Order placed successfully, Submit your requirements to activate the order."
            }, status=status.HTTP_201_CREATED)

        else:
            return Response({"error": "PayPal payment execution failed."}, status=status.HTTP_400_BAD_REQUEST)

class CustomOfferPayPalCheckoutAPIView(APIView):

    def post(self, request, offer_id):
        user = request.user
        offer = get_object_or_404(CustomOffer, id=offer_id, recipient=user)

        # Check if the offer has already been accepted and paid for
        if offer.is_accepted:
            return Response({"error": "This offer has already been paid for."}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate the price with the 5% fee
        price = offer.price + (offer.price * Decimal('0.05'))
        success_url = request.build_absolute_uri(reverse("custom_offer_paypal_success"))
        cancel_url = request.build_absolute_uri(reverse("paypal_cancel"))

        # Set up the PayPal payment object
        payment = Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": success_url,
                "cancel_url": cancel_url
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": f"Custom Offer - {offer.description[:50]}",
                        "sku": f"{offer.id}",
                        "price": f"{price:.2f}",
                        "currency": "USD",
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": f"{price:.2f}",
                    "currency": "USD"
                },
                "description": f"Payment for Custom Offer - {offer.description[:50]}"
            }]
        })

        # Create the payment through PayPal SDK
        if payment.create():
            approval_url = next((link.href for link in payment.links if link.rel == "approval_url"), None)
            if approval_url:
                return Response({"approval_url": approval_url}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "No approval URL found in PayPal response."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({"error": "Failed to create PayPal payment."}, status=status.HTTP_400_BAD_REQUEST)




@api_view(['GET'])
def custom_offer_paypal_success_api(request):
    payment_id = request.GET.get("paymentId")
    payer_id = request.GET.get("PayerID")

    if not payment_id or not payer_id:
        return Response({"error": "Invalid PayPal payment details."}, status=status.HTTP_400_BAD_REQUEST)

    payment = paypalrestsdk.Payment.find(payment_id)
    if payment.execute({"payer_id": payer_id}):
        transaction = payment.transactions[0]
        item = transaction.item_list["items"][0]
        offer_id = item["sku"]

        offer = get_object_or_404(CustomOffer, id=offer_id, recipient=request.user)

        offer.is_accepted = True
        offer.save()

        order = Order.objects.create(
            user=request.user,
            gig=offer.gig,
            package_type="custom_offer",
            price=offer.price,
            is_paid=True,
            delivery_days=offer.delivery_time
        )

        Notification.objects.create(
            user=offer.sender,
            app_name="workprenair",
            message=f"You have received a new order from {request.user.username}. Let's wait for the client's requirements."
        )

        buyer_url = request.build_absolute_uri(reverse("order_detail", args=[order.slug]))
        # Send Email to Buyer
        buyer_email_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
                <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                    <!-- Header -->
                    <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                        <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                    </div>
                    <!-- Body -->
                    <div style="padding: 20px;">
                        <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🛒 Order Confirmed! Your Purchase #{order.id} is Ready</h2>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {request.user.username},</p>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">
                            Thank you for your purchase on <strong>FirePrenair</strong>! 🎉 Your order has been successfully processed.
                        </p>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">
                            <strong>Important:</strong> To activate your order, please submit the required details at the earliest.
                        </p>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Order Details:</strong></p>
                        <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                            <li style="margin-bottom: 10px;"><strong>Order ID:</strong> {order.id}</li>
                            <li style="margin-bottom: 10px;"><strong>Product/Service:</strong> {offer.gig.title}</li>
                            <li style="margin-bottom: 10px;"><strong>Total Amount:</strong> ${order.price}</li>
                        </ul>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">Click below to submit your requirements and activate your order:</p>
                        <p style="text-align: center; margin: 20px 0;">
                            <a href="{buyer_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">Submit Requirements</a>
                        </p>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">Need help? Our support team is always here for you.</p>
                    </div>
                    <!-- Footer -->
                    <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                        <p style="margin: 0; font-size: 14px;">Thank you for choosing FirePrenair! 🚀</p>
                    </div>
                </div>
            </body>
            </html>
        """
        send_email(request.user.email, f"🛒 Order Confirmed! Your Order #{order.id} is Awaiting your requirements!", buyer_email_content)

        manage_orders_url = request.build_absolute_uri(reverse('sellor_dashboard'))
        # Send Email to Seller
        seller_email_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
                <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                    <!-- Header -->
                    <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                        <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                    </div>
                    <!-- Body -->
                    <div style="padding: 20px;">
                        <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🎉 New Order Received! #{order.id}</h2>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {offer.gig.user.username},</p>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">
                            Great news! You’ve received a new order for your service on <strong>FirePrenair</strong>.
                        </p>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">
                            <strong>Important:</strong> This order is awaiting the buyer's requirements. Please be ready to start as soon as they are submitted.
                        </p>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Order Details:</strong></p>
                        <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                            <li style="margin-bottom: 10px;"><strong>Order ID:</strong> {order.id}</li>
                            <li style="margin-bottom: 10px;"><strong>Buyer:</strong> {request.user.username}</li>
                            <li style="margin-bottom: 10px;"><strong>Product/Service:</strong> {offer.gig.title}</li>
                            <li style="margin-bottom: 10px;"><strong>Amount:</strong> ${order.price}</li>
                        </ul>
                        <p style="text-align: center; margin: 20px 0;">
                            <a href="{manage_orders_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">📂 Manage My Orders</a>
                        </p>
                    </div>
                    <!-- Footer -->
                    <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                        <p style="margin: 0; font-size: 14px;">Let’s keep delivering excellence!</p>
                        <p style="margin: 0; font-size: 14px;">The FirePrenair Team</p>
                    </div>
                </div>
            </body>
            </html>
        """
        send_email(offer.gig.user.email, f"🎉 New Order Received! #{order.id}", seller_email_content)

        return Response({
            "message": "Payment successful. Order placed successfully, Submit your requirements to start the order."
        }, status=status.HTTP_200_OK)
    else:
        return Response({"error": "PayPal payment execution failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def paypal_cancel_api(request):
    return Response({"error": "Payment canceled by the user.redirect t errros page"}, status=status.HTTP_400_BAD_REQUEST)



# --------------  Custom Offers ---------------------------
class CustomOffersListAPIView(APIView):

    def get(self, request):
        user = request.user
        custom_offers_sent = None
        custom_offers_received = None

        # Check if the user is a freelancer and retrieve sent offers, else retrieve received offers
        if user.is_work_freelancer:
            custom_offers_sent = CustomOffer.objects.filter(sender=user)
        else:
            custom_offers_received = CustomOffer.objects.filter(recipient=user, is_declined=False)

        # Serialize the custom offers (sending only necessary fields for the API)
        sent_offers = [{
            "id": offer.id,
            "sender": offer.sender.username,
            "recipient": offer.recipient.username,
            "description": offer.description,
            "price": str(offer.price),
            "created_at": offer.created_at,
            "is_accepted": offer.is_accepted
        } for offer in custom_offers_sent] if custom_offers_sent else []

        received_offers = [{
            "id": offer.id,
            "sender": offer.sender.username,
            "recipient": offer.recipient.username,
            "description": offer.description,
            "price": str(offer.price),
            "created_at": offer.created_at,
            "is_accepted": offer.is_accepted
        } for offer in custom_offers_received] if custom_offers_received else []

        return Response({
            "custom_offers_sent": sent_offers,
            "custom_offers_received": received_offers
        }, status=status.HTTP_200_OK)

@api_view(['POST'])
def create_offer_api(request):
    if not request.user.is_work_freelancer:
        return JsonResponse({"message": "You must be a freelancer to send offers."}, status=400)

    if request.method == "POST":
        gig_slug = request.POST.get('gig')
        recipient_slug = request.POST.get('recipient')
        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        delivery_time = request.POST.get('delivery_time')

        # Get the gig and recipient objects
        gig = get_object_or_404(Gig, slug=gig_slug, user=request.user)
        recipient = get_object_or_404(User, username=recipient_slug)

        # Create the custom offer
        custom_offer = CustomOffer.objects.create(
            gig=gig,
            sender=request.user,
            recipient=recipient,
            title=title,
            description=description,
            price=price,
            delivery_time=delivery_time,
        )

        # Create the notification
        Notification.objects.create(user=recipient, app_name="workprenair", message=f"New offer received from {request.user.username}.")

        # Build the URL for custom offers list
        custom_offers_url = request.build_absolute_uri(reverse('custom_offers_list'))

        # Email Content for the recipient
        offer_email_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
            <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                <!-- Header -->
                <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                    <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                </div>

                <!-- Body -->
                <div style="padding: 20px;">
                    <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🎉 You’ve Received a New Offer!</h2>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {recipient.username},</p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                        Great news! <strong>{request.user.username}</strong> has sent you a custom offer for their service on <strong>FirePrenair</strong>.
                    </p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Offer Details:</strong></p>
                    <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                        <li style="margin-bottom: 10px;"><strong>Title:</strong> {title}</li>
                        <li style="margin-bottom: 10px;"><strong>Price:</strong> ${price}</li>
                        <li style="margin-bottom: 10px;"><strong>Delivery Time:</strong> {delivery_time} days</li>
                    </ul>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                        Review the offer and take action to proceed with the service.
                    </p>
                    <p style="text-align: center; margin: 20px 0;">
                        <a href="{custom_offers_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">📜 View My Offers</a>
                    </p>
                </div>

                <!-- Footer -->
                <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                    <p style="margin: 0; font-size: 14px;">We’re excited to see your next project come to life!</p>
                    <p style="margin: 0; font-size: 14px;">The FirePrenair Team</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send email to recipient
        send_mail(
            f"🎉 New Offer Received from {request.user.username}",
            offer_email_content,
            'from@example.com',  # Replace with the actual sender email
            [recipient.email],
            fail_silently=False,
            html_message=offer_email_content
        )

        # Return a JSON response with the offer data
        return JsonResponse({
            "message": "Offer sent successfully.",
            "offer": {
                "title": custom_offer.title,
                "price": custom_offer.price,
                "delivery_time": custom_offer.delivery_time,
                "recipient": recipient.username,
                "sender": request.user.username,
            }
        }, status=201)

    return JsonResponse({"message": "Invalid request method."}, status=400)



@api_view(['POST'])
def decline_offer_api(request, offer_id):
    try:
        offer = get_object_or_404(CustomOffer, id=offer_id)
    except CustomOffer.DoesNotExist:
        return Response({"message": "Offer not found."}, status=status.HTTP_404_NOT_FOUND)

    # Ensure the user is the recipient of the offer
    if request.user != offer.recipient:
        return Response({"message": "You are not authorized to perform this action."}, status=status.HTTP_403_FORBIDDEN)

    # Decline the offer
    offer.is_declined = True
    offer.save()

    # Create a notification for the sender
    Notification.objects.create(user=offer.sender, app_name="workprenair", message=f"Your offer has been declined by {request.user.username}.")

    # Return a success message with offer details
    return Response({
        "message": "Offer declined successfully.",
        "offer": {
            "id": offer.id,
            "title": offer.title,
            "price": offer.price,
            "delivery_time": offer.delivery_time,
            "recipient": offer.recipient.username,
            "sender": offer.sender.username,
            "is_declined": offer.is_declined
        }
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
def delete_offer_api(request, offer_id):
    offer = get_object_or_404(CustomOffer, id=offer_id)

    # Ensure the user is the sender of the offer
    if request.user != offer.sender:
        return Response({"message": "You are not authorized to perform this action."}, status=status.HTTP_403_FORBIDDEN)

    # Delete the offer
    offer.delete()

    # Return a success message
    return Response({"message": "Offer deleted successfully."}, status=status.HTTP_204_NO_CONTENT)



@api_view(['GET'])
def user_chats_api(request):
    # Get the search query if it exists
    search_query = request.GET.get('search', '') 
    
    # Get the user's chats
    user_chats = request.user.get_work_chats()

    # Apply the search filter if a search query is provided
    if search_query:
        user_chats = user_chats.filter(
            Q(user1__name__icontains=search_query) | Q(user2__name__icontains=search_query)
        )

    chats_with_last_message = []
    
    # Iterate over each chat and gather necessary information
    for user_chat in user_chats:
        time = timezone.now()
        last_message = user_chat.chat_messages.order_by('-timestamp').first()
        unread_count = user_chat.chat_messages.filter(is_read=False, receiver=request.user).count()
        
        if last_message:
            time = last_message.timestamp
        
        chats_with_last_message.append({
            "chat_id": user_chat.id,
            "user1_name": user_chat.user1.name,
            "user2_name": user_chat.user2.name,
            "last_message": last_message.content if last_message else None,
            "last_message_timestamp": time,
            "unread_count": unread_count
        })

    # Return the data in JSON format
    return Response({
        'user_chats': chats_with_last_message,
        'search_query': search_query,
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
def user_chat_api(request, chatSlug):
    try:
        # Check if the user is authenticated
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)

        chat = PrivateChat.objects.filter(slug=chatSlug, commu_prenair_chat=False).first()

        if not chat:
            other_user_slug = request.query_params.get('user_slug')
            other_user = get_object_or_404(User, slug=other_user_slug)

            chat = PrivateChat.objects.filter(
                (Q(user1=request.user, commu_prenair_chat=False) & Q(user2=other_user, commu_prenair_chat=False)) | 
                (Q(user1=other_user, commu_prenair_chat=False) & Q(user2=request.user, commu_prenair_chat=False))
            ).first()

            if not chat:
                unique_uuid = uuid.uuid4()
                slug = slugify(f"{request.user.username}-{other_user.username}-work-{unique_uuid}")
                chat = PrivateChat.objects.create(user1=request.user, user2=other_user, slug=slug, commu_prenair_chat=False)
                Notification.objects.create(user=other_user, app_name="workprenair", message=f"{request.user.username} has Started a Chat on Workprenair!")

            # Return chat slug
            return Response({"chatSlug": chat.slug}, status=status.HTTP_201_CREATED)
        
        # Get chat messages for the chat
        chat_messages = chat.chat_messages.all()
        other_user = chat.user1 if chat.user1 != request.user else chat.user2
        chat.chat_messages.filter(is_read=False, receiver=request.user).update(is_read=True)
        
        # Get all user chats and related information
        user_chats = request.user.get_work_chats()

        chats_with_last_message = []
        for user_chat in user_chats:
            last_message = user_chat.chat_messages.order_by('-timestamp').first()
            unread_count = user_chat.chat_messages.filter(is_read=False, receiver=request.user).count()
            time = timezone.now()
            if last_message:
                time = last_message.timestamp
            chats_with_last_message.append({
                'chat_slug': user_chat.slug,
                'last_message': last_message.content if last_message else None,
                'timestamp': time,
                'unread_count': unread_count
            })

        # Prepare response data
        response_data = {
            'chatSlug': chatSlug,
            'chat_with': {
                'slug': chat.slug,
                'user1': chat.user1.username,
                'user2': chat.user2.username,
                'commu_prenair_chat': chat.commu_prenair_chat,
            },
            'chat_messages': [{
                'content': message.content,
                'timestamp': message.timestamp,
                'sender': message.sender.username,
                'receiver': message.receiver.username,
                'is_read': message.is_read,
            } for message in chat_messages],
            'other_user': {
                'slug': other_user.slug,
                'username': other_user.username
            },
            'user_chats': chats_with_last_message
        }

        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(e)

@api_view(['POST'])
def ai_chat_assist_api(request, chatSlug):
    # Check if the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)

    # Retrieve chat object
    chat = get_object_or_404(PrivateChat, slug=chatSlug)
    
    # Check if the user is part of the chat
    if request.user not in [chat.user1, chat.user2]:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    try:
        # Parse request body
        data = json.loads(request.body)
        context = data.get('context', '')
        recent_messages = data.get('recent_messages', [])

        # Format recent messages
        formatted_messages = []
        for msg in recent_messages:
            if isinstance(msg, dict):
                formatted_messages.append(f"{msg.get('sender_role', 'Unknown')}: {msg.get('content', '')}")
            else:
                formatted_messages.append(str(msg))

        # Determine role (freelancer or client)
        role = "freelancer" if request.user.is_work_freelancer else "client"

        # Create the prompt for OpenAI
        prompt = f"""You're a professional communication assistant helping {role} in a client-freelancer chat.
        Conversation context (most recent first): {context}
        {chr(10).join(formatted_messages)}

        Generate 3 professional response suggestions with these rules:
        1. Suggestions should be from the {role}'s perspective
        2. Maintain appropriate professional tone for business communication
        3. Consider the relationship context (client vs freelancer)
        4. Each suggestion 40-60 words
        5. Numbered list without markdown

        Example for freelancer:
        1. I'll have the initial draft ready by Friday. Would you prefer to schedule a review session?
        2. Could you clarify the target audience for this feature? That will help me prioritize the implementation.
        3. Let's discuss the timeline adjustments. I can offer 2 options that might work with your schedule.

        Example for client:
        1. The design looks good overall. Could we make the primary buttons more prominent?
        2. Let me check with stakeholders about the budget increase. I'll have an answer by tomorrow.
        3. Would you be available for a quick call Wednesday afternoon to go over the revisions?"""

        # Call OpenAI API (assuming you have OpenAI client set up)
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200
        )
        
        # Parse the response
        raw_output = response.choices[0].message['content'].strip()
        suggestions = []

        for line in raw_output.split('\n'):
            cleaned = re.sub(r'^\d+\.\s*', '', line).strip()
            if cleaned and len(cleaned) > 10:  # Avoid empty lines or very short suggestions
                suggestions.append(cleaned)

        # Return the suggestions
        return Response({
            'suggestions': suggestions[:3]  # Return only top 3 suggestions
        }, status=status.HTTP_200_OK)

    except Exception as e:
        # Return error response if anything goes wrong
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ------------------- Categories -------------------
# Get top-level categories

@api_view(['GET'])
def get_top_categories_api(request):
    try:
        top_categories = WorkCategory.objects.filter(parent__isnull=True)
        serializer = WorkCategorySerializer(top_categories, many=True)
        return Response({'categories': serializer.data}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_work_subcategories_api(request, category_id):
    try:
        level_2_categories = WorkCategory.objects.filter(parent_id=category_id)
        serializer = SubcategorySerializer(level_2_categories, many=True)
        return Response({'level_2_categories': serializer.data}, status=status.HTTP_200_OK)
    except WorkCategory.DoesNotExist:
        return Response({'error': 'Category not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'errorr': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET', 'POST'])
def become_seller_api(request):
    """Apply to sell on WorkPrenair, mirroring `work_prenair.views.become_seller`.

    A GET answers "where should Become Seller take me?". The website decides
    that server-side: an approved seller is bounced to their dashboard, anyone
    else gets the application form pre-filled from their account. Only POST
    existed here, so a client had to guess — which is why the app's button went
    to the dashboard for everyone, approved or not.

    Note the two separate flags. `is_work_profile_approved` says the user *may*
    sell; `is_work_freelancer` says they are *currently* acting as a seller.
    Switching between buyer and seller only flips the second, and that is what
    `toggle_profile_api` does.
    """
    if not request.user.is_authenticated:
        return Response({"error": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == 'GET':
        user = request.user
        return Response(
            {
                "is_approved": user.is_work_profile_approved,
                "is_freelancer": user.is_work_freelancer,
                "prefill": {
                    "name": user.name or "",
                    "phone": user.phone_no or "",
                    "country": user.country or "",
                    "about": user.work_bio or "",
                    "portfolio": user.portfolio_link or "",
                    "expertise": user.work_expertise or "",
                },
            },
            status=status.HTTP_200_OK,
        )

    # Check if the user is already a seller
    if request.user.is_work_profile_approved:
        return Response({"warning": "You are already a seller on Workprenair."}, status=status.HTTP_400_BAD_REQUEST)

    # Get data from the request
    name = request.data.get('name')
    phone_no = request.data.get('phone')
    country = request.data.get('country')
    bio = request.data.get('about')
    portfolio_link = request.data.get('portfolio')
    expertise = request.data.get('expertise')

    # Check if all required fields are provided
    if not all([name, phone_no, country, bio, expertise]):
        return Response({"error": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)

    # Update user details
    request.user.name = name
    request.user.phone_no = phone_no
    request.user.country = country
    request.user.work_bio = bio
    request.user.work_expertise = expertise
    request.user.portfolio_link = portfolio_link
    request.user.is_work_profile_approved = True
    request.user.is_work_freelancer = True
    request.user.save()

    # Return success response
    return Response({"message": "You are now a seller on Workprenair."}, status=status.HTTP_200_OK)


@api_view(['POST'])
def toggle_profile_api(request):
    """
    API endpoint to toggle between Workprenair Buyer and Seller profile for the logged-in user.
    """
    # Check if the user is authenticated
    if not request.user.is_authenticated:
        return Response({"error": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)

    # If the user is already a freelancer (Seller), toggle to Buyer
    if request.user.is_work_freelancer:
        request.user.is_work_freelancer = False
        request.user.save()
        return Response({"message": "Switched to Workprenair Buyer"}, status=status.HTTP_200_OK)

    # If the user is not a freelancer, check if their profile is approved for a seller
    if request.user.is_work_profile_approved:
        request.user.is_work_freelancer = True
        request.user.save()
        return Response({"message": "Switched to Workprenair Seller"}, status=status.HTTP_200_OK)
    
    # If the user's profile is not approved for a seller, send an error message
    return Response({"error": "Your seller profile is not approved. Please approve it."}, status=status.HTTP_400_BAD_REQUEST)





# response = client.images.generate(
#     model="dall-e-3",
#     prompt="a white siamese cat",
#     size="1024x1024",
#     quality="standard",
#     n=1,
# )

# print(response.data[0].url)
#












