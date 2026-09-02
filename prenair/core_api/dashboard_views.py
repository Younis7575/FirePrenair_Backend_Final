from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.decorators import login_required
from dashboard.models import WithdrawalRequest
from profiles.models import Notification
from dashboard.decorators import admin_not_allowed

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
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import *
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view  # <-- Add this import
from rest_framework.decorators import permission_classes  # Import permission_classes decorator
from django.db.models import Q
import os
from django.db.models import Sum
from django.db.models.functions import ExtractMonth


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@admin_not_allowed
def dashboard_home_api(request):
    user = request.user
    completion_percentage = user.profile_completion_percentage()
    missing_fields = user.missing_profile_fields()
    
    all_fields = ['name', 'bio', 'profile_pic', 'phone_no', 'age', 'country']
    
    withdraw_requests = WithdrawalRequest.objects.filter(user=user).order_by(
        "-created_at"
    )
    
    data = {
        "user": {
            "username": user.username,
            "email": user.email,
            # Add other user fields as needed
        },
        "withdraw_requests": [
            {
                "id": request.id,
                "amount": request.amount,
                "status": request.status,
                "created_at": request.created_at,
                # Add other withdraw request fields as needed
            } for request in withdraw_requests
        ],
        "completion_percentage": completion_percentage,
        "missing_fields": missing_fields,
        "all_fields": all_fields,
    }
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_notifications_api(request):
    user = request.user
    notifications = Notification.objects.filter(user=user).order_by("-created_at")
    
    work_notifications = notifications.filter(app_name="workprenair")
    digi_notifications = notifications.filter(app_name="digiprenair")
    edu_notifications = notifications.filter(app_name="eduprenair")
    commu_notifications = notifications.filter(app_name="commuprenair")
    
    # Helper function to serialize notification objects
    def serialize_notifications(notifications_queryset):
        return [
            {
                "id": notification.id,
                "message": notification.message,
                "is_read": notification.is_read,
                "created_at": notification.created_at,
                # Add other notification fields as needed
            } for notification in notifications_queryset
        ]
    
    data = {
        "work_notifications": serialize_notifications(work_notifications),
        "digi_notifications": serialize_notifications(digi_notifications),
        "edu_notifications": serialize_notifications(edu_notifications),
        "commu_notifications": serialize_notifications(commu_notifications),
    }
    
    return Response(data, status=status.HTTP_200_OK)



from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from dashboard.decorators import admin_not_allowed
from digi_prenair.models import *
from commu_prenair.models import *
from dashboard.models import *
from edu_prenair.models import *
from work_prenair.models import *
from .serializers import ProductSerializer, NotificationSerializer
import calendar

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@admin_not_allowed
def dashboard_digiprenair_api(request):
    user = request.user
    digi_total_reviews = Review.objects.filter(product__seller=user).count()
    digi_total_items = user.digi_total_items
    total_earnings = user.digi_total_earnings
    total_sales = user.digi_total_sales
    recent_sales = OrderItem.objects.filter(product__seller=user).order_by(
        "-order__created_at"
    )[:10]

    # Total sales per month
    monthly_sales = (
        OrderItem.objects.filter(product__seller=user)
        .annotate(month=ExtractMonth("order__created_at"))
        .values("month")
        .annotate(total_sales=Sum("product__price"))
        .order_by("month")
    )

    # Prepare data for the chart
    sales_data = [0] * 12  # Default array for all months (Jan to Dec)
    for entry in monthly_sales:
        month_index = entry["month"] - 1  # Convert to 0-based index
        sales_data[month_index] = float(
            entry["total_sales"] or 0
        )  # Convert Decimal to float

    chart_data = {
        "sales": sales_data,
        "labels": [calendar.month_name[i] for i in range(1, 13)],  # Jan to Dec
    }

    orders = Order.objects.filter(user=user, is_paid=True)
    
    # notifications
    # Fetch unread notifications for the user
    unread_notifications = Notification.objects.filter(
        user=user, is_read=False, app_name="digiprenair"
    )

    # Mark unread notifications as read
    unread_notifications.update(is_read=True)

    # Fetch all notifications (including the ones just marked as read)
    notifications = Notification.objects.filter(
        user=user, app_name="digiprenair"
    ).order_by("-created_at")[:5]
    
    # Serialize the data
    data = {
        "user": {
            "id": user.id,
            "username": user.username,
            # Add other user fields as needed
        },
        "digi_total_items": digi_total_items,
        "digi_total_reviews": digi_total_reviews,
        "total_earnings": float(total_earnings) if total_earnings else 0,
        "total_sales": total_sales,
        "recent_sales": [
            {
                "id": sale.id,
                "product_name": sale.product.name,
                "price": float(sale.product.price),
                "order_date": sale.order.created_at,
                # Add other fields as needed
            } for sale in recent_sales
        ],
        "orders": [
            {
                "id": order.id,
                "total": float(order.total),
                "created_at": order.created_at,
                # Add other fields as needed
            } for order in orders
        ],
        "chart_data": chart_data,
        "notifications": [
            {
                "id": notification.id,
                "message": notification.message,
                "is_read": notification.is_read,
                "created_at": notification.created_at,
                # Add other notification fields as needed
            } for notification in notifications
        ],
    }
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@admin_not_allowed
def get_child_categories_digi_api(request):
    parent_id = request.query_params.get("parent_id")
    if parent_id:
        categories = Category.objects.filter(parent_id=parent_id)
    else:
        categories = Category.objects.none()

    category_data = [{"id": cat.id, "name": cat.name} for cat in categories]
    return Response({"categories": category_data}, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@admin_not_allowed
def upload_item_digiprenair_api(request):
    user = request.user

    # Check if the user is a seller
    if not user.is_digi_seller:
        return Response(
            {"error": "You are not a seller. Access denied."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    if request.method == "GET":
        categories = Category.objects.filter(parent=None)
        category_data = [{"id": cat.id, "name": cat.name} for cat in categories]
        return Response({"categories": category_data}, status=status.HTTP_200_OK)
    
    elif request.method == "POST":
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(seller=user)  # Associate product with the logged-in seller
            return Response(
                {"message": "Product uploaded successfully!", "product": serializer.data}, 
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@admin_not_allowed
def manage_item_digiprenair_api(request):
    user = request.user

    if not user.is_digi_seller:
        return Response(
            {"error": "You are not a seller. Access denied."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    products = Product.objects.filter(seller=user)
    serializer = ProductSerializer(products, many=True)
    return Response({"products": serializer.data}, status=status.HTTP_200_OK)


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@admin_not_allowed
def edit_item_digiprenair_api(request, slug):
    user = request.user

    if not user.is_digi_seller:
        return Response(
            {"error": "You are not a seller. Access denied."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    product = get_object_or_404(Product, slug=slug)
    
    # Check if the product belongs to the user
    if product.seller != user:
        return Response(
            {"error": "You can only edit your own products."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    if request.method == "GET":
        serializer = ProductSerializer(product)
        categories = Category.objects.filter(parent=None)
        category_data = [{"id": cat.id, "name": cat.name} for cat in categories]
        
        # Prepare category data for the frontend
        category_info = {
            "categories": category_data,
            "selected_category_l_1": product.category.id if product.category else None,
            "selected_category_l_2": product.category_l_2.id if product.category_l_2 else None,
            "selected_category_l_3": product.category_l_3.id if product.category_l_3 else None,
        }
        
        return Response({
            "product": serializer.data,
            "category_info": category_info
        }, status=status.HTTP_200_OK)
    
    elif request.method in ["PUT", "PATCH"]:
        serializer = ProductSerializer(product, data=request.data, partial=request.method=="PATCH")
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Product updated successfully!",
                "product": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@admin_not_allowed
def delete_notification_api(request, notification_id):
    # Get the notification or return 404 if not found
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )

    # Delete the notification
    notification.delete()

    return Response({"message": "Notification deleted successfully"}, status=status.HTTP_204_NO_CONTENT)




from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.conf import settings

import requests
import time


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@admin_not_allowed
def image_generation_api(request):
    user = request.user
    
    if request.method == "GET":
        return Response({
            "user": {
                "username": user.username,
                "id": user.id
            }
        }, status=status.HTTP_200_OK)
    
    elif request.method == "POST":
        prompt = request.data.get("prompt")
        if not prompt:
            return Response({"error": "Prompt is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {settings.LEONARDO_API_KEY}"
        }
        
        # Step 1: Create generation job
        payload = {
            "alchemy": True,
            "height": 768,
            "modelId": "6b645e3a-d64f-4341-a6d8-7a3690fbf042",
            "num_images": 1, 
            "presetStyle": "DYNAMIC",
            "prompt": prompt,
            "width": 1024
        }
        
        post_response = requests.post(
            "https://cloud.leonardo.ai/api/rest/v1/generations",
            json=payload,
            headers=headers
        )
        
        if not post_response.ok:
            return Response(
                {"error": "Failed to create generation job"},
                status=post_response.status_code
            )
        
        try:
            generation_id = post_response.json()["sdGenerationJob"]["generationId"]
        except KeyError:
            return Response({"error": "Invalid API response"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        get_url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
        image_urls = []
        
        max_retries = 10
        retry_delay = 3  # seconds
        
        for _ in range(max_retries):
            get_response = requests.get(get_url, headers=headers)
            
            if get_response.ok:
                try:
                    generation_data = get_response.json()["generations_by_pk"]
                    status_code = generation_data["status"]
                    
                    if status_code == "COMPLETE":
                        images = generation_data.get("generated_images", [])
                        image_urls = [img["url"] for img in images if img.get("url")]
                        break
                    elif status_code in ["PENDING", "PROCESSING"]:
                        time.sleep(retry_delay)
                    else:
                        return Response(
                            {"error": f"Generation failed: {status_code}"}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
                except KeyError:
                    return Response(
                        {"error": "Invalid API response format"}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:
                time.sleep(retry_delay)
        
        if image_urls:
            # Return first image URL to maintain original response format
            return Response({"image_url": image_urls[0]}, status=status.HTTP_200_OK)
        
        return Response(
            {"error": "Image generation timed out"}, 
            status=status.HTTP_504_GATEWAY_TIMEOUT
        )


# EduPrenair API Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@admin_not_allowed
def dashboard_eduprenair_api(request):
    user = request.user

    listed_courses = (
        user.course_set.filter(is_published=True)
        .annotate(enrollment_count=Count("enrolled_students") - 1)
        .order_by("-created_at")[:5]
    )
    
    enrolled_courses = StudentEnrollment.objects.filter(user=user).exclude(course__instructor=user)

    edu_total_earnings = user.edu_total_earnings
    edu_total_reviews = CourseRating.objects.filter(course__instructor=user).count()
    edu_instrcutor_courses = user.edu_instrcutor_courses
    edu_instructor_total_students = user.edu_instructor_total_students

    # Prepare data for the Course Enrollment Chart
    course_titles = [course.title for course in listed_courses]
    enrollment_counts = [course.enrollment_count for course in listed_courses]
    
    # Notifications
    # Fetch unread notifications for the user
    unread_notifications = Notification.objects.filter(
        user=user, is_read=False, app_name="eduprenair"
    )

    # Mark unread notifications as read
    unread_notifications.update(is_read=True)

    # Fetch all notifications (including the ones just marked as read)
    notifications = Notification.objects.filter(
        user=user, app_name="eduprenair"
    ).order_by("-created_at")[:5]
    
    # Serialize the data
    listed_courses_data = [
        {
            "id": course.id,
            "title": course.title,
            "slug": course.slug,
            "price": float(course.price) if course.price else 0,
            "enrollment_count": course.enrollment_count,
            "thumbnail": course.thumbnail.url if course.thumbnail else None,
            "created_at": course.created_at,
        } for course in listed_courses
    ]
    
    enrolled_courses_data = [
        {
            "id": enrollment.course.id,
            "title": enrollment.course.title,
            "slug": enrollment.course.slug,
            "instructor": enrollment.course.instructor.username,
            "thumbnail": enrollment.course.thumbnail.url if enrollment.course.thumbnail else None,
            "enrolled_at": enrollment.enrolled_at,
        } for enrollment in enrolled_courses
    ]
    
    notifications_data = [
        {
            "id": notification.id,
            "message": notification.message,
            "is_read": notification.is_read,
            "created_at": notification.created_at,
        } for notification in notifications
    ]
    
    data = {
        "user": {
            "id": user.id,
            "username": user.username,
            # Add other user fields as needed
        },
        "listed_courses": listed_courses_data,
        "enrolled_courses": enrolled_courses_data,
        "edu_total_earnings": float(edu_total_earnings) if edu_total_earnings else 0,
        "edu_total_reviews": edu_total_reviews,
        "edu_instrcutor_courses": edu_instrcutor_courses,
        "edu_instructor_total_students": edu_instructor_total_students,
        "chart_data": {
            "course_titles": course_titles,
            "enrollment_counts": enrollment_counts,
        },
        "notifications": notifications_data,
    }
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@admin_not_allowed
def manage_courses_eduprenair_api(request):
    user = request.user

    # Fetch courses categorized by their state
    published_courses = user.course_set.filter(is_published=True).order_by("-created_at")
    not_published_courses = user.course_set.filter(
        is_published=False, submit_for_approval=False
    ).order_by("-created_at")
    pending_courses = user.course_set.filter(
        submit_for_approval=True, is_published=False
    ).order_by("-created_at")

    # Serialize the data
    published_courses_data = CourseSerializer(published_courses, many=True).data
    not_published_courses_data = CourseSerializer(not_published_courses, many=True).data
    pending_courses_data = CourseSerializer(pending_courses, many=True).data
    
    data = {
        "user": {
            "id": user.id,
            "username": user.username,
        },
        "published_courses": published_courses_data,
        "not_published_courses": not_published_courses_data,
        "pending_courses": pending_courses_data,
    }
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@admin_not_allowed
def get_child_categories_api(request):
    parent_id = request.query_params.get("parent_id")
    if parent_id:
        categories = CourseCategory.objects.filter(parent_id=parent_id)
    else:
        categories = CourseCategory.objects.none()

    category_data = [{"id": cat.id, "name": cat.name} for cat in categories]
    return Response({"categories": category_data}, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@admin_not_allowed
def course_create_eduprenair_api(request):
    user = request.user
    
    if not user.is_edu_instructor:
        return Response(
            {"error": "You are not an Instructor. Access denied."}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == "GET":
        level_1_categories = CourseCategory.objects.filter(parent=None)
        categories_data = [
            {
                "id": category.id,
                "name": category.name,
            } for category in level_1_categories
        ]
        
        return Response({"categories": categories_data}, status=status.HTTP_200_OK)
    
    elif request.method == "POST":
        serializer = CourseSerializer(data=request.data)
        if serializer.is_valid():
            course = serializer.save(instructor=user)
            course.enrolled_students.add(user)
            course.save()
            StudentEnrollment.objects.create(user=user, course=course)
            
            return Response(
                {
                    "message": "Course Added to Draft. Modify there further for Submission!",
                    "course": serializer.data
                }, 
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@admin_not_allowed
def submit_for_approval_api(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug, instructor=request.user)
    
    if course.submit_for_approval:
        return Response(
            {"message": "This course has already been submitted for approval."}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    else:
        course.submit_for_approval = True
        course.save()
        return Response(
            {"message": "Your course has been submitted for approval."}, 
            status=status.HTTP_200_OK
        )


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@admin_not_allowed
def course_edit_eduprenair_api(request, course_slug):
    user = request.user
    
    # Check if the user is an instructor
    if not user.is_edu_instructor:
        return Response(
            {"error": "You are not an Instructor. Access denied."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    # Fetch the course to be edited, ensuring it belongs to the logged-in instructor
    course = get_object_or_404(Course, slug=course_slug, instructor=user)
    
    if request.method == "GET":
        serializer = CourseSerializer(course)
        level_1_categories = CourseCategory.objects.filter(parent=None)
        categories_data = [
            {
                "id": category.id,
                "name": category.name,
            } for category in level_1_categories
        ]
        
        # Prepare category data for the frontend
        category_info = {
            "categories": categories_data,
            "selected_category_l_1": course.category_l_1.id if course.category_l_1 else None,
            "selected_category_l_2": course.category_l_2.id if course.category_l_2 else None,
            "selected_category_l_3": course.category_l_3.id if course.category_l_3 else None,
        }
        
        return Response({
            "course": serializer.data,
            "category_info": category_info
        }, status=status.HTTP_200_OK)
    
    elif request.method in ["PUT", "PATCH"]:
        serializer = CourseSerializer(course, data=request.data, partial=request.method=="PATCH")
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Course updated successfully!", "course": serializer.data},
                status=status.HTTP_200_OK
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@admin_not_allowed
def delete_course_api(request, slug):
    user = request.user

    # Check if the user is an instructor
    if not user.is_edu_instructor:
        return Response(
            {"error": "You are not an Instructor. Access denied."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    # Fetch the course to be deleted, ensuring it belongs to the logged-in instructor
    course = get_object_or_404(Course, slug=slug, instructor=user)

    # Delete the course
    course.delete()
    return Response(
        {"message": "Course deleted successfully!"}, 
        status=status.HTTP_204_NO_CONTENT
    )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@admin_not_allowed
def add_module_course_eduprenair_api(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug, instructor=request.user)
    
    if request.method == "GET":
        modules = Module.objects.filter(course=course)
        serializer = ModuleSerializer(modules, many=True)
        return Response({
            "course": {
                "id": course.id,
                "title": course.title,
                "slug": course.slug,
            },
            "modules": serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == "POST":
        title = request.data.get("title")
        description = request.data.get("description")
        order = request.data.get("order")

        if not all([title, description, order]):
            return Response(
                {"error": "All fields are required to add a module."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if Module.objects.filter(course=course, order=order).exists():
            return Response(
                {"error": "A module with this order already exists in the course."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        module = Module.objects.create(
            course=course, title=title, description=description, order=order
        )
        
        serializer = ModuleSerializer(module)
        return Response({
            "message": f'Module "{module.title}" has been added successfully!',
            "module": serializer.data
        }, status=status.HTTP_201_CREATED)
        
        
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Count, Avg, Max
from django.utils.text import slugify
import uuid
import json
import markdown
from django.utils.safestring import mark_safe
from django.core.files.storage import default_storage

from groq import Groq
from django.conf import settings


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def add_lesson_course_eduprenair_api(request, module_id):
    # Fetch the module and ensure it's related to the logged-in instructor's course
    module = get_object_or_404(Module, id=module_id, course__instructor=request.user)

    if request.method == "POST":
        title = request.data.get("title")
        description = request.data.get("description")
        video = request.FILES.get("video")
        order = request.data.get("order")

        # Ensure that user only uploads video or PDF
        if video and not video.name.endswith((".mp4", ".avi", ".mov", ".pdf")):
            return Response(
                {"error": "Only video files (mp4, avi, mov) or PDF files are allowed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if Lesson.objects.filter(module=module, order=order).exists():
            return Response(
                {"error": "A lesson with this order already exists in the module."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if video and video.size > 100 * 1024 * 1024:
            return Response(
                {"error": "The file size should not be greater than 100MB."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if title and video and order:
            lesson = Lesson.objects.create(
                module=module,
                title=title,
                description=description if description else None,
                video=video,
                order=order,
                slug=f"{slugify(title)}-{module.id}-{order}_{str(uuid.uuid4().int)[:6]}",
            )
            serializer = LessonSerializer(lesson)
            return Response({
                "message": f'Lesson "{lesson.title}" has been added successfully!',
                "lesson": serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {"error": "All fields are required to add a lesson."},
                status=status.HTTP_400_BAD_REQUEST
            )

    # If GET request, return module data with its lessons
    module_serializer = ModuleSerializer(module, context={'request': request})
    return Response(module_serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_lesson_api(request, lesson_id):
    lesson = get_object_or_404(
        Lesson, id=lesson_id, module__course__instructor=request.user
    )

    lesson_title = lesson.title
    course_slug = lesson.module.course.slug
    
    # Delete the lesson
    lesson.delete()
    
    return Response({
        "message": f'Lesson "{lesson_title}" has been deleted successfully!',
        "course_slug": course_slug
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def course_stats_api(request, course_slug):
    user = request.user
    course = get_object_or_404(Course, slug=course_slug, instructor=user)
    
    if not course.is_published:
        return Response({
            "error": 'This course is not published yet.'
        }, status=status.HTTP_403_FORBIDDEN)

    if course.instructor != user:
        return Response({
            "error": 'You are not authorized to view this page.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    students = StudentEnrollment.objects.filter(course=course).exclude(user=user)
    
    course_serializer = CourseSerializer(course)
    students_serializer = StudentEnrollmentSerializer(students, many=True)
    
    return Response({
        'course': course_serializer.data,
        'students': students_serializer.data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def digi_reviews_api(request):
    user = request.user
    if not user.is_digi_seller:
        return Response({
            "error": 'You are not a seller. Access denied.'
        }, status=status.HTTP_403_FORBIDDEN)

    product_id = request.query_params.get('product')
    rating = request.query_params.get('rating')
    sort = request.query_params.get('sort', 'newest')

    reviews = Review.objects.filter(product__seller=user)
    if product_id and product_id != 'all':
        reviews = reviews.filter(product_id=product_id)
    
    if rating and rating != 'all':
        reviews = reviews.filter(rating=rating)
    
    if sort == 'oldest':
        reviews = reviews.order_by('created_at')
    elif sort == 'highest':
        reviews = reviews.order_by('-rating')
    elif sort == 'lowest':
        reviews = reviews.order_by('rating')
    else: 
        reviews = reviews.order_by('-created_at')

    products = Product.objects.filter(seller=user).annotate(
        review_count=Count('reviews')
    ).filter(review_count__gt=0)

    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    five_star_count = reviews.filter(rating=5).count()
    reviewed_products_count = products.count()

    reviews_serializer = ReviewSerializer(reviews, many=True)
    products_serializer = ProductSerializer(products, many=True)
    
    return Response({
        'reviews': reviews_serializer.data,
        'products': products_serializer.data,
        'avg_rating': avg_rating,
        'five_star_count': five_star_count,
        'reviewed_products_count': reviewed_products_count,
        'selected_product': product_id,
        'selected_rating': rating,
        'selected_sort': sort,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_commuprenair_api(request):
    user = request.user

    # CommuPrenair
    recent_posts = Post.objects.filter(author=user).order_by("-created_at")[:3]

    # Retrieve both sent and received connections for the user
    connections_sent = Connection.objects.filter(from_user=user).select_related("to_user")
    connections_received = Connection.objects.filter(to_user=user).select_related("from_user")

    # Combine both sent and received connections
    connections = list(
        set(
            [conn.to_user for conn in connections_sent]
            + [conn.from_user for conn in connections_received]
        )
    )

    # Fetch the latest message from each unique sender to this user
    latest_messages = (
        Message.objects.filter(receiver=user)
        .values("sender")
        .annotate(latest_timestamp=Max("timestamp"))
        .order_by("-latest_timestamp")
    )

    # Use the annotated timestamps to get the actual message objects
    user_messages = Message.objects.filter(
        receiver=user,
        timestamp__in=[entry["latest_timestamp"] for entry in latest_messages],
    ).order_by("-timestamp")
    
    # Notifications
    # Fetch unread notifications for the user
    unread_notifications = Notification.objects.filter(
        user=user, is_read=False, app_name="commuprenair"
    )

    # Mark unread notifications as read
    unread_notifications.update(is_read=True)

    # Fetch all notifications (including the ones just marked as read)
    notifications = Notification.objects.filter(
        user=user, app_name="commuprenair"
    ).order_by("-created_at")[0:5]
    
    # Serialize data
    posts_serializer = PostSerializer(recent_posts, many=True)
    user_serializer = UserSerializer(connections, many=True)
    messages_serializer = MessageSerializer(user_messages, many=True)
    notifications_serializer = NotificationSerializer(notifications, many=True)

    return Response({
        "recent_posts": posts_serializer.data,
        "connections": user_serializer.data,
        "user_messages": messages_serializer.data,
        "notifications": notifications_serializer.data,
    })


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def dashboard_edit_profile_api(request):
    user = request.user
    is_username_changed = user.is_username_changed

    if request.method == "PUT":
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            if 'username' in serializer.validated_data:
                user.is_username_changed = True
            serializer.save()
            return Response({
                "message": "Profile updated successfully!",
                "user": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # GET request
    serializer = UserSerializer(user)
    return Response({
        "user": serializer.data,
        "is_username_changed": is_username_changed
    })


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def dashboard_change_password_api(request):
    user = request.user
    
    if request.method == "PUT":
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")
        
        # Validate old password
        if not user.check_password(old_password):
            return Response({"error": "Current password is incorrect"}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Validate new password
        if new_password != confirm_password:
            return Response({"error": "New passwords don't match"}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Change password
        user.set_password(new_password)
        user.save()
        
        return Response({"message": "Your password has been updated successfully!"}, 
                       status=status.HTTP_200_OK)
    
    # GET request - just return success response for accessing the endpoint
    return Response({"message": "Password change form"})


@api_view(['POST'])
def generate_description_eduprenair_api(request):
    try:
        title = request.data.get("title", "")

        if not title.strip():
            return Response(
                {"error": "Title is required for description generation."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate description using Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        groq_response = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": f"Generate a detailed course description for a course titled: {title}",
                }
            ],
            model="llama3-8b-8192",
        )

        # Extract the generated description
        description_raw = groq_response.choices[0].message.content

        # Convert Markdown to HTML
        description_html = markdown.markdown(description_raw)
        description_html_safe = mark_safe(description_html)

        return Response({
            "description": description_raw,
            "description_html": description_html_safe,
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def generate_description_digiprenair_api(request):
    try:
        title = request.data.get("title", "")

        if not title.strip():
            return Response(
                {"error": "Title is required for description generation."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate description using Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        groq_response = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": f"Generate a detailed product description for: {title}. give in markdown format",
                }
            ],
            model="llama3-8b-8192",
        )

        # Extract the generated description
        description_d = groq_response.choices[0].message.content
        bot_reply_html = markdown.markdown(description_d)
        description = mark_safe(bot_reply_html)
        
        return Response({"description": description})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def generate_description_workprenair_api(request):
    try:
        title = request.data.get("title", "")

        if not title.strip():
            return Response(
                {"error": "Title is required for description generation."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate description using Groq API
        client = Groq(api_key=settings.GROQ_API_KEY)
        groq_response = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": f"Generate a detailed gig description for: {title}. Provide it in markdown format.",
                }
            ],
            model="llama3-8b-8192",
        )

        description_md = groq_response.choices[0].message.content
        description_html = markdown.markdown(description_md)
        
        return Response({"description": description_html}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)  
        
        
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum, Count, Avg
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.utils.text import slugify
from decimal import Decimal
from datetime import datetime, timedelta
import dateutil.relativedelta
from django.http import JsonResponse



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_dash_api(request):
    search_query = request.query_params.get("search", "")
    
    if search_query:
        users = CustomUser.objects.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone_no__icontains=search_query)
        )
    else:
        users = CustomUser.objects.all()

    # Custom pagination
    paginator = PageNumberPagination()
    paginator.page_size = 100
    result_page = paginator.paginate_queryset(users, request)
    serializer = CustomUserSerializer(result_page, many=True)
    
    return paginator.get_paginated_response({
        "users": serializer.data,
        "search_query": search_query
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_online_users_api(request):
    search_query = request.query_params.get("search", "")

    if search_query:
        users = CustomUser.objects.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone_no__icontains=search_query),
            is_online=True
        )
    else:
        users = CustomUser.objects.filter(is_online=True)

    # Custom pagination
    paginator = PageNumberPagination()
    paginator.page_size = 10
    result_page = paginator.paginate_queryset(users, request)
    serializer = CustomUserSerializer(result_page, many=True)
    
    return paginator.get_paginated_response({
        "users": serializer.data,
        "search_query": search_query
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_stats_api(request):
    # Calculate all the statistics
    total_users = CustomUser.objects.all().count()
    total_withdraw_requests = WithdrawalRequest.objects.filter(status="COMPLETED").count()
    total_withdraw_requests_pending = WithdrawalRequest.objects.filter(status="PENDING").count()
    total_amount_withdrawn = WithdrawalRequest.objects.filter(status="COMPLETED").aggregate(total_amount=Sum("amount"))["total_amount"] or 0
    
    # digiprenair
    total_digi_sellers = CustomUser.objects.filter(is_digi_seller=True).count()
    total_products = Product.objects.all().count()
    total_orders = Order.objects.all().count()
    
    # eduprenair
    total_instructors = CustomUser.objects.filter(is_edu_instructor=True).count()
    total_courses = Course.objects.all().count()
    total_enrollments = StudentEnrollment.objects.all().count()
    
    # commuprenair
    total_posts = Post.objects.all().count()
    total_groups = Group.objects.all().count()
    
    # workprenair
    total_work_sellers = CustomUser.objects.filter(is_work_freelancer=True).count()
    total_gigs = Gig.objects.all().count()
    total_work_orders = Order.objects.all().count()
    
    # Return all stats in a single response
    return Response({
        "total_users": total_users,
        "total_withdraw_requests": total_withdraw_requests,
        "total_withdraw_requests_pending": total_withdraw_requests_pending,
        "total_amount_withdrawn": total_amount_withdrawn,
        "total_digi_sellers": total_digi_sellers,
        "total_products": total_products,
        "total_orders": total_orders,
        "total_instructors": total_instructors,
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "total_posts": total_posts,
        "total_groups": total_groups,
        "total_work_sellers": total_work_sellers,
        "total_gigs": total_gigs,
        "total_work_orders": total_work_orders,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def withdrawal_requests_api(request):
    pending_requests = WithdrawalRequest.objects.filter(
        status__in=["PENDING", "PROCESSING"]
    )
    serializer = WithdrawalRequestSerializer(pending_requests, many=True)
    
    return Response({
        "pending_requests": serializer.data
    })


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def withdraw_admin_detail_api(request, withdraw_id):
    withdraw_request = get_object_or_404(WithdrawalRequest, id=withdraw_id)
    
    if request.method == "PUT":
        status_value = request.data.get("status")
        
        # Update the withdrawal request status
        withdraw_request.status = status_value
        
        # Handle financial transactions based on status
        if status_value == "FAILED":
            withdraw_request.user.available_earnings += Decimal(withdraw_request.amount + 3)
            withdraw_request.user.amount_being_cleared -= Decimal(withdraw_request.amount)
        elif status_value == "COMPLETED":
            withdraw_request.user.amount_being_cleared -= Decimal(withdraw_request.amount)
        
        # Save changes
        withdraw_request.save()
        withdraw_request.user.save()

        # Send email notification
        email_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
                <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                    <!-- Header -->
                    <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                        <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                    </div>

                    <!-- Body -->
                    <div style="padding: 20px;">
                        <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">Your Withdrawal Request is {status_value.capitalize()}!</h2>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {withdraw_request.user.username},</p>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">
                            Your withdrawal request of <strong>${withdraw_request.amount}</strong> has been updated to <strong>{status_value.capitalize()}</strong>. 
                        </p>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">
                            For further details, you can check your account dashboard.
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
        send_email(withdraw_request.user.email, f"Your Withdrawal Request is {status_value.capitalize()}!", email_content)

        # Create notification
        from .models import Notification
        Notification.objects.create(
            user=withdraw_request.user,
            app_name="workprenair",
            content=f"Your withdrawal request of ${withdraw_request.amount} is now {status_value.lower()}.",
        )
        
        return Response({
            "message": "Action on withdrawal request completed successfully!"
        }, status=status.HTTP_200_OK)
    
    # GET request - return withdrawal request details
    serializer = WithdrawalRequestSerializer(withdraw_request)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_traffic_logs_api(request):
    # Date filtering
    period = request.query_params.get('period', 'day')
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    qs = TrafficLog.objects.all()
    
    # Apply date filters
    if start_date and end_date:
        qs = qs.filter(timestamp__date__range=[start_date, end_date])
    else:
        if period == 'week':
            qs = qs.filter(timestamp__gte=datetime.now() - dateutil.relativedelta.relativedelta(weeks=1))
        elif period == 'month':
            qs = qs.filter(timestamp__gte=datetime.now() - dateutil.relativedelta.relativedelta(months=1))
        else:  # Default to daily
            qs = qs.filter(timestamp__date=datetime.now().date())

    # Aggregate data
    traffic_data = qs.annotate(
        date=functions.Trunc('timestamp', period)
    ).values('date', 'country').annotate(
        visits=Count('id')
    ).order_by('-date')

    return Response({
        'traffic_data': list(traffic_data),
        'total_visits': qs.count(),
        'countries': list(qs.values('country').annotate(total=Count('id')))
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def traffic_insights_json_api(request):
    period = request.query_params.get('period', 'day')
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    # Base queryset
    qs = TrafficLog.objects.filter(is_staff=False)
    
    # Date filtering
    date_filters = Q()
    if start_date and end_date:
        date_filters &= Q(timestamp__date__gte=start_date)
        date_filters &= Q(timestamp__date__lte=end_date)
    else:
        if period == 'week':
            date_filters &= Q(timestamp__gte=datetime.now() - timedelta(days=7))
        elif period == 'month':
            date_filters &= Q(timestamp__gte=datetime.now() - timedelta(days=30))
        else:  # Default to daily
            date_filters &= Q(timestamp__date=datetime.now().date())
    
    filtered_qs = qs.filter(date_filters)
    
    # Time series aggregation
    trunc_map = {
        'day': TruncDate('timestamp'),
        'week': TruncWeek('timestamp'),
        'month': TruncMonth('timestamp')
    }
    time_trunc = trunc_map.get(period, TruncDate('timestamp'))
    
    timeline_data = (
        filtered_qs
        .annotate(time_period=time_trunc)
        .values('time_period')
        .annotate(visits=Count('id'))
        .order_by('time_period')
    )
    
    # Country distribution
    country_data = (
        filtered_qs
        .values('country')
        .annotate(visits=Count('id'))
        .order_by('-visits')[:10]
    )
    
    # Device breakdown
    device_data = (
        filtered_qs
        .values('device_type')
        .annotate(visits=Count('id'))
        .order_by('-visits')
    )
    
    # Top pages
    top_pages = (
        filtered_qs
        .values('url')
        .annotate(visits=Count('id'))
        .order_by('-visits')[:5]
    )
    
    # Referrer analysis
    referrer_data = (
        filtered_qs
        .exclude(referrer='')
        .values('referrer')
        .annotate(visits=Count('id'))
        .order_by('-visits')[:5]
    )
    
    # Use DRF Response instead of JsonResponse for consistency
    return Response({
        'timeline': list(timeline_data),
        'countries': list(country_data),
        'devices': list(device_data),
        'top_pages': list(top_pages),
        'referrers': list(referrer_data),
        'total_visits': filtered_qs.count()
    })  
        
        
        
        
        
        
        
        
        
        






########################################################################################    payout views api's ########################################################################################
from decimal import Decimal
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404



@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def payout_request_api(request):
    user = request.user
    
    # Check if user has a payout account
    user_payoneer = PayoutAccount.objects.filter(user=user).exists()
    if not user_payoneer:
        return Response(
            {"error": "Please attach your payout account first"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if request.method == "POST":
        amount = request.data.get('amount')
        acc_type = request.data.get('account_type')
        
        # Validate amount
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid amount entered"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if acc_type == 'Payoneer' and not user.payout_account.filter(type='Payoneer').exists():
            return Response(
                {"error": "Please add your Payoneer account in your payout settings"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if acc_type == 'Paypal' and not user.payout_account.filter(type='Paypal').exists():
            return Response(
                {"error": "Please add your Paypal account in your payout settings"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if amount <= 4:
            return Response(
                {"error": "Amount must be greater than or equal to $5"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if amount > user.available_earnings:
            return Response(
                {"error": "You cannot withdraw more than your available balance"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        amount_to_add = amount - 3
        
        withdrawal = WithdrawalRequest.objects.create(
            user=user,
            amount=amount_to_add,
            status='PENDING',
            payout_type=acc_type
        )
        
        user.available_earnings -= Decimal(amount)
        user.amount_being_cleared += Decimal(amount_to_add)
        user.save()
        
        return Response({
            "message": "Your payout request has been submitted successfully",
            "withdrawal_id": withdrawal.id,
            "amount": amount_to_add,
            "status": "PENDING"
        }, status=status.HTTP_201_CREATED)
    
    # For GET request, return user's payout information
    return Response({
        "available_earnings": user.available_earnings,
        "has_payoneer": user.payout_account.filter(type='Payoneer').exists(),
        "has_paypal": user.payout_account.filter(type='Paypal').exists()
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def payout_settings_api(request):
    user = request.user
    
    if request.method == "POST":
        email = request.data.get('email')
        name = request.data.get('fullname')
        acc_type = request.data.get('acc_type')

        if not email or not name:
            return Response(
                {"error": "Please provide both email and full name"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if acc_type == 'Paypal':
            account, created = PayoutAccount.objects.update_or_create(
                user=user,
                type='Paypal',
                defaults={
                    'email': email,
                    'name': name
                }
            )
            return Response({
                "message": "Paypal account details updated successfully",
                "account": {
                    "id": account.id,
                    "email": account.email,
                    "name": account.name,
                    "type": account.type
                }
            }, status=status.HTTP_200_OK)
        
        elif acc_type == 'Payoneer':
            account, created = PayoutAccount.objects.update_or_create(
                user=user,
                type='Payoneer',
                defaults={
                    'email': email,
                    'name': name,
                }
            )
            return Response({
                "message": "Payoneer account details updated successfully",
                "account": {
                    "id": account.id,
                    "email": account.email,
                    "name": account.name,
                    "type": account.type
                }
            }, status=status.HTTP_200_OK)
        
        else:
            return Response(
                {"error": "Invalid account type. Choose either 'Paypal' or 'Payoneer'"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # For GET request, fetch user's payout accounts
    payoneer_acc = PayoutAccount.objects.filter(user=user, type='Payoneer').first()
    paypal_acc = PayoutAccount.objects.filter(user=user, type='Paypal').first()
    
    payoneer_data = None
    if payoneer_acc:
        payoneer_data = {
            "id": payoneer_acc.id,
            "name": payoneer_acc.name,
            "email": payoneer_acc.email
        }
    
    paypal_data = None
    if paypal_acc:
        paypal_data = {
            "id": paypal_acc.id,
            "name": paypal_acc.name,
            "email": paypal_acc.email
        }
    
    return Response({
        "payoneer_account": payoneer_data,
        "paypal_account": paypal_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_history_api(request):
    user = request.user
    withdrawals = WithdrawalRequest.objects.filter(user=user)
    
    withdrawal_data = []
    for withdrawal in withdrawals:
        withdrawal_data.append({
            "id": withdrawal.id,
            "amount": withdrawal.amount,
            "status": withdrawal.status,
            "payout_type": withdrawal.payout_type,
            "created_at": withdrawal.created_at,  # Assuming this field exists
            "updated_at": withdrawal.updated_at if hasattr(withdrawal, 'updated_at') else None
        })
    
    return Response({"withdrawals": withdrawal_data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_billings_api(request):
    user = request.user
    
    user_plans = UserPlan.objects.filter(user=user)
    user_plan_data = []
    
    for plan in user_plans:
        user_plan_data.append({
            "id": plan.id,
            "plan_name": plan.plan.title if hasattr(plan, 'plan') else None,
            "start_date": plan.start_date if hasattr(plan, 'start_date') else None,
            "end_date": plan.end_date if hasattr(plan, 'end_date') else None,
            "is_active": plan.is_active if hasattr(plan, 'is_active') else None,
            "price": plan.price if hasattr(plan, 'price') else None
        })
    
    plans = PricingPlan.objects.all()
    plan_data = []
    
    for plan in plans:
        plan_data.append({
            "id": plan.id,
            "title": plan.title,
            "price": plan.price if hasattr(plan, 'price') else None,
            "description": plan.description if hasattr(plan, 'description') else None,
            "features": plan.features if hasattr(plan, 'features') else None
        })
    
    basic_plan = get_object_or_404(PricingPlan, title='FreeTier')
    startprenair_plan = get_object_or_404(PricingPlan, title='StartPrenair')
    bizprenair_plan = get_object_or_404(PricingPlan, title='BizPrenair')
    entreprenair_plan = get_object_or_404(PricingPlan, title='EntrePrenair')
    
    return Response({
        "user_plans": user_plan_data,
        "all_plans": plan_data,
        "available_plans": {
            "basic_plan": {
                "id": basic_plan.id,
                "title": basic_plan.title,
                "price": basic_plan.price if hasattr(basic_plan, 'price') else None
            },
            "startprenair_plan": {
                "id": startprenair_plan.id,
                "title": startprenair_plan.title,
                "price": startprenair_plan.price if hasattr(startprenair_plan, 'price') else None
            },
            "bizprenair_plan": {
                "id": bizprenair_plan.id,
                "title": bizprenair_plan.title,
                "price": bizprenair_plan.price if hasattr(bizprenair_plan, 'price') else None
            },
            "entreprenair_plan": {
                "id": entreprenair_plan.id,
                "title": entreprenair_plan.title,
                "price": entreprenair_plan.price if hasattr(entreprenair_plan, 'price') else None
            }
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def paypal_manual_transfer_api(request):
    user = request.user
    
    amount = request.data.get('amount', 0)
    try:
        amount = float(amount)
        amount = Decimal(amount)
    except (ValueError, TypeError):
        return Response(
            {"error": "Invalid amount provided"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if amount <= 0:
        return Response(
            {"error": "Amount must be greater than zero"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if amount > user.available_earnings:
        return Response(
            {"error": "You cannot withdraw more than your available balance"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user.available_earnings -= amount
    user.save()
    
    withdrawal = WithdrawalRequest.objects.create(
        user=user, 
        amount=amount, 
        status='COMPLETED', 
        payout_type='MANUAL'
    )
    
    return Response({
        "message": "Your withdrawal request has been processed successfully",
        "withdrawal_id": withdrawal.id,
        "amount": float(amount),
        "status": "COMPLETED"
    }, status=status.HTTP_201_CREATED)