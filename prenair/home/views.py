from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from .models import Category as BlogCategory
from django.core.exceptions import ValidationError
from django.contrib import messages
from edu_prenair.models import *
from digi_prenair.models import *
from work_prenair.models import Category as WorkCategory, Gig
from commu_prenair.models import Groupcategory, Group, Post
from django.conf import settings
from datetime import timedelta
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# ai 
import json
from django.utils.translation import gettext as _
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import markdown
import time 
from openai import OpenAI
client = OpenAI()

@csrf_exempt
def fireprenair_chat_bot(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_input = data.get("message")
        if not user_input:
            return JsonResponse({"error": "No message provided"}, status=400)

        thread_id = get_or_create_thread(request.user)
        assistant_id = "asst_HhwdB6czd6xyFk9JW1KMlZcT"

        # 1. Send user message
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_input
        )

        # 2. Run assistant
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )

        # 3. Wait until done
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            if run_status.status == "completed":
                break
            time.sleep(1)

        # 4. Get assistant response
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        reply = messages.data[0].content[0].text.value
        # apply markdown formatting
        markdown_reply = markdown.markdown(reply, extensions=['fenced_code', 'codehilite'])
        return JsonResponse({"message": markdown_reply})
    return JsonResponse({"error": "Invalid request"}, status=405)


def get_or_create_thread(user):
    thread_obj = ChatThread.objects.filter(user=user).first()
    if thread_obj:
        return thread_obj.thread_id
    response = client.beta.threads.create()
    ChatThread.objects.create(user=user, thread_id=response.id)
    return response.id

@csrf_exempt
def delete_chat_thread(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            return JsonResponse({"status": "user not authenticated"}, status=401)
            
        thread_obj = ChatThread.objects.filter(user=request.user).first()
        if thread_obj:
            try:
                client.beta.threads.delete(thread_obj.thread_id)
                thread_obj.delete()
                return JsonResponse({"status": "thread deleted"})
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)
        return JsonResponse({"status": "no thread found"})
    return JsonResponse({"error": "Invalid request"}, status=405)

from dashboard.decorators import get_top_digi_products, get_top_sellers
from profiles.models import CustomUser
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

def get_homepage_context(request):
    best_courses = Course.objects.filter(is_published=True, best_selling=True)[:3]
    best_products = Product.objects.filter(is_featured=True)
    best_services = Gig.objects.filter(featured=True)
    best_groups = Group.objects.filter(is_featured=True)

    show_register_popup = request.GET.get('register') == 'true'
    show_login_popup = 'login' in request.GET and request.GET.get('login') in ('true', '')
    work_featured_categories = WorkCategory.objects.filter(is_featured=True)
    edu_featured_categories = CourseCategory.objects.filter(is_featured=True)
    digi_featured_categories = Category.objects.filter(is_featured=True)
    commu_featured_categories = Groupcategory.objects.filter(is_featured=True)
    top_sellers = get_top_sellers(count=1)

    recover = request.GET.get('recover') or ''
    uid = request.GET.get('uid') or ''
    token = request.GET.get('token') or ''
    password_reset_invalid = False
    recovery_open_mode = ''
    if recover == 'reset' and uid and token:
        recovery_open_mode = 'reset'
        try:
            pk = force_str(urlsafe_base64_decode(uid))
            user = CustomUser.objects.get(pk=pk)
            if not default_token_generator.check_token(user, token):
                password_reset_invalid = True
        except Exception:
            password_reset_invalid = True
    elif recover == 'password':
        recovery_open_mode = 'password'
    elif recover == 'username':
        recovery_open_mode = 'username'

    return {
        'best_courses': best_courses,
        'best_products': best_products,
        'best_services': best_services,
        'best_groups': best_groups,
        'work_featured_categories': work_featured_categories,
        'edu_featured_categories': edu_featured_categories,
        'digi_featured_categories': digi_featured_categories,
        'commu_featured_categories': commu_featured_categories,
        'show_register_popup': show_register_popup,
        'show_login_popup': show_login_popup,
        'top_sellers': top_sellers,
        'recovery_open_mode': recovery_open_mode,
        'password_reset_uid': uid,
        'password_reset_token': token,
        'password_reset_invalid': password_reset_invalid,
    }

def home(request):
    return render(request, 'home/homepage.html', get_homepage_context(request))

def leaderboard_dashboard(request):
    # Top Global Sellers (Workprenair)
    top_sellers = []
    # top_sellers = User.objects.filter(
    #     is_work_freelancer=True
    # ).order_by('-total_earnings')[:3]
    dummy_sellers = [
        {'name': 'Sophie Chen', 'total_earnings': 150000},
        {'name': 'James Wilson', 'total_earnings': 120000},
        {'name': 'Elena Diaz', 'total_earnings': 50000}
    ][:3-len(top_sellers)]

    # Top Global Products (Digiprenair)
    top_products = []
    # top_products = Product.objects.annotate(
    #     total_sales=models.Sum('orderitem__quantity')
    # ).order_by('-total_sales')[:3]
    dummy_products = [
        {'title': 'Digital Marketing Course', 'total_sales': 500},
        {'title': 'Freelance Toolkit', 'total_sales': 450},
        {'title': 'SEO Masterclass', 'total_sales': 300}
    ][:3-len(top_products)]

    # Global Rising Stars (Workprenair)
    rising_stars = []
    # rising_stars = User.objects.filter(is_work_freelancer=True,created_at__gte=now()-timedelta(days=30)
    # ).annotate(
    #     growth=models.F('total_earnings')/models.F('work_total_earnings')
    # ).order_by('-growth')[:3]
    dummy_stars = [
        {'name': 'Maria Johnson', 'growth': 65},
        {'name': 'Liam Smith', 'growth': 55},
        {'name': 'Alex Patel', 'growth': 45}
    ][:3-len(rising_stars)]

    # Most Loved Creators (Eduprenair)
    loved_creators = []
    # loved_creators = User.objects.filter(
    #     course__isnull=False
    # ).annotate(
    #     avg_rating=models.Avg('course__courserating__rating'),
    #     review_count=models.Count('course__courserating')
    # ).order_by('-avg_rating', '-review_count')[:3]
    dummy_creators = [
        {'name': 'Sophie Chen', 'avg_rating': 4.9, 'review_count': 1200},
        {'name': 'Maria Johnson', 'avg_rating': 4.8, 'review_count': 900},
        {'name': 'James Wilson', 'avg_rating': 4.7, 'review_count': 750}
    ][:3-len(loved_creators)]

    country_sellers = []
    # country_sellers = list(User.objects.filter(
    #     is_work_freelancer=True
    # ).exclude(location__isnull=True).values('location').annotate(
    #     total_earnings=models.Sum('total_earnings'),
    #     top_seller=models.Subquery(
    #         User.objects.filter(
    #             location=models.OuterRef('location'),
    #             is_work_freelancer=True
    #         ).order_by('-total_earnings').values('name')[:1]
    #     ),
    #     seller_count=models.Count('id')
    # ).order_by('-total_earnings')[:5])

    dummy_country_sellers = [
        {'country': 'United States', 'top_seller': 'Sophie Chen', 'total_earnings': 150000},
        {'country': 'United Kingdom', 'top_seller': 'James Wilson', 'total_earnings': 120000},
        {'country': 'Canada', 'top_seller': 'Elena Diaz', 'total_earnings': 80000}
    ]
    country_sellers = (country_sellers + dummy_country_sellers)[:3]

    # Top Products By Country
    country_products = []
    # country_products = list(Product.objects.exclude(
    #     seller__location__isnull=True
    # ).values('seller__location').annotate(
    #     top_product=models.Subquery(
    #         Product.objects.filter(
    #             seller__location=models.OuterRef('seller__location')
    #         ).order_by('-item_sales').values('title')[:1]
    #     ),
    #     total_sales=models.Sum('item_sales')
    # ).order_by('-total_sales')[:5])

    dummy_country_products = [
        {'seller__country': 'United States', 'top_product': 'SEO Masterclass', 'total_sales': 300},
        {'seller__country': 'United Kingdom', 'top_product': 'Webinar Blueprint', 'total_sales': 250},
        {'seller__country': 'Pakistan', 'top_product': 'Coding Template', 'total_sales': 200}
    ]
    country_products = (country_products + dummy_country_products)[:3]

    # Most Active Sellers By Country
    active_sellers = []
    # active_sellers = list(User.objects.filter(
    #     is_work_freelancer=True
    # ).exclude(location__isnull=True).values('location').annotate(
    #     active_count=models.Count('gigs'),
    #     top_active=models.Subquery(
    #         User.objects.filter(
    #             location=models.OuterRef('location')
    #         ).annotate(
    #             gig_count=models.Count('gigs')
    #         ).order_by('-gig_count').values('name')[:1]
    #     )
    # ).order_by('-active_count')[:5])

    dummy_active_sellers = [
        {'country': 'Canada', 'top_active': 'Elena Diaz', 'active_count': 50},
        {'country': 'Pakistan', 'top_active': 'Zain Ali', 'active_count': 45},
        {'country': 'Germany', 'top_active': 'Liam Smith', 'active_count': 40}
    ]
    active_sellers = (active_sellers + dummy_active_sellers)[:3]

    # Rising Creators By Country
    rising_creators = []
    # rising_creators = list(User.objects.filter(
    #     is_work_freelancer=True,
    #     created_at__gte=now()-timedelta(days=90)
    # ).exclude(location__isnull=True).values('location').annotate(
    #     growth_rate=models.ExpressionWrapper(
    #         models.F('total_earnings') / models.F('work_total_earnings'),
    #         output_field=models.FloatField()
    #     ),
    #     top_creator=models.Subquery(
    #         User.objects.filter(
    #             location=models.OuterRef('location')
    #         ).order_by('-total_earnings').values('name')[:1]
    #     )
    # ).order_by('-growth_rate')[:5])

    dummy_rising_creators = [
        {'country': 'Australia', 'top_creator': 'Maria Johnson', 'growth_rate': 65},
        {'country': 'Germany', 'top_creator': 'Liam Smith', 'growth_rate': 55},
        {'country': 'France', 'top_creator': 'Sophie Martin', 'growth_rate': 45}
    ]
    rising_creators = (rising_creators + dummy_rising_creators)[:3]

    # digi_sellers = list(User.objects.filter(
    #     is_digi_seller=True
    # ).order_by('-digi_total_earnings')[:3])
    digi_sellers = []
    dummy_digi = [
        {'name': 'Sophie Chen', 'digi_total_earnings': 90000, 'role': 'Digital Products'},
        {'name': 'James Wilson', 'digi_total_earnings': 70000, 'role': 'Digital Products'},
        {'name': 'Elena Diaz', 'digi_total_earnings': 50000, 'role': 'Digital Products'}
    ][:3-len(digi_sellers)]
    digi_sellers += dummy_digi

    # Eduprenair Top Rated Products (Courses)
    edu_products = []
    # edu_products = list(Course.objects.annotate(
    #     avg_rating=models.Avg('courserating__rating')
    # ).order_by('-avg_rating')[:3])
    dummy_edu = [
        {'title': 'Coding Bootcamp', 'instructor__name': 'Elena Diaz', 'avg_rating': 4.9},
        {'title': 'Marketing Course', 'instructor__name': 'Alex Patel', 'avg_rating': 4.8},
        {'title': 'Design Masterclass', 'instructor__name': 'Sophie Chen', 'avg_rating': 4.7}
    ][:3-len(edu_products)]
    edu_products += dummy_edu

    # Workprenair Fastest Growing Sellers (Freelancers)
    work_growth = []
    # work_growth = list(User.objects.filter(
    #     is_work_freelancer=True
    # ).annotate(
    #     growth=models.ExpressionWrapper(
    #         (models.F('total_earnings') - models.F('work_total_earnings')) / 
    #         models.F('work_total_earnings') * 100,
    #         output_field=models.FloatField()
    #     )
    # ).order_by('-growth')[:3])
    dummy_work = [
        {'name': 'Maria Johnson', 'growth': 65, 'role': 'Freelance'},
        {'name': 'Liam Smith', 'growth': 60, 'role': 'Freelance'},
        {'name': 'Alex Patel', 'growth': 55, 'role': 'Freelance'}
    ][:3-len(work_growth)]
    work_growth += dummy_work

    # Commuprenair Most New Products (Webinars/Coaching)
    commu_new = []
    # commu_new = list(Course.objects.filter(
    #     created_at__gte=now()-timedelta(days=30)
    # ).annotate(
    #     product_count=models.Count('id')
    # ).order_by('-created_at')[:3])
    dummy_commu = [
        {'title': 'Webinar Series', 'instructor__name': 'Alex Patel', 'product_count': 10},
        {'title': 'Coaching Program', 'instructor__name': 'Elena Diaz', 'product_count': 8},
        {'title': 'Workshop Bundle', 'instructor__name': 'Sophie Chen', 'product_count': 6}
    ][:3-len(commu_new)]
    commu_new += dummy_commu

    no_1_seller = get_top_sellers(count=1)[0] if get_top_sellers(count=1) else None
    top_digi_products = get_top_digi_products(count=5)

    context = {
        'top_sellers': list(top_sellers) + dummy_sellers,
        'top_products': list(top_products) + dummy_products,
        'rising_stars': list(rising_stars) + dummy_stars,
        'loved_creators': list(loved_creators) + dummy_creators,
        'country_sellers': country_sellers,
        'country_products': country_products,
        'active_sellers': active_sellers,
        'rising_creators': rising_creators,
        'digi_sellers': digi_sellers[:3],
        'edu_products': edu_products[:3],
        'work_growth': work_growth[:3],
        'commu_new': commu_new[:3],
        'no_1_seller': no_1_seller
,       'top_digi_products': top_digi_products
    }
    return render(request, 'home/leaderboard_dashboard.html', context)

def home_subscribe(request):
    errors = {}
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        
        if not name:
            errors['name'] = "Name is required."
        if not email:
            errors['email'] = "Email is required."
        else:
            from django.core.validators import validate_email
            try:
                validate_email(email)
            except ValidationError:
                errors['email'] = "Enter a valid email address."

            if Subscribe.objects.filter(email=email).exists():
                errors['email'] = "This email is already subscribed."

        if not errors:
            Subscribe.objects.create(name=name, email=email)
            messages.success(request, "You have successfully subscribed!")
            return redirect('home')

    context = {
        'errors': errors,
        'values': request.POST if request.method == 'POST' else {},
    }

    return render(request, 'home/home_subscribe.html', context)

# ------------------------- Category API's -------------------------
def work_parent_categories(request):
    categories = WorkCategory.objects.filter(parent=None)
    data = []
    for category in categories[:5]:
        data.append({
            'id': category.id,
            'name': category.name,
            'description': category.description
        })
    return JsonResponse(data, safe=False)


def edu_parent_categories(request):
    categories = CourseCategory.objects.filter(parent=None)
    data = []
    for category in categories[:5]:
        data.append({
            'id': category.id,
            'name': category.name,
            'description': category.description
        })
    return JsonResponse(data, safe=False)


def digi_parent_categories(request):
    categories = Category.objects.filter(parent=None)
    data = []
    for category in categories[:5]:
        data.append({
            'id': category.id,
            'name': category.name,
            'description': category.description
        })
    return JsonResponse(data, safe=False)


def commu_parent_categories(request):
    categories = Groupcategory.objects.filter(parent=None)
    data = []
    for category in categories[:5]:
        data.append({
            'id': category.id,
            'name': category.name,
            'description': category.desc
        })
    return JsonResponse(data, safe=False)






# ------------------------- Legal Pages -------------------------
def terms_of_use(request):
    return render(request, 'home/terms.html')


def license_agreement(request):
    return render(request, 'home/license_agreement.html')


def privacy_policy(request):
    return render(request, 'home/privacy_policy.html')

def copyright_info(request):
    return render(request, 'home/copyright_info.html')

def cookies(request):
    return render(request, 'home/cookies.html')

def dmca_policy(request):
    return render(request, 'home/dmca_policy.html')

def privacy_choice_policy(request):
    return render(request, 'home/privacy_choice_policy.html')

def refund_policy(request):
    return render(request, 'home/refund_policy.html')


# ------------------------- Company Pages -------------------------
def about_us(request):
    return render(request, 'home/about_us.html')

def contact_support(request):
    return render(request, 'home/contact_support.html')

def help_support(request):
    return render(request, 'home/help_support.html')

def how_it_works(request):  
    return render(request, 'home/how_it_works.html')

def pricing(request):
    plans = PricingPlan.objects.all().order_by('price_monthly')
    basic_plan = PricingPlan.objects.get(title='FreeTier')
    startprenair_plan = PricingPlan.objects.get(title='StartPrenair')
    bizprenair_plan = PricingPlan.objects.get(title='BizPrenair')
    entreprenair_plan = PricingPlan.objects.get(title='EntrePrenair')


    context = {
        'plans': plans,
        'basic_plan': basic_plan,
        'start_plan': startprenair_plan,
        'biz_plan': bizprenair_plan,
        'entre_plan': entreprenair_plan
    }
    return render(request, 'home/pricing.html', context)

def fees_commisions(request):
    return render(request, 'home/fees_commisions.html')

def faq(request):
    return render(request, 'home/faq.html')



# ------------------------- Resources Pages -------------------------
def training(request):
    return render(request, 'home/training.html')

def digital_products(request):
    return render(request, 'home/digital_products.html')


def affiliates(request):
    return render(request, 'home/affiliates.html')

def partnerships(request):
    return render(request, 'home/partnerships.html')

def community(request):
    return render(request, 'home/community.html')


# Extra Pages
def custom_404(request, exception):
    return render(request, 'home/404.html', status=404)

def custom_500(request):
    return render(request, 'home/500.html', status=500)



# feature pages
def features(request):
    return render(request, 'home/features.html')

def corporate_solutions(request):
    return render(request, 'home/corporate_solutions.html')


# ── Corporate flow API endpoints ──────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def corporate_check_email(request):
    """Return whether the email belongs to an existing account."""
    try:
        data = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, ValueError):
        data = {}
    from profiles.models import CustomUser
    email = (data.get('email') or '').strip().lower()
    if not email:
        return JsonResponse({'error': 'Email is required.'}, status=400)
    import re as _re
    if not _re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return JsonResponse({'error': 'Please enter a valid email address.'}, status=400)
    exists = CustomUser.objects.filter(email__iexact=email).exists()
    return JsonResponse({'exists': exists})


@csrf_exempt
@require_http_methods(["POST"])
def corporate_login_api(request):
    """Lightweight JSON login endpoint used by the corporate project modal."""
    from django.contrib.auth import authenticate, login as auth_login
    from profiles.models import CustomUser
    try:
        data = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, ValueError):
        data = {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    if not email or not password:
        return JsonResponse({'success': False, 'error': 'Email and password are required.'}, status=400)
    user = authenticate(request, username=email, password=password)
    if user is None:
        # try by username
        try:
            u = CustomUser.objects.get(username__iexact=email)
            user = authenticate(request, username=u.email, password=password)
        except CustomUser.DoesNotExist:
            pass
    if user is None:
        return JsonResponse({'success': False, 'error': 'Invalid email or password.'}, status=400)
    auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return JsonResponse({'success': True})


@csrf_exempt
@require_http_methods(["POST"])
def corporate_verify_otp(request):
    """Verify OTP for new registrations inside the corporate modal."""
    from profiles.models import CustomUser
    from django.contrib.auth import login as auth_login
    from django.utils.crypto import get_random_string
    import base64, uuid
    from django.core.files.base import ContentFile

    try:
        data = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, ValueError):
        data = {}
    code = (data.get('code') or '').strip().upper()
    registration_data = request.session.get('registration_data')

    if not registration_data:
        return JsonResponse({'success': False, 'error': 'Session expired. Please register again.'}, status=400)
    if registration_data.get('verification_code') != code:
        return JsonResponse({'success': False, 'error': 'Invalid code. Please try again.'}, status=400)

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
        if registration_data.get('profile_photo_data'):
            try:
                fmt, imgstr = registration_data['profile_photo_data'].split(';base64,')
                ext = fmt.split('/')[-1]
                fname = f"profile_pics/{user.username}_{uuid.uuid4().hex[:8]}.{ext}"
                user.profile_pic.save(fname, ContentFile(base64.b64decode(imgstr), name=fname), save=True)
            except Exception:
                pass
        user.save()
        del request.session['registration_data']
        auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': True})


@csrf_exempt
@require_http_methods(["POST"])
def submit_corporate_project(request):
    """Save a CorporateProject and mark the user as a corporate client."""
    from .models import CorporateProject
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required.'}, status=401)
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
        return JsonResponse({'success': False, 'errors': errors}, status=400)

    project = CorporateProject.objects.create(
        user=request.user,
        title=title,
        description=description,
        category=category,
        budget=budget,
    )
    # mark the user as a corporate client
    if not request.user.is_corporate_client:
        request.user.is_corporate_client = True
        request.user.save(update_fields=['is_corporate_client'])

    return JsonResponse({
        'success': True,
        'project_id': project.pk,
        'redirect_url': '/corporate-dashboard/',
    })


def corporate_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('/?login=true')
    from .models import CorporateProject
    projects = CorporateProject.objects.filter(user=request.user)
    return render(request, 'home/corporate_dashboard.html', {
        'projects': projects,
        'active_count': projects.filter(status='active').count(),
        'pending_count': projects.filter(status='pending').count(),
        'completed_count': projects.filter(status='completed').count(),
    })


def feature_detail(request):
    feature_pg = request.GET.get('feature')
    if not feature_pg:
        return redirect('features')
    return render(request, f'home/features_detail_{feature_pg}.html')


def blog_list(request):
    posts_list = BlogPost.objects.filter(published=True).order_by('-published_date')
    paginator = Paginator(posts_list, 10)
    page = request.GET.get('page')
    
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)
    categories = Category.objects.all()
    
    context = {
        'posts': posts,
        'categories': categories,
    }
    return render(request, 'home/blog_list.html', context)


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, published=True)
    post.views += 1
    post.save()
    related_posts = BlogPost.objects.filter(
        category=post.category,
        published=True
    ).exclude(id=post.id)[:3]
    categories = BlogCategory.objects.all()[:10]
    context = {
        'blog': post,
        'related_blogs': related_posts,
        'categories': categories
    }
    return render(request, 'home/blog_detail.html', context)