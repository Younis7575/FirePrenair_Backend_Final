from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.db.models import Count, Q, Avg
from django.utils import timezone
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from edu_prenair.models import *
from profiles.models import *
from edu_prenair.decorators import *
import stripe
import uuid
import io
from io import BytesIO
import requests
from django.core.exceptions import BadRequest
from PIL import Image, ImageDraw, ImageFont
import markdown
from django.utils.safestring import mark_safe
import json
from groq import Groq
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI
from .serializers import *
from rest_framework.decorators import parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
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
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import *
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view  # <-- Add this import
from rest_framework.decorators import permission_classes  # Import permission_classes decorator
from django.db.models import Q
import os





# client = OpenAI(api_key=settings.OPENAI_API_KEY)
client = Groq(api_key=settings.GROQ_API_KEY)

# Knowledge base for chatbot
knowledge_base = {
    "eduprenair": {
        "description": """
            Eduprenair is the learning hub of Fireprenair, providing courses, resources, and tools to help users enhance their skills 
            in business management, AI technology, digital marketing, and more. It ensures both beginners and advanced learners can 
            achieve their professional goals through personalized recommendations and AI-powered learning tools.
        """,
        "features": [
            "Comprehensive courses on AI, business management, and digital marketing.",
            "AI-driven personalized course recommendations.",
            "Resources tailored for both beginners and advanced learners.",
            "Interactive tools and materials for self-paced learning.",
        ],
        "faq": {
            "What type of courses are offered?": "Eduprenair provides courses in business management, AI technology, digital marketing, and personal development.",
            "Are the courses beginner-friendly?": "Yes, Eduprenair offers resources for all levels, from beginners to advanced learners.",
            "Can I get a certificate upon completion?": "Yes, some courses provide a certificate after successful completion of assessments.",
            "How can I access a course?": "Sign up on Fireprenair, navigate to Eduprenair, select a course, and enroll to start learning.",
            "Is there a free trial?": "Eduprenair offers free trial content for select courses to help users decide before enrolling.",
        },
    }
}


@csrf_exempt
@api_view(['POST'])
def eduprenair_chatbot_api(request):
    user_message = request.data.get("message", "").lower()

    # Predefined responses for quick replies
    predefined_responses = {
        "name": "I am your customer support assistant, here to help you with any questions about Eduprenair.",
        "who_created_you": "I was created by the development team of Fireprenair.",
        "what_can_you_do": "I can help you navigate our platform, answer questions about our services, and provide consultation details.",
    }

    for key, response in predefined_responses.items():
        if key in user_message:
            return Response({"message": response})

    # Interact with Groq API
    client = Groq(api_key=settings.GROQ_API_KEY)
    groq_response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": json.dumps(
                    {
                        "knowledge_base": knowledge_base,
                        "instruction": "Please generate short, clear, and professional responses. "
                        "Limit unnecessary details, ensure the tone is formal, and provide concise answers. "
                        "Avoid elaboration and keep responses to the point."
                        "Give answer according to question.",
                    }
                ),
            },
            {"role": "user", "content": user_message},
        ],
        model="llama3-8b-8192",
    )

    # Process the Groq response
    bot_reply = groq_response.choices[0].message.content.strip()
    bot_reply_html = markdown.markdown(bot_reply)
    bot_reply_html = mark_safe(bot_reply_html)

    return Response({"message": bot_reply_html})

@api_view(['GET'])
@permission_classes([AllowAny])  # <--- This is the fix
def edu_home_api(request):
    try:
        best_courses = Course.objects.filter(is_published=True, best_selling=True)
        best_instructors = CustomUser.objects.filter(
            is_edu_instructor=True, featured_instructor=True
        )
        course_categories = CourseCategory.objects.filter(is_featured=True)
        
        # You would typically use serializers here to convert models to JSON
        context = {
            "best_courses": [
                {
                    "id": course.slug,
                    "title": course.title,
                    "slug": course.slug,
                    "price": course.price,
                    "instructor": UserDataSerializer(course.instructor, context={"request": request}).data,
                    "thumbnail": request.build_absolute_uri(course.thumbnail.url) if course.thumbnail else None,
                }
                for course in best_courses
            ],
            # "best_instructors": [
            #     {
            #         "id": instructor.slug,
            #         "name": instructor.name,
            #         "slug": instructor.slug,
            #         "profile_pic": request.build_absolute_uri(instructor.profile_pic.url) if instructor.profile_pic else None,
            #     }
            #     for instructor in best_instructors
            # ],
            "best_instructors": UserDataSerializer(best_instructors, many=True, context={"request": request}).data,
            "course_categories":CourseCategorySerializer(course_categories,many=True,context={"request": request}).data,
            # "course_categories": [
            #     {
            #         "id": category.pk,
            #         "name": category.name,
            #         "desc": category.description,
            #     }
            #     for category in course_categories
            # ],
        }

        return Response(context)
    except Exception as e:
        print(e)
        return Response(e,status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def edu_profile_api(request, slug):
    profile = get_object_or_404(CustomUser, slug=slug)
    
    context = {
        "profile": {
            "id": profile.id,
            "name": profile.name,
            "username": profile.username,
            "email": profile.email,
            "edu_bio": profile.edu_bio,
            "is_edu_instructor": profile.is_edu_instructor,
            "profile_pic": profile.profile_pic.url if profile.profile_pic else None,
        }
    }
    return Response(context)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def edu_settings_api(request):
    if request.method == "POST":
        user = request.user

        name = request.data.get("name")
        bio = request.data.get("bio")
        profile_pic = request.FILES.get("profile_pic")

        user.name = name
        user.edu_bio = bio

        if profile_pic:
            user.profile_pic = profile_pic
        user.save()

        return Response({"message": "Profile updated successfully."}, status=status.HTTP_200_OK)

    # GET method
    user = request.user
    context=UserSerializer(user).data
    return Response(context)


class InstructorsPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100


class InstructorsAPIView(APIView):
    permission_classes = [AllowAny]
    pagination_class = InstructorsPagination

    def get(self, request):
        try:
            search_query = request.query_params.get("search", "").strip()
            category_id = request.query_params.get("category", "").strip()
            selected_categories = request.query_params.getlist("category")
            selected_instructors = request.query_params.getlist("instructor")

            edu_instructors = CustomUser.objects.filter(is_edu_instructor=True)
            top_level_categories = CourseCategory.objects.filter(parent__isnull=True)
            second_level_categories = CourseCategory.objects.filter(parent__in=top_level_categories)
            categories = top_level_categories | second_level_categories

            # Filter instructors by category
            if category_id:
                edu_instructors = edu_instructors.filter(
                    Q(course__category_l_1_id=category_id)
                    | Q(course__category_l_2_id=category_id)
                    | Q(course__category_l_3_id=category_id),
                    course__is_published=True,
                ).distinct()

            # Filter instructors by search query
            if search_query:
                edu_instructors = edu_instructors.filter(name__icontains=search_query)

            # Filter by selected categories
            if selected_categories:
                edu_instructors = edu_instructors.filter(
                    Q(course__category_l_1_id__in=selected_categories)
                    | Q(course__category_l_2_id__in=selected_categories)
                    | Q(course__category_l_3_id__in=selected_categories),
                    course__is_published=True,
                ).distinct()

            # Filter by selected instructors
            if selected_instructors:
                edu_instructors = edu_instructors.filter(id__in=selected_instructors).distinct()

            # Paginate results
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(edu_instructors, request)
            
            # Get all instructors with course count
            instructors_with_count = CustomUser.objects.filter(is_edu_instructor=True).annotate(
                course_count=Count("course")
            )

            # Format response data
            instructor_data = [
                {
                    "id": instructor.id,
                    "name": instructor.name,
                    "username": instructor.username,
                    # "slug": instructor.slug,
                    "profile_pic": request.build_absolute_uri(instructor.profile_pic.url) if instructor.profile_pic else None,
                }
                for instructor in page
            ]
            
            categories_data = [
                {
                    "id": category.id,
                    "name": category.name,
                    # "slug": category.slug,
                    "parent_id": category.parent_id,
                }
                for category in categories
            ]

            data = {
                "instructors": instructor_data,
                "categories": categories_data,
                "total_count": edu_instructors.count(),
            }
            
            return paginator.get_paginated_response(data)
        except Exception as e:
            print(e)
            

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def instructor_dashboard_api(request):
    if not request.user.is_edu_instructor:
        return Response({"message": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)
        
    courses_teaching = Course.objects.filter(
        instructor=request.user, is_published=True
    ).order_by("-created_at")
    
    students = CustomUser.objects.filter(enrolled_courses__in=courses_teaching).exclude(id=request.user.id)
    enrolled_courses = StudentEnrollment.objects.filter(user=request.user).exclude(course__instructor=request.user)
    completed_courses = enrolled_courses.filter(is_completed=True)
    
    stdentdata=UserSerializer(students, many=True).data
    enrolled_coursesdata=StudentEnrollmentSerializer(enrolled_courses, many=True).data
    completed_coursesdata=StudentEnrollmentSerializer(completed_courses, many=True).data
    context = {
        "courses_teaching": CourseSerializer(courses_teaching, many=True).data,
        "students": stdentdata,
        "enrolled_courses": enrolled_coursesdata,
        "completed_courses": completed_coursesdata,
    }
    return Response(context)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def edu_student_dashboard_api(request):
    if request.user.is_edu_instructor:
        return Response({"message": "Redirecting to instructor dashboard"}, status=status.HTTP_302_FOUND)

    enrolled_courses = StudentEnrollment.objects.filter(user=request.user)
    completed_courses = enrolled_courses.filter(is_completed=True)
    enrolled_coursesdata=StudentEnrollmentSerializer(enrolled_courses, many=True).data
    completed_coursesdata=StudentEnrollmentSerializer(completed_courses, many=True).data
    
    context = {
        "enrolled_courses": enrolled_coursesdata,
        "completed_courses": completed_coursesdata,
    }
    
    return Response(context)


class AllCoursesAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        search_query = request.query_params.get("search", "").strip()
        category_ids = [cid for cid in request.query_params.getlist("category") if cid.isdigit()]
        price_min = request.query_params.get("price_min", "").strip()
        price_max = request.query_params.get("price_max", "").strip()
        sort_by = request.query_params.get("sort_by", "relevance")  
        level = request.query_params.get("level", "").strip()  

        courses = Course.objects.filter(is_published=True)

        if search_query:
            courses = courses.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(instructor__name__icontains=search_query)
            )

        if category_ids:
            courses = courses.filter(
                Q(category_l_1_id__in=category_ids) |
                Q(category_l_2_id__in=category_ids) |
                Q(category_l_3_id__in=category_ids)
            )

        if price_min and price_min.isdigit():
            courses = courses.filter(price__gte=float(price_min))
        if price_max and price_max.isdigit():
            courses = courses.filter(price__lte=float(price_max))

        price_filter = request.query_params.get("price_filter", "")
        if price_filter == "free":
            courses = courses.filter(is_free=True)
        elif price_filter == "paid":
            courses = courses.filter(is_free=False)

        if level in ["Beginner", "Intermediate", "Advanced"]:
            courses = courses.filter(level=level)

        if sort_by == "price_low":
            courses = courses.order_by("price")
        elif sort_by == "price_high":
            courses = courses.order_by("-price")
        elif sort_by == "rating":
            courses = courses.annotate(avg_rating=Avg('courserating__rating')).order_by('-avg_rating')
        elif sort_by == "newest":
            courses = courses.order_by("-created_at")  

        top_level_categories = CourseCategory.objects.filter(parent__isnull=True)

        # Pagination
        paginator = Paginator(courses, 12) 
        page = request.query_params.get("page")
        try:
            courses_page = paginator.page(page)
        except PageNotAnInteger:
            courses_page = paginator.page(1)
        except EmptyPage:
            courses_page = paginator.page(paginator.num_pages)

        courses_data=CourseSerializer(courses, many=True).data
        categories_data = [
            {
                "id": category.id,
                "name": category.name,
                # "slug": category.slug,
            }
            for category in top_level_categories
        ]

        return Response({
            "courses": courses_data,
            "categories": categories_data,
            "count": courses.count(),
            "pages": paginator.num_pages,
            "current_page": courses_page.number,
            "filters": {
                "search_query": search_query,
                "price_min": price_min,
                "price_max": price_max,
                "sort_by": sort_by,
                "level": level,
            }
        })




@api_view(["POST"])
@permission_classes([IsAuthenticated])
# @parser_classes([MultiPartParser, FormParser])
def add_course_api(request):
    categories = CourseCategory.objects.all()  # still available if needed
    for i in categories:
        print(i.id)
    
    title = request.data.get("title")
    category_id = request.data.get("category")
    short_description = request.data.get("short_description")
    description = request.data.get("description")
    outcome = request.data.get("outcome")
    requirements = request.data.get("requirements")
    language = request.data.get("language")
    price = request.data.get("price")
    is_free = bool(request.data.get("is_free"))
    level = request.data.get("level")
    duration = request.data.get("duration")
    thumbnail = request.FILES.get("thumbnail")

    try:
        category = CourseCategory.objects.get(id=category_id)

        request.user.is_edu_instructor = True
        request.user.save()

        course = Course.objects.create(
            title=title,
            instructor=request.user,
            category_l_1=category,
            slug=f"{slugify(title)}-{request.user.username}-{str(uuid.uuid4().int)[:6]}",
            description=description,
            requirements=requirements,
            language=language,
            price=price if not is_free else 0,
            is_free=is_free,
            level=level,
            duration=duration,
            thumbnail=thumbnail,
            is_published=False,
        )

        return Response(
            {"message": "Course created successfully! Awaiting approval."},
            status=status.HTTP_201_CREATED
        )

    except Exception as e:
        return Response(
            {"error": f"Error creating course: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )







@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_courses_api(request):
    drafts = Course.objects.filter(instructor=request.user, submit_for_approval=False)
    courses = Course.objects.filter(instructor=request.user, is_published=True)
    pendings = Course.objects.filter(
        instructor=request.user, submit_for_approval=True, is_published=False
    )
    drafts_data = CourseSerializer(drafts, many=True).data
    courses_data = CourseSerializer(courses, many=True).data
    pendings_data = CourseSerializer(pendings, many=True).data
    context = {
        "drafts": drafts_data,
        "courses": courses_data,
        "pendings": pendings_data,
    }
    
    return Response(context)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_for_approval_api(request, slug):
    course = get_object_or_404(Course, slug=slug, instructor=request.user)

    if course.submit_for_approval:
        return Response({"message": "This course has already been submitted for approval."}, status=status.HTTP_400_BAD_REQUEST)
    else:
        course.submit_for_approval = True
        course.save()
        return Response({"message": "Your course has been submitted for approval."}, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def add_module_api(request, course_slug):
    try:
        course = get_object_or_404(Course, slug=course_slug, instructor=request.user)
        
        if request.method == "POST":
            title = request.data.get("title")
            description = request.data.get("description")
            order = request.data.get("order")

            if not all([title, description, order]):
                return Response(
                    {"error": "All fields are required to add a module."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            module = Module.objects.create(
                course=course, title=title, description=description, order=order
            )
            moduledata=ModuleSerializer(module).data
            return Response({
                "message": f'Module "{module.title}" has been added successfully!',
                "module": moduledata
            }, status=status.HTTP_201_CREATED)
        
        # GET request
        modules = Module.objects.filter(course=course)
        modules_data = [
            {
                "id": module.id,
                "title": module.title,
                "description": module.description,
                "order": module.order,
                "lessons_count": module.lessons.count(),
            }
            for module in modules
        ]
        
        return Response({
            "course": {
                "id": course.id,
                "title": course.title,
                "slug": course.slug,
            },
            "modules": modules_data
        })
    except Exception as e:
        return Response({"error": f"Error adding module: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_lesson_api(request, module_id):
    module = get_object_or_404(Module, id=module_id, course__instructor=request.user)
    
    title = request.data.get("title")
    video = request.FILES.get("video")
    order = request.data.get("order")

    if not all([title, video, order]):
        return Response(
            {"error": "All fields are required to add a lesson."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    lesson = Lesson.objects.create(
        module=module,
        title=title,
        video=video,
        order=order,
        slug=f"{slugify(title)}-{str(uuid.uuid4().int)[:6]}",
    )
    lessondata=LessonSerializer(lesson).data
    return Response({
        "message": f'Lesson "{lesson.title}" has been added successfully!',
        "lesson": lessondata
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_lesson_completed_api(request, lesson_slug, course_slug):
    lesson = get_object_or_404(Lesson, slug=lesson_slug)
    course = get_object_or_404(Course, slug=course_slug)
    enrollment = get_object_or_404(
        StudentEnrollment, user=request.user, course=course
    )
    completed_lessons = enrollment.completed_lessons.all()
    enrollment.add_completed_lesson(lesson)

    total_lessons = course.modules.aggregate(total_lessons=models.Count("lessons"))[
        "total_lessons"
    ]

    return Response({
        "message": "Lesson marked as completed",
        "progress": enrollment.progress,
        "completed_lessons": completed_lessons.count(),
        "is_completed": enrollment.is_completed,
        "total_lessons": total_lessons,
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_course_api(request, slug):
    course = get_object_or_404(Course, slug=slug, instructor=request.user)
    course.delete()
    return Response({"message": "Course deleted successfully."}, status=status.HTTP_200_OK)


@api_view(['GET'])
def course_detail_api(request, slug):
    course = get_object_or_404(Course, slug=slug)

    sub_description_html = markdown.markdown(course.description[0:100] + ". . . . .")
    description_html = markdown.markdown(course.description)

    is_enrolled = (request.user.is_authenticated and StudentEnrollment.objects.filter(user=request.user, course=course).first())
    has_rated = (request.user.is_authenticated and CourseRating.objects.filter(user=request.user, course=course).exists())

    prev_course = Course.objects.filter(created_at__lt=course.created_at).order_by('-created_at').first()
    next_course = Course.objects.filter(created_at__gt=course.created_at).order_by('created_at').first()

    # Get modules and lessons
    modules_data = []
    for module in course.modules.all():
        module_data = {
            "id": module.id,
            "title": module.title,
            "description": module.description,
            "order": module.order,
            "lessons": [
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "slug": lesson.slug,
                    "order": lesson.order,
                }
                for lesson in module.lessons.all()
            ]
        }
        modules_data.append(module_data)

    context = {
        "course": {
            "id": course.id,
            "title": course.title,
            "slug": course.slug,
            "description": course.description,
            "description_html": description_html,
            "sub_description_html": sub_description_html,
            "price": course.price,
            "is_free": course.is_free,
            "level": course.level,
            "duration": course.duration,
            "language": course.language,
            "requirements": course.requirements,
            "thumbnail": request.build_absolute_uri(course.thumbnail.url) if course.thumbnail else None,
            "created_at": course.created_at,
            "instructor": {
                "id": course.instructor.id,
                "name": course.instructor.name,
                "slug": course.instructor.slug,
                "profile_pic": request.build_absolute_uri(course.instructor.profile_pic.url) if course.instructor.profile_pic else None,
            },
            "student_count": course.enrolled_students.count(),
            "rating_avg": CourseRating.objects.filter(course=course).aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0,
            "rating_count": CourseRating.objects.filter(course=course).count(),
        },
        "is_enrolled": bool(is_enrolled),
        "has_rated": has_rated,
        "prev_course": {
            "slug": prev_course.slug,
            "title": prev_course.title
        } if prev_course else None,
        "next_course": {
            "slug": next_course.slug,
            "title": next_course.title
        } if next_course else None,
        "modules": modules_data,
    }

    return Response(context)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def course_content_api(request, slug):
    course = get_object_or_404(Course, slug=slug)
    enrollment = get_object_or_404(StudentEnrollment, user=request.user, course=course)

    description_html = markdown.markdown(course.description)

    
    context = {
        "course": course,
        "enrollment": enrollment,
        "modules": course.modules.all().prefetch_related('lessons'),
        "progress": enrollment.progress,
        "description_html": description_html
    }
    return Response(context, status=status.HTTP_200_OK)


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
import json
import io
import stripe
import requests
import paypalrestsdk
from paypalrestsdk import Payment
from PIL import Image, ImageDraw, ImageFont
from decimal import Decimal
from io import BytesIO
from django.http import HttpResponse, FileResponse

from edu_prenair.models import *
from .serializers import *


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_lesson_api(request, lesson_slug):
    lesson = get_object_or_404(Lesson, slug=lesson_slug)
    course = lesson.module.course
    
    if not course.is_user_enrolled(request.user):
        return Response(
            {"error": "You must be enrolled in this course to access the materials."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if lesson.is_pdf():
        if settings.USE_S3_STORAGE:
            pdf_url = f"https://fireprenair.s3.amazonaws.com/{lesson.video}"
        else:
            pdf_url = request.build_absolute_uri(lesson.video.url)

        return Response({
            "pdf_url": pdf_url,
            "material": LessonSerializer(lesson).data
        })
    
    data = {
        'type': 'pdf' if lesson.is_pdf() else 'video',
        'url': lesson.video.url,
        'title': lesson.title,
        'description': lesson.description
    }
    return Response(data)


# ------------------- Quiz -------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_quiz_api(request, course_slug):
    try:
        course = get_object_or_404(Course, slug=course_slug)
    except Course.DoesNotExist:
        return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get user prompt from request
    user_prompt = request.data.get('prompt', '')
    
    # Prepare course content for AI
    course_content = f"""
    Course Title: {course.title}
    Description: {course.description}
    Level: {course.level}
    
    Modules:
    """
    
    for module in course.modules.all():
        course_content += f"\nModule: {module.title}\n"
        for lesson in module.lessons.all():
            course_content += f"- Lesson: {lesson.title}\n"
            if lesson.description:
                course_content += f"  Description: {lesson.description}\n"
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"""
                    You are an expert quiz generator for an online learning platform. 
                    Based on the following course content and user request, generate a relevant quiz.
                    
                    Course Content:
                    {course_content}
                    
                    Generate 5-10 high-quality multiple choice questions with 4 options each.
                    Format your response as JSON with this structure:
                    {{
                        "title": "Quiz title based on user prompt",
                        "description": "Brief description of quiz",
                        "questions": [
                            {{
                                "question_text": "Question?",
                                "correct_answer": "Correct Answer",
                                "answer_options": ["Option1", "Option2", "Option3", "Option4"],
                                "explanation": "Explanation text"
                            }}
                        ]
                    }}
                    """
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.7
        )
        
        quiz_data = json.loads(response.choices[0].message.content)
        quiz = Quiz.objects.create(
            course=course,
            title=quiz_data['title'],
            description=quiz_data['description']
        )
        
        for q in quiz_data['questions']:
            QuizQuestion.objects.create(
                quiz=quiz,
                question_text=q['question_text'],
                correct_answer=q['correct_answer'],
                answer_options=q['answer_options'],
                explanation=q.get('explanation', ''),
                order=q.get('order', 0)
            )
        
        return Response({
            'success': True,
            'quiz_id': quiz.id,
            'title': quiz.title,
            'description': quiz.description,
            'num_questions': quiz.questions.count()
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def take_quiz_api(request, quiz_id):
    
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # Check if user is enrolled in the course
    if not request.user.enrolled_courses.filter(slug=quiz.course.slug).exists():
        return Response(
            {"error": "You must be enrolled in this course to take the quiz"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Create or get existing attempt
    attempt, created = QuizAttempt.objects.get_or_create(
        user=request.user,
        quiz=quiz,
        completed_at__isnull=True,
        defaults={'started_at': timezone.now()}
    )
    
    if request.method == 'POST':
        score = 0
        total_questions = quiz.questions.count()
        
        for question in quiz.questions.all():
            question_key = f'question_{question.id}'
            if question_key in request.data:
                selected_answer = request.data[question_key]
                is_correct = (selected_answer.lower().strip() == 
                             question.correct_answer.lower().strip())
                
                QuizQuestionResponse.objects.create(
                    attempt=attempt,
                    question=question,
                    selected_answer=selected_answer,
                    is_correct=is_correct
                )
                
                if is_correct:
                    score += 1
        
        attempt.score = (score / total_questions) * 100
        attempt.completed_at = timezone.now()
        attempt.save()
        
        return Response({
            "success": True,
            "message": f"Quiz completed! Score: {attempt.score:.1f}%",
            "score": attempt.score,
            "attempt_id": attempt.id
        })
    
    return Response({
        'quiz': QuizSerializer(quiz).data,
        'attempt': QuizAttemptSerializer(attempt).data,
        'questions': QuizQuestionSerializer(quiz.questions.all().order_by('order'), many=True).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def quiz_results_api(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
    return Response({
        'attempt': QuizAttemptSerializer(attempt).data,
        'quiz': QuizSerializer(attempt.quiz).data,
        'course': CourseSerializer(attempt.quiz.course).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_certificate_api(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    enrollment = get_object_or_404(StudentEnrollment, user=request.user, course=course)

    if not enrollment.is_completed:
        return Response({"error": "You haven't completed this course yet!"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        response = requests.get("https://fireprenair.s3.us-east-2.amazonaws.com/images/misc/Course_certificate.png")
        response.raise_for_status()
        
        img = Image.open(BytesIO(response.content))
        draw = ImageDraw.Draw(img)

        font_name = ImageFont.truetype("arial.ttf", 100)
        font_small = ImageFont.truetype("times.ttf", 40)
        user_name = request.user.name
        draw.text((900, 650), user_name, fill="black", font=font_name, anchor="mm")

        completion_date = enrollment.completion_date.strftime("%B %d, %Y")
        completion_text = f"For successfully completing the course '{course.title}' on {completion_date}"
        draw.text(
            (950, 750), completion_text, fill="black", font=font_small, anchor="mm"
        )

        course_instructor = course.instructor.name
        draw.text(
            (610, 1040),
            f"{course_instructor}",
            fill="black",
            font=font_small,
            anchor="mm",
        )

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        # Return as file response via REST framework
        return FileResponse(buffer, filename=f"{course_slug}_certificate.png", content_type="image/png")
    except IOError as e:
        return Response({"error": f"Error processing image: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_review_api(request, slug):
    course = get_object_or_404(Course, slug=slug)
    
    rating = request.data.get("rating")
    review_text = request.data.get("review_text", "").strip()

    if not rating and review_text:
        return Response({"error": "Please provide a rating and review text."}, status=status.HTTP_400_BAD_REQUEST)

    # Create course rating
    review = CourseRating.objects.create(
        user=request.user,
        course=course,
        rating=int(rating),
        review=review_text,
    )
    
    # Create notification
    Notification.objects.create(
        user=course.instructor,
        message=f"{request.user.username} has reviewed your course",
        app_name="eduprenair",
    )

    # Send email notification to the instructor
    instructor_email_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
            <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                    <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                </div>
                <div style="padding: 20px;">
                    <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">New Review Posted</h2>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {course.instructor.username},</p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                        A new review has been posted for your course <strong>{course.title}</strong> by <strong>{request.user.username}</strong>.
                    </p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Review Details:</strong></p>
                    <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                        <li style="margin-bottom: 10px;"><strong>Rating:</strong> {rating} stars</li>
                        <li style="margin-bottom: 10px;"><strong>Review:</strong> {review_text}</li>
                    </ul>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">You can view the review on your course page.</p>
                </div>
                <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                    <p style="margin: 0; font-size: 14px;">Thank you for being a valued instructor on FirePrenair! 🚀</p>
                </div>
            </div>
        </body>
        </html>
    """
    send_email(
        course.instructor.email,
        "New Review Posted on Your Course",
        instructor_email_content,
    )

    return Response({
        "success": True,
        "message": "Review posted successfully!",
        "review": CourseRatingSerializer(review).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_review_api(request):
    try:
        review_text = request.data.get('review', '')
        target_slug = request.data.get('target_slug', '')  
        is_work_review = request.data.get("work_review", False) 
    except Exception:
        return Response({'error': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
    
    if request.user.slug != target_slug:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    try:
        system_prompt = """Analyze this {} review. Provide:
        1. Sentiment (Positive/Negative/Neutral) and confidence level
        2. 3 key points from the review
        3. Suggestions for improvement based on the review

        Format response as JSON with keys: sentiment, key_points, suggestions""".format(
            "service/gig" if is_work_review else "course"
        )

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": review_text}
            ]
        )
        
        analysis = json.loads(response.choices[0].message.content)
        return Response({'analysis': analysis})
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reviews_api(request):
    reviews_given = CourseRating.objects.filter(user=request.user).exclude(
        course__instructor=request.user
    )
    reviews_received = CourseRating.objects.filter(course__instructor=request.user)

    return Response({
        "reviews_given": CourseRatingSerializer(reviews_given, many=True).data,
        "reviews_received": CourseRatingSerializer(reviews_received, many=True).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_courses_api(request):
    enrolled_courses = StudentEnrollment.objects.filter(user=request.user).exclude(course__instructor=request.user)
    active_courses = enrolled_courses.filter(is_completed=False)
    completed_courses = enrolled_courses.filter(is_completed=True)
    
    return Response({
        "enrolled_courses": [CourseSerializer(enrollment.course).data for enrollment in enrolled_courses],
        "active_courses": [CourseSerializer(enrollment.course).data for enrollment in active_courses],
        "completed_courses": [CourseSerializer(enrollment.course).data for enrollment in completed_courses],
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_wishlist_api(request, slug):
    course = get_object_or_404(Course, slug=slug)
    wishlist, created = CourseWishlist.objects.get_or_create(user=request.user, course=course)
    
    return Response({
        "success": True,
        "message": f'Course "{course.title}" has been added to your wishlist.',
        "wishlist": CourseWishlistSerializer(wishlist).data
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_from_wishlist_api(request, slug):
    course = get_object_or_404(Course, slug=slug)
    CourseWishlist.objects.filter(user=request.user, course=course).delete()
    
    return Response({
        "success": True,
        "message": f'Course "{course.title}" has been removed from your wishlist.'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wishlists_api(request):
    wishlists = CourseWishlist.objects.filter(user=request.user)
    return Response({
        "wishlists": CourseWishlistSerializer(wishlists, many=True).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_history_api(request):
    today = timezone.now()
    enrolls_today = StudentEnrollment.objects.filter(enrolled_date__date=today.date(), user=request.user)
    enrolls_month = StudentEnrollment.objects.filter(
        enrolled_date__year=today.year, enrolled_date__month=today.month, user=request.user
    )
    enrolls_year = StudentEnrollment.objects.filter(enrolled_date__year=today.year, user=request.user)

    return Response({
        "enrolls_today": [CourseSerializer(enrollment.course).data for enrollment in enrolls_today],
        "enrolls_month": [CourseSerializer(enrollment.course).data for enrollment in enrolls_month],
        "enrolls_year": [CourseSerializer(enrollment.course).data for enrollment in enrolls_year],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications_api(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    return Response({
        "notifications": [
            {
                "id": notification.id,
                "message": notification.message,
                "created_at": notification.created_at,
                "is_read": notification.is_read,
                "app_name": notification.app_name
            }
            for notification in notifications
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def announcements_api(request):
    instructor_announcements = CourseAnnouncement.objects.filter(
        course__instructor=request.user
    )
    student_announcements = CourseAnnouncement.objects.filter(
        course__enrolled_students=request.user
    )
    
    return Response({
        "instructor_announcements": CourseAnnouncementSerializer(instructor_announcements, many=True).data,
        "student_announcements": CourseAnnouncementSerializer(student_announcements, many=True).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_announcement_api(request):
    if not request.user.is_edu_instructor:
        return Response(
            {"error": "You are not allowed to perform this action."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    course_slug = request.data.get("course")
    title = request.data.get("title")
    content = request.data.get("content")

    if not title or not content or not course_slug:
        return Response(
            {"error": "All fields are required to add an announcement."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        course = get_object_or_404(Course, slug=course_slug, instructor=request.user)
        announcement = CourseAnnouncement.objects.create(course=course, title=title, content=content)
        
        return Response({
            "success": True,
            "message": "Announcement added successfully.",
            "announcement": CourseAnnouncementSerializer(announcement).data
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_announcement_api(request, id):
    announcement = get_object_or_404(CourseAnnouncement, id=id)
    
    if request.user != announcement.course.instructor:
        return Response(
            {"error": "You are not allowed to perform this action."}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    announcement.delete()
    return Response({
        "success": True,
        "message": "Announcement deleted successfully."
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def earnings_api(request):
    if not request.user.is_edu_instructor:
        return Response(
            {"error": "You are not an authorized person to access this resource!"}, 
            status=status.HTTP_403_FORBIDDEN
        )

    instructor = request.user
    courses = Course.objects.filter(
        instructor=instructor, is_published=True, best_selling=True
    )

    return Response({
        "instructor": {
            "id": instructor.id,
            "username": instructor.username,
            "name": instructor.name,
            "edu_total_earnings": instructor.edu_total_earnings,
            "available_earnings": instructor.available_earnings
        },
        "courses": CourseSerializer(courses, many=True).data
    })

# ------------------- Email Notifications -------------------
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def send_email(to_email, subject, html_content):
    message = Mail(
        from_email="support@fireprenair.com",
        to_emails=to_email,
        subject=subject,
        html_content=html_content,
    )
    try:
        sg = SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        sg.send(message)
    except Exception as e:
        print(f"Error sending email: {e}")


# <---------------------------------------- Course Payments -------------------------------->


stripe.api_key = settings.STRIPE_SECRET_KEY
from decimal import Decimal
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def course_payment_view_api(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)

    mode = 'subscription' if course.monthly_subscription else 'payment'
    c_price = course.course_price()
    price = c_price + (c_price * Decimal('0.05'))
    price_data = {
        "currency": "usd",
        "product_data": {
            "name": course.title,
            "description": f"Total Price: ${price:.2f} (5% processing fee included)",
        },
        "unit_amount": int(price * 100),
        "recurring": {"interval": "month"} if mode == "subscription" else None,
    }

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": price_data,
                    "quantity": 1,
                }
            ],
            mode=mode,
            success_url=request.build_absolute_uri(
                reverse("course_detail", kwargs={"slug": course.slug})
            ),
            cancel_url=request.build_absolute_uri(
                reverse("course_detail", kwargs={"slug": course.slug})
            ),
            metadata={"course_slug": course.slug, "user_id": request.user.id},
        )
        return Response({"checkout_url": checkout_session.url})

    except stripe.error.StripeError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from decimal import Decimal
import stripe
import paypalrestsdk
from paypalrestsdk import Payment
from django.conf import settings



@csrf_exempt
@api_view(['POST'])
def stripe_webhook_api(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET_COURSE
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return Response({"status": "Invalid payload or signature"}, status=status.HTTP_400_BAD_REQUEST)

    # on success of payment
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        course_slug = session["metadata"]["course_slug"]
        user_id = session["metadata"]["user_id"]
        course = Course.objects.get(slug=course_slug)
        user = User.objects.get(id=user_id)

        enrollment, created = StudentEnrollment.objects.get_or_create(
            user=user, course=course
        )
        course.enrolled_students.add(user)
        course.save()
        c_price = course.course_price()

        instructor = course.instructor
        Notification.objects.create(
            user=instructor,
            message=f"{user.username} has enrolled in your course {course.title}",
            app_name="eduprenair",
        )
        if session["mode"] == "subscription":
            # for subscription
            enrollment.subscription_id = session["subscription"]
            enrollment.save()
            course_price = c_price - Decimal('0.20') * c_price
            instructor.edu_total_earnings += course_price
            instructor.total_earnings += course_price
            instructor.available_earnings += course_price
            instructor.save()

        else:
            # for one time payment
            course_price = c_price - Decimal('0.20') * c_price
            instructor.edu_total_earnings += course_price
            instructor.total_earnings += course_price
            instructor.available_earnings += course_price
            instructor.save()

        buyer_url = request.build_absolute_uri(reverse("edu_student_dashboard"))

         # Send email notification to the buyer (student)
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
                            <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🎉 Enrollment Confirmed! Welcome to {course.title}</h2>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {user.username},</p>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">
                                Thank you for enrolling in <strong>{course.title}</strong> on <strong>FirePrenair</strong>! 🎉 Your enrollment has been successfully processed.
                            </p>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Course Details:</strong></p>
                            <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                                <li style="margin-bottom: 10px;"><strong>Course Title:</strong> {course.title}</li>
                                <li style="margin-bottom: 10px;"><strong>Total Amount:</strong> ${course.course_price()}</li>
                            </ul>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">You can start learning right away! Access your course from the link below:</p>
                            <p style="text-align: center; margin: 20px 0;">
                                <a href="{buyer_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">Start Learning</a>
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

        send_email(
                    user.email,
                    f"🎉 Enrollment Confirmed! Welcome to {course.title}",
                    buyer_email_content,
                )
        seller_url = request.build_absolute_uri(reverse("edu_instructor_dashboard"))

                # Send email notification to the seller
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
                        <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🎉 Congratulations! A Student Enrolled in Your Course</h2>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {course.instructor.username},</p>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">
                            We are excited to inform you that a student { user.username } has successfully enrolled in your course <strong>{course.title}</strong> on <strong>FirePrenair</strong>! 🎉
                        </p>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Enrollment Details:</strong></p>
                        <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                            <li style="margin-bottom: 10px;"><strong>Course Title:</strong> {course.title}</li>
                            <li style="margin-bottom: 10px;"><strong>Total Amount:</strong> ${course.course_price()}</li>
                        </ul>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">You can view the details of this enrollment and manage your courses from your instructor dashboard:</p>
                        <p style="text-align: center; margin: 20px 0;">
                            <a href="{seller_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">View Dashboard</a>
                        </p>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">Need help? Our support team is always here for you.</p>
                    </div>

                    <!-- Footer -->
                    <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                        <p style="margin: 0; font-size: 14px;">Thank you for being a valued instructor on FirePrenair! 🚀</p>
                    </div>
                </div>
            </body>
            </html>
        """

        try:
            send_email(
                    instructor.email,
                    f"🎉 Congratulations! A Student Enrolled in Your Course",
                    seller_email_content,
                )
            print(
                    f"Email sent successfully to user:{user.email} and instructor:{instructor.email}"
                )
        except Exception as e:
            print(f"Error sending email: {e}")

    # charge monthly
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        subscription_id = invoice['subscription']
        inv_price = invoice['amount_paid'] / 100

        enrollment = StudentEnrollment.objects.filter(
            subscription_id=subscription_id
        ).first()
        if enrollment:
            course = enrollment.course
            instructor = course.instructor
            user = enrollment.user
            course_price = inv_price - Decimal('0.20') * inv_price
            instructor.edu_total_earnings += course_price
            instructor.total_earnings += course_price
            instructor.available_earnings += course_price
            instructor.save()
            Notification.objects.create(
                user=instructor,
                message=f"{course.title} has been charged for monthly subscription",
                app_name="eduprenair",
            )

            buyer_url = request.build_absolute_uri(reverse("edu_student_dashboard"))

            # Send email notification to the buyer (student)
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
                                                    <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🎉 Enrollment renewed! Welcome to {course.title}</h2>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {user.username},</p>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                                                        Thank you for enrolling in <strong>{course.title}</strong> on <strong>FirePrenair</strong>! 🎉 Your enrollment has been successfully renewed!.
                                                    </p>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Course Details:</strong></p>
                                                    <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                                                        <li style="margin-bottom: 10px;"><strong>Course Title:</strong> {course.title}</li>
                                                        <li style="margin-bottom: 10px;"><strong>Total Amount:</strong> ${inv_price}</li>
                                                    </ul>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">You can continue learning right away! Access your course from the link below:</p>
                                                    <p style="text-align: center; margin: 20px 0;">
                                                        <a href="{buyer_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">Start Learning</a>
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

            send_email(
                    user.email,
                    f"🎉 Enrollment renewed! Welcome to {course.title}",
                    buyer_email_content,
                )
            seller_url = request.build_absolute_uri(reverse("edu_instructor_dashboard"))

            # Send email notification to the seller
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
                                                    <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🎉 Congratulations! A Student Enrollement renewed in Your Course</h2>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {course.instructor.username},</p>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                                                        We are excited to inform you that a student { user.username } has successfully renewed thier enrollment in your course <strong>{course.title}</strong> on <strong>FirePrenair</strong>! 🎉
                                                    </p>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Enrollment Details:</strong></p>
                                                    <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                                                        <li style="margin-bottom: 10px;"><strong>Course Title:</strong> {course.title}</li>
                                                        <li style="margin-bottom: 10px;"><strong>Total Amount:</strong> ${inv_price}</li>
                                                    </ul>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">You can view the details of this enrollment and manage your courses from your instructor dashboard:</p>
                                                    <p style="text-align: center; margin: 20px 0;">
                                                        <a href="{seller_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">View Dashboard</a>
                                                    </p>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Need help? Our support team is always here for you.</p>
                                                </div>

                                                <!-- Footer -->
                                                <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                                                    <p style="margin: 0; font-size: 14px;">Thank you for being a valued instructor on FirePrenair! 🚀</p>
                                                </div>
                                            </div>
                                        </body>
                                        </html>
                                    """

            try:
                send_email(
                        instructor.email,
                        f"🎉 Congratulations! A Student Enrollment renewed in Your Course",
                        seller_email_content,
                    )
                print(
                    f"Email sent successfully to instructor: {course.instructor.email}"
                )
            except Exception as e:
                print(f"Error sending email: {e}")

    return Response({"status": "success"}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def paypal_course_checkout_api(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    
    # Check if course is free
    if course.is_free:
        return Response(
            {"error": "This course is free to enroll"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check for monthly subscription
    if course.monthly_subscription:
        return Response(
            {"error": "Pay with Stripe for monthly subscription"},
            status=status.HTTP_400_BAD_REQUEST
        )
        
    user = request.user
    c_price = course.course_price()
    price = c_price + (c_price * Decimal('0.05'))

    success_url = request.build_absolute_uri(
        reverse("paypal_course_success", kwargs={"course_slug": course_slug})
    )
    cancel_url = request.build_absolute_uri(reverse("paypal_cancel"))

    payment = Payment(
        {
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "redirect_urls": {"return_url": success_url, "cancel_url": cancel_url},
            "transactions": [
                {
                    "item_list": {
                        "items": [
                            {
                                "name": f"Course: {course.title}",
                                "sku": f"{course.slug}",
                                "price": f"{price:.2f}",
                                "currency": "USD",
                                "quantity": 1,
                            }
                        ]
                    },
                    "amount": {"total": f"{price:.2f}", "currency": "USD"},
                    "description": f"Purchase of {course.title} with a total price of ${price:.2f} (5% processing fee included).",
                }
            ],
        }
    )

    # Create the payment and redirect the user to PayPal approval URL
    if payment.create():
        approval_url = next((link.href for link in payment.links if link.rel == "approval_url"), None)
        if approval_url:
            return Response({"redirect_url": approval_url}, status=status.HTTP_200_OK)
    
    return Response(
        {"error": "Failed to create PayPal payment"},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def paypal_course_success_api(request, course_slug):
    payment_id = request.query_params.get("paymentId")
    payer_id = request.query_params.get("PayerID")

    if not payment_id or not payer_id:
        return Response(
            {"error": "Invalid PayPal payment details"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    payment = Payment.find(payment_id)

    if payment.execute({"payer_id": payer_id}):
        course = get_object_or_404(Course, slug=course_slug)
        user = request.user

        enrollment, created = StudentEnrollment.objects.get_or_create(
            user=user, course=course
        )
        course.enrolled_students.add(user)
        course.save()

        instructor = course.instructor
        c_price = course.course_price()
        course_price = c_price - Decimal('0.20') * c_price
        instructor.edu_total_earnings += course_price
        instructor.total_earnings += course_price
        instructor.available_earnings += course_price
        instructor.save()

        Notification.objects.create(
            user=instructor, 
            message=f"{user.username} has enrolled in your course {course.title}.", 
            app_name="eduprenair"
        )

        buyer_url = request.build_absolute_uri(reverse("edu_student_dashboard"))

        # Send email notification to the buyer (student)
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
                    <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🎉 Enrollment Confirmed! Welcome to {course.title}</h2>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {user.username},</p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                        Thank you for enrolling in <strong>{course.title}</strong> on <strong>FirePrenair</strong>! 🎉 Your enrollment has been successfully processed.
                    </p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Course Details:</strong></p>
                    <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                        <li style="margin-bottom: 10px;"><strong>Course Title:</strong> {course.title}</li>
                        <li style="margin-bottom: 10px;"><strong>Total Amount:</strong> ${c_price}</li>
                    </ul>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">You can start learning right away! Access your course from the link below:</p>
                    <p style="text-align: center; margin: 20px 0;">
                        <a href="{buyer_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">Start Learning</a>
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

        send_email(
            user.email,
            f"🎉 Enrollment Confirmed! Welcome to {course.title}",
            buyer_email_content,
        )
        seller_url = request.build_absolute_uri(reverse("edu_instructor_dashboard"))

        # Send email notification to the seller
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
                        <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🎉 Congratulations! A Student Enrolled in Your Course</h2>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {course.instructor.username},</p>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">
                            We are excited to inform you that a student { user.username } has successfully enrolled in your course <strong>{course.title}</strong> on <strong>FirePrenair</strong>! 🎉
                        </p>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Enrollment Details:</strong></p>
                        <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                            <li style="margin-bottom: 10px;"><strong>Course Title:</strong> {course.title}</li>
                            <li style="margin-bottom: 10px;"><strong>Total Amount:</strong> ${c_price}</li>
                        </ul>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">You can view the details of this enrollment and manage your courses from your instructor dashboard:</p>
                        <p style="text-align: center; margin: 20px 0;">
                            <a href="{seller_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">View Dashboard</a>
                        </p>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">Need help? Our support team is always here for you.</p>
                    </div>

                    <!-- Footer -->
                    <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                        <p style="margin: 0; font-size: 14px;">Thank you for being a valued instructor on FirePrenair! 🚀</p>
                    </div>
                </div>
            </body>
            </html>
        """

        try:
            send_email(
                instructor.email,
                f"🎉 Congratulations! A Student Enrolled in Your Course",
                seller_email_content,
            )
            print(
                f"Email sent successfully to user:{user.email} and instructor:{instructor.email}"
            )
        except Exception as e:
            print(f"Error sending email: {e}")

        return Response(
            {"success": True, "message": "Successfully enrolled in course"},
            status=status.HTTP_200_OK
        )
    else:
        return Response(
            {"error": "PayPal payment execution failed"},
            status=status.HTTP_400_BAD_REQUEST
        )


# def get_subcategories(request, category_id):
#     level_2_categories = CourseCategory.objects.filter(parent_id=category_id)

#     data = []
#     for category in level_2_categories:
#         children = category.courses_subcategories.all()
#         child_data = [
#             {"id": child.id, "name": child.name, "url": f"#"} for child in children
#         ]
#         data.append({"id": category.id, "name": category.name, "children": child_data})

#     return JsonResponse({"level_2_categories": data})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def become_instructor_api(request):
    user = request.user

    if user.is_edu_instructor:
        return Response(
            {"detail": "You are already an instructor."},
            status=status.HTTP_400_BAD_REQUEST
        )

    name = request.data.get("name")
    bio = request.data.get("edu_bio")

    if not name or not bio:
        return Response(
            {"detail": "Name and bio are required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    user.name = name
    user.edu_bio = bio
    user.is_edu_instructor = True
    user.save()

    return Response(
        {"detail": "Congratulations! Your instructor account has been approved."},
        status=status.HTTP_200_OK
    )