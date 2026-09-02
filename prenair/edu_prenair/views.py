from django.shortcuts import render, redirect, get_object_or_404
from django.utils.text import slugify
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import *
from profiles.models import *
import stripe
from django.views import View
from django.conf import settings
from django.urls import reverse
from .decorators import *
from django.utils.decorators import method_decorator
from django.db.models import Count
import uuid
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from PIL import Image, ImageDraw, ImageFont
from django.http import HttpResponse
import io
from io import BytesIO
import requests
from django.core.exceptions import BadRequest
from elevenlabs import ElevenLabs
# ai
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.safestring import mark_safe
import markdown
from groq import Groq
from django.views.decorators.http import require_POST
from openai import OpenAI
# client = OpenAI(api_key=settings.OPENAI_API_KEY)
client = Groq(api_key=settings.GROQ_API_KEY)


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
def eduprenair_chatbot_view(request):
    if request.method == "POST":
        user_message = request.POST.get("message", "").lower()

        # Predefined responses for quick replies
        predefined_responses = {
            "name": "I am your customer support assistant, here to help you with any questions about Eduprenair.",
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

        return JsonResponse({"message": bot_reply_html})

    return JsonResponse({"message": "Only POST requests are allowed."}, status=400)


# Create your views here.


def edu_home(request):
    best_courses = Course.objects.filter(is_published=True, best_selling=True)
    best_instructors = CustomUser.objects.filter(
        is_edu_instructor=True, featured_instructor=True
    )
    course_categories = CourseCategory.objects.filter(is_featured=True)
    context = {
        "best_courses": best_courses,
        "best_instructors": best_instructors,
        "course_categories": course_categories,
    }

    return render(request, "edu_prenair/edu_home.html", context)


@authenticated_user_required
def edu_profile(request, slug):
    profile = get_object_or_404(CustomUser, slug=slug)
    context = {
        "profile": profile,
    }
    return render(request, "edu_prenair/edu_profile.html", context)


@authenticated_user_required
def edu_settings(request):
    if request.method == "POST":
        user = request.user

        name = request.POST.get("name")
        bio = request.POST.get("bio")
        profile_pic = request.FILES.get("profile_pic")

        user.name = name
        user.edu_bio = bio

        if profile_pic:
            user.profile_pic = profile_pic
        user.save()

        messages.success(request, "Profile updated successfully.")

        return redirect("edu_settings")

    return render(request, "edu_prenair/edu_settings.html")


def instructors(request):
    search_query = request.GET.get("search", "").strip()
    category_id = request.GET.get("category", "").strip()
    selected_categories = request.GET.getlist("category")
    selected_instructors = request.GET.getlist("instructor")

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

    paginator = Paginator(edu_instructors, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    # Annotate instructors with course counts
    instructors = CustomUser.objects.filter(is_edu_instructor=True).annotate(
        course_count=Count("course")
    )

    context = {
        "page_obj": page_obj,
        "categories": categories,
        "instructors": instructors,
    }
    return render(request, "edu_prenair/instructors.html", context)


@authenticated_user_required
def instructor_dashboard(request):
    if request.user.is_edu_instructor == False:
        return redirect("edu_student_dashboard")
    courses_teaching = Course.objects.filter(
        instructor=request.user, is_published=True
    ).order_by("-created_at")
    students = CustomUser.objects.filter(enrolled_courses__in=courses_teaching).exclude(id=request.user.id)
    enrolled_courses = StudentEnrollment.objects.filter(user=request.user).exclude(course__instructor=request.user)
    completed_courses = enrolled_courses.filter(is_completed=True)
    context = {
        "courses_teaching": courses_teaching,
        "students": students,
        "enrolled_courses": enrolled_courses,
        "completed_courses": completed_courses,
    }
    return render(request, "edu_prenair/instructor_dashboard.html", context)


@authenticated_user_required
def edu_student_dashboard(request):
    if request.user.is_edu_instructor:
        return redirect("edu_instructor_dashboard")

    enrolled_courses = StudentEnrollment.objects.filter(user=request.user)
    completed_courses = enrolled_courses.filter(is_completed=True)
    context = {
        "enrolled_courses": enrolled_courses,
        "completed_courses": completed_courses,
    }
    return render(request, "edu_prenair/student_dashboard.html", context)


def all_courses(request):
    search_query = request.GET.get("search", "").strip()
    category_ids = [cid for cid in request.GET.getlist("category") if cid.isdigit()]
    price_min = request.GET.get("price_min", "").strip()
    price_max = request.GET.get("price_max", "").strip()
    sort_by = request.GET.get("sort_by", "relevance")  
    level = request.GET.get("level", "").strip()  

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

    price_filter = request.GET.get("price_filter", "")
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

    paginator = Paginator(courses, 12) 
    page = request.GET.get("page")
    try:
        courses = paginator.page(page)
    except PageNotAnInteger:
        courses = paginator.page(1)
    except EmptyPage:
        courses = paginator.page(paginator.num_pages)

    context = {
        "courses": courses,
        "user": request.user,
        "categories": top_level_categories,
        "search_query": search_query,
        "price_min": price_min,
        "price_max": price_max,
        "sort_by": sort_by,
        "level": level,
    }
    return render(request, "edu_prenair/all_courses.html", context)


@authenticated_user_required
def add_course(request):
    categories = CourseCategory.objects.all()

    if request.method == "POST":
        title = request.POST.get("title")
        category_id = request.POST.get("category")
        category = CourseCategory.objects.get(id=category_id)
        short_description = request.POST.get("short_description")
        description = request.POST.get("description")
        outcome = request.POST.get("outcome")
        requirements = request.POST.get("requirements")
        language = request.POST.get("language")
        price = request.POST.get("price")
        is_free = bool(request.POST.get("is_free"))
        level = request.POST.get("level")
        duration = request.POST.get("duration")
        thumbnail = request.FILES.get("thumbnail")

        request.user.is_edu_instructor = True
        request.user.save()

        # Create course
        try:
            course = Course.objects.create(
                title=title,
                instructor=request.user,
                category=category,
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
            messages.success(request, "Course created successfully! Awaiting approval.")
            return redirect("edu_instructor_dashboard")
        except Exception as e:
            messages.error(request, f"Error creating course: {e}")
            return redirect("edu_add_course")

    context = {
        "categories": categories,
    }
    return render(request, "edu_prenair/add_course.html", context)


@authenticated_user_required
def my_courses(request):
    drafts = Course.objects.filter(instructor=request.user, submit_for_approval=False)
    courses = Course.objects.filter(instructor=request.user, is_published=True)
    pendings = Course.objects.filter(
        instructor=request.user, submit_for_approval=True, is_published=False
    )
    context = {
        "drafts": drafts,
        "courses": courses,
        "pendings": pendings,
    }
    return render(request, "edu_prenair/my_courses.html", context)


@authenticated_user_required
def submit_for_approval(request, slug):
    course = get_object_or_404(Course, slug=slug, instructor=request.user)

    if course.submit_for_approval:
        messages.info(request, "This course has already been submitted for approval.")
    else:
        course.submit_for_approval = True
        course.save()
        messages.success(request, "Your course has been submitted for approval.")
    return redirect("edu_my_courses")


@authenticated_user_required
def add_module(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug, instructor=request.user)
    modules = Module.objects.filter(course=course)

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        order = request.POST.get("order")

        if title and description and order:
            module = Module.objects.create(
                course=course, title=title, description=description, order=order
            )
            messages.success(
                request, f'Module "{module.title}" has been added successfully!'
            )
            return redirect("add_module", course_slug=course.slug)
        else:
            messages.error(request, "All fields are required to add a module.")

    return render(
        request, "edu_prenair/add_module.html", {"course": course, "modules": modules}
    )


@authenticated_user_required
def add_lesson(request, module_id):
    module = get_object_or_404(Module, id=module_id, course__instructor=request.user)

    if request.method == "POST":
        title = request.POST.get("title")
        video = request.FILES.get("video")
        order = request.POST.get("order")

        if title and video and order:
            lesson = Lesson.objects.create(
                module=module,
                title=title,
                video=video,
                order=order,
                slug=f"{slugify(title)}-{str(uuid.uuid4().int)[:6]}",
            )
            messages.success(
                request, f'Lesson "{lesson.title}" has been added successfully!'
            )
            return redirect("add_module", course_slug=module.course.slug)
        else:
            messages.error(request, "All fields are required to add a lesson.")

    return render(request, "edu_prenair/add_module.html", {"module": module})


@authenticated_user_required
def mark_lesson_completed(request, lesson_slug, course_slug):
    if request.user.is_authenticated:
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

        return JsonResponse(
            {
                "message": "Lesson marked as completed",
                "progress": enrollment.progress,
                "completed_lessons": completed_lessons.count(),
                "is_completed": enrollment.is_completed,
                "total_lessons": total_lessons,
            }
        )
    else:
        return JsonResponse({"message": "User not authenticated"}, status=403)


@authenticated_user_required
def delete_course(request, slug):
    course = get_object_or_404(Course, slug=slug, instructor=request.user)
    course.delete()
    messages.success(request, "Course deleted successfully.")
    return redirect("edu_my_courses")


def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)

    sub_description_html = markdown.markdown(course.description[0:100] + ". . . . .")
    description_html = markdown.markdown(course.description)

    is_enrolled = (request.user.is_authenticated and StudentEnrollment.objects.filter(user=request.user, course=course).first())
    has_rated = (request.user.is_authenticated and CourseRating.objects.filter(user=request.user, course=course).exists())

    prev_course = Course.objects.filter(created_at__lt=course.created_at).order_by('-created_at').first()
    next_course = Course.objects.filter(created_at__gt=course.created_at).order_by('created_at').first()

    context = {
        "course": course,
        "is_enrolled": is_enrolled,
        "prev_course": prev_course,
        "next_course": next_course,
        "has_rated": has_rated,
        "modules": course.modules.all(),
        "sub_description_html": sub_description_html,
        "description_html": description_html,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        template = "edu_prenair/partials/course_modal_content.html"
    else:
        template = "edu_prenair/course_detail.html"
    return render(request, template, context)


@login_required
def course_content(request, slug):
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
    return render(request, "edu_prenair/course_content.html", context)


@login_required
def view_lesson(request, lesson_slug):    
    lesson = get_object_or_404(Lesson, slug=lesson_slug)
    course = lesson.module.course
    
    if not course.is_user_enrolled(request.user):
        messages.error(request, "You must be enrolled in this course to access the materials.")
        return redirect("course_detail", slug=course.slug)
    
    if lesson.is_pdf():
        if settings.USE_S3_STORAGE:
            pdf_url = f"https://fireprenair.s3.amazonaws.com/{lesson.video}"
        else:
            pdf_url = request.build_absolute_uri(lesson.video.url)

        return render(request, "edu_prenair/flipbook.html", {"pdf_url": pdf_url, "material": lesson})
    
    data = {
        'type': 'pdf' if lesson.is_pdf() else 'video',
        'url': lesson.video.url if lesson.video else None,
        'title': lesson.title,
        'description': lesson.description
    }
    return JsonResponse(data)


@require_POST
@login_required
def generate_speech(request):
    text = request.POST.get('text', '')
    gender = request.POST.get('gender', 'male')
    if not text:
        return JsonResponse({'error': 'No text provided'}, status=400)

    if gender == 'female':
        voice_id = "21m00Tcm4TlvDq8ikWAM"
    else:
        voice_id = "JBFqnCBsd6RMkjVDRZzb"

    try:
        client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
        audio = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        return HttpResponse(audio, content_type='audio/mpeg')
        
    except Exception as e:
        print(e)
        return JsonResponse({'error': str(e)}, status=500)


# ------------------- Quiz -------------------
@require_POST
def generate_quiz(request, course_slug):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        course = Course.objects.get(slug=course_slug)
    except Course.DoesNotExist:
        return JsonResponse({'error': 'Course not found'}, status=404)
    
    # Get user prompt from request
    data = json.loads(request.body)
    user_prompt = data.get('prompt', '')
    
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
        
        return JsonResponse({
            'success': True,
            'quiz_id': quiz.id,
            'title': quiz.title,
            'description': quiz.description,
            'num_questions': quiz.questions.count()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Check if user is enrolled in the course
    if not request.user.enrolled_courses.filter(slug=quiz.course.slug).exists():
        messages.error(request, "You must be enrolled in this course to take the quiz")
        return redirect('course_detail', slug=quiz.course.slug)
    
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
            selected_answer = request.POST.get(f'question_{question.id}')
            if selected_answer:
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
        
        messages.success(request, f"Quiz completed! Score: {attempt.score:.1f}%")
        return redirect('quiz_results', attempt_id=attempt.id)
    
    return render(request, 'edu_prenair/take_quiz.html', {
        'quiz': quiz,
        'attempt': attempt,
        'questions': quiz.questions.all().order_by('order')
    })

def quiz_results(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
    return render(request, 'edu_prenair/quiz_results.html', {
        'attempt': attempt,
        'quiz': attempt.quiz,
        'course': attempt.quiz.course
    })

@login_required
def get_certificate(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    enrollment = get_object_or_404(StudentEnrollment, user=request.user, course=course)

    if not enrollment.is_completed:
        messages.error(request, "You must complete the course to receive a certificate.")
        return redirect("course_content", slug=course_slug)

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

        response = HttpResponse(buffer, content_type="image/png")
        response["Content-Disposition"] = (
            f'attachment; filename="{course_slug}_certificate.png"'
        )
        return response
    except IOError as e:
        raise BadRequest(f"Error processing image: {str(e)}")


@login_required
@authenticated_user_required
def post_review(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if request.method == "POST":
        rating = int(request.POST.get("rating"))
        review_text = request.POST.get("review_text", "").strip()

        if not rating and review_text:
            messages.error(request, "Please provide a rating and review text.")
            return redirect("course_detail", slug=slug)

        CourseRating.objects.create(
            user=request.user,
            course=course,
            rating=rating,
            review=review_text,
        )
        messages.success(request, "Review posted successfully!")
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

        return redirect("course_detail", slug=slug)
    

@require_POST
def analyze_review(request):
    try:
        data = json.loads(request.body)
        review_text = data.get('review', '')
        target_slug = data.get('target_slug', '')  
        is_work_review = data.get("work_review", False) 
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    if request.user.slug != target_slug:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

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
        return JsonResponse({'analysis': analysis})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@authenticated_user_required
def reviews(request):
    reviews_given = CourseRating.objects.filter(user=request.user).exclude(
        course__instructor=request.user
    )
    reviews_received = CourseRating.objects.filter(course__instructor=request.user)

    context = {
        "reviews_given": reviews_given,
        "reviews_received": reviews_received,
    }
    return render(request, "edu_prenair/reviews.html", context)


@authenticated_user_required
def student_courses(request):
    enrolled_courses = StudentEnrollment.objects.filter(user=request.user).exclude(course__instructor=request.user)
    active_courses = enrolled_courses.filter(is_completed=False)
    completed_courses = enrolled_courses.filter(is_completed=True)
    context = {
        "enrolled_courses": enrolled_courses,
        "active_courses": active_courses,
        "completed_courses": completed_courses,
    }
    return render(request, "edu_prenair/enrolled_courses.html", context)


@authenticated_user_required
def add_to_wishlist(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if request.user.is_authenticated:
        CourseWishlist.objects.get_or_create(user=request.user, course=course)
        messages.success(
            request, f'Course "{course.title}" has been added to your wishlist.'
        )
    else:
        messages.error(
            request, "You must be logged in to add a course to your wishlist."
        )
    return redirect("wishlist")


@authenticated_user_required
def remove_from_wishlist(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if request.user.is_authenticated:
        CourseWishlist.objects.filter(user=request.user, course=course).delete()
        messages.success(
            request, f'Course "{course.title}" has been removed from your wishlist.'
        )
    else:
        messages.error(
            request, "You must be logged in to remove a course from your wishlist."
        )
    return redirect("wishlist")


@authenticated_user_required
def wishlists(request):
    wishlists = CourseWishlist.objects.filter(user=request.user)
    context = {
        "wishlists": wishlists,
    }
    return render(request, "edu_prenair/wishlists.html", context)


@authenticated_user_required
def order_history(request):
    today = timezone.now()
    enrolls_today = StudentEnrollment.objects.filter(enrolled_date__date=today.date())
    enrolls_month = StudentEnrollment.objects.filter(
        enrolled_date__year=today.year, enrolled_date__month=today.month
    )
    enrolls_year = StudentEnrollment.objects.filter(enrolled_date__year=today.year)

    context = {
        "enrolls_today": enrolls_today,
        "enrolls_month": enrolls_month,
        "enrolls_year": enrolls_year,
    }

    return render(request, "edu_prenair/order_history.html", context)


@authenticated_user_required
def get_notifications(request):
    return render(request, "edu_prenair/notifications.html")


@authenticated_user_required
def announcements(request):
    instructor_announcements = CourseAnnouncement.objects.filter(
        course__instructor=request.user
    )
    student_announcements = CourseAnnouncement.objects.filter(
        course__enrolled_students=request.user
    )
    context = {
        "instructor_announcements": instructor_announcements,
        "student_announcements": student_announcements,
    }

    return render(request, "edu_prenair/announcements.html", context)


@authenticated_user_required
def add_announcement(request):
    if not request.user.is_edu_instructor:
        messages.warning(request, "You are not allowed to perform this action.")
        return redirect("edu_announcements")

    instructor_courses = Course.objects.filter(
        instructor=request.user, is_published=True
    )

    if request.method == "POST":
        course_slug = request.POST.get("course")
        title = request.POST.get("title")
        content = request.POST.get("content")

        course = get_object_or_404(Course, slug=course_slug, instructor=request.user)

        if not title or not content or not course_slug:
            messages.error(request, "All fields are required to add an announcement.")
            return redirect("add_edu_announcement")

        CourseAnnouncement.objects.create(course=course, title=title, content=content)
        messages.success(request, "Announcement added successfully.")
        return redirect("edu_announcements")

    context = {"instructor_courses": instructor_courses}
    return render(request, "edu_prenair/add_announcement.html", context)


@authenticated_user_required
def delete_announcement(request, id):
    if request.user != CourseAnnouncement.objects.get(id=id).course.instructor:
        messages.warning(request, "You are not allowed to perform this action.")
        return redirect("edu_announcements")
    announcement = get_object_or_404(CourseAnnouncement, id=id)
    announcement.delete()
    messages.success(request, "Announcement deleted successfully.")
    return redirect("edu_announcements")


@authenticated_user_required
def earnings(request):
    if not request.user.is_edu_instructor:
        messages.warning(request, "You are not Authorized person to Access this page!")
        return redirect("edu_student_dashboard")

    instructor = request.user
    courses = Course.objects.filter(
        instructor=instructor, is_published=True, best_selling=True
    )

    context = {"instructor": instructor, "courses": courses}

    return render(request, "edu_prenair/earnings.html", context)


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


def course_payment_view(request, course_slug):
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
        return redirect(checkout_session.url, code=303)

    except stripe.error.StripeError as e:
        return render(request, "profiles/error.html", {"error": str(e)})


stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET_COURSE
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return JsonResponse({"status": "Invalid payload or signature"}, status=400)

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

    return JsonResponse({"status": "success"}, status=200)


import paypalrestsdk
from paypalrestsdk import Payment


@login_required
def paypal_course_checkout(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    if course.is_free:
        messages.warning(request, "This course is free to enroll.")
        return redirect("course_detail", slug=course_slug)

    if course.monthly_subscription:
        messages.warning(request, "Pay with Stripe for monthly subscription.")
        return redirect("course_detail", slug=course_slug)
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
        for link in payment.links:
            if link.rel == "approval_url":
                return redirect(link.href)
    else:
        return render(
            request,
            "profiles/error.html",
            {"error": "Failed to create PayPal payment."},
        )


@login_required
def paypal_course_success(request, course_slug):
    payment_id = request.GET.get("paymentId")
    payer_id = request.GET.get("PayerID")

    if not payment_id or not payer_id:
        return render(
            request, "profiles/error.html", {"error": "Invalid PayPal payment details."}
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

        Notification.objects.create(user=instructor, message=f"{user.username} has enrolled in your course {course.title}.", app_name="eduprenair")

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

        return redirect('course_detail', slug=course.slug)
    else:
        return render(request, "profiles/error.html", {"error": "PayPal payment execution failed."})





def get_subcategories(request, category_id):
    level_2_categories = CourseCategory.objects.filter(parent_id=category_id)

    data = []
    for category in level_2_categories:
        children = category.courses_subcategories.all()
        child_data = [
            {"id": child.id, "name": child.name, "url": f"#"} for child in children
        ]
        data.append({"id": category.id, "name": category.name, "children": child_data})

    return JsonResponse({"level_2_categories": data})


@login_required
def become_intructor(request):
    if request.user.is_edu_instructor:
        messages.warning(request, "You are already an Intructor")
        return redirect("dashboard_eduprenair")

    if request.method == "POST":
        name = request.POST.get("name")
        bio = request.POST.get("edu_bio")

        user = request.user
        user.name = name
        user.edu_bio = bio
        user.is_edu_instructor = True
        user.save()
        messages.success(
            request, "Congragulations, Your Instrcutor Account has been approved"
        )
        return redirect("course_create_eduprenair")

    return render(request, "edu_prenair/become_instructor.html")
