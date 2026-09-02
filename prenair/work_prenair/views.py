from django.shortcuts import render, redirect, get_object_or_404, reverse
from .models import *
from commu_prenair.models import Message, PrivateChat
from django.contrib.auth.decorators import login_required
from django.conf import settings
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
def workprenair_chatbot_view(request):
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



def work_home(request):
    web_dev_gigs = Gig.objects.filter(category_level_1__name='Programming & Tech')[:8]
    design_gigs = Gig.objects.filter(category_level_1__name='Graphics & Design')[:8]
    ai_gigs = Gig.objects.filter(category_level_1__name='AI')[:8]
    writing_gigs = Gig.objects.filter(category_level_1__name='Writing')[:8]
    marketing_gigs = Gig.objects.filter(category_level_1__name='Digital Marketing')[:8]

    top_categories = Category.objects.filter(is_featured=True, parent=None)

    context = {
        'web_dev_gigs': web_dev_gigs,
        'design_gigs': design_gigs,
        'ai_gigs': ai_gigs,
        'writing_gigs': writing_gigs,
        'marketing_gigs': marketing_gigs,
        'top_categories': top_categories
    }

    return render(request, 'work_prenair/work_home.html', context)

# ------------------- DASHBOARD -------------------

@login_required
def sellor_dashboard(request):
    if not request.user.is_work_freelancer:
        return redirect('buyer_dashboard')
    
    user_gigs = request.user.gigs.all()

    monthly_orders_data = (
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
    for data in monthly_orders_data
    ]

    # Aggregate orders data by year (for "Year" view)
    yearly_orders_data = (
        Order.objects.filter(gig__in=user_gigs)
        .annotate(year=ExtractYear('created_at'))
        .values('year')
        .annotate(order_count=Count('id'))
        .order_by('year')
    )

    active_orders = []
    active_orders_count = 0
    for gig in user_gigs:
        orders = gig.orders.filter(is_completed=False, is_delivered=False)
        active_orders_count += orders.count()
        active_orders.extend(orders)

    delivered_orders = []
    for gig in user_gigs:
        orders = gig.orders.filter(is_delivered=True, is_completed=False)
        delivered_orders.extend(orders)

    completed_orders = []
    completed_orders_count = 0
    for gig in user_gigs:
        orders = gig.orders.filter(is_completed=True)
        completed_orders_count += orders.count()
        completed_orders.extend(orders)

    notifications = Notification.objects.filter(user=request.user, app_name="workprenair")

    context = {
        'user_gigs': user_gigs,
        'active_orders': active_orders,
        'completed_orders': completed_orders,
        'active_orders_count': active_orders_count,
        'completed_orders_count': completed_orders_count,
        'delivered_orders': delivered_orders,
        'notifications' : notifications,
        'formatted_monthly_orders_data': formatted_monthly_orders_data,
        'yearly_orders_data': list(yearly_orders_data),
    }

    return render(request, 'work_prenair/sellor_dashboard.html', context)


@login_required
def user_orders(request):
    if request.user.is_work_freelancer:
        orders = Order.objects.filter(gig__user=request.user)
    else:
        orders = Order.objects.filter(user=request.user)
    active_orders = orders.filter(is_completed=False, is_delivered=False)
    completed_orders = orders.filter(is_completed=True)
    delivered_orders = orders.filter(is_delivered=True, is_completed=False)

    context = {
        'active_orders': active_orders,
        'delivered_orders': delivered_orders,
        'completed_orders': completed_orders,
    }
    return render(request, 'work_prenair/user_projects.html', context)

@login_required
def buyer_dashboard(request):
    if request.user.is_work_freelancer:
        return redirect('sellor_dashboard')
    active_orders = Order.objects.filter(user=request.user, is_completed=False, is_delivered=False)
    completed_orders = Order.objects.filter(user=request.user, is_completed=True)
    delivered_orders = Order.objects.filter(user=request.user, is_delivered=True, is_completed=False)
    notifications = Notification.objects.filter(user=request.user, app_name="workprenair")
    reviews = Review.objects.filter(order__user=request.user, is_client_review=False)

    monthly_orders_data = (
    Order.objects.filter(user=request.user)
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
    for data in monthly_orders_data
    ]

    context = {
        'active_orders': active_orders,
        'completed_orders': completed_orders,
        'delivered_orders': delivered_orders,
        'notifications' : notifications,
        'chart_data': chart_data,
        'reviews': reviews
    }

    return render(request, 'work_prenair/buyer_dashboard.html', context)




def workprenair_notifications(request):
    user = request.user

    # Fetch unread notifications for the user
    unread_notifications = Notification.objects.filter(user=user, is_read=False, app_name='workprenair')

    # Mark unread notifications as read
    unread_notifications.update(is_read=True)

    # Fetch all notifications (including the ones just marked as read)
    notifications = Notification.objects.filter(user=user, app_name='workprenair').order_by("-created_at")

    context = {
        "user": user,
        "notifications": notifications,
    }
    return render(request, "work_prenair/workprenair_notifications.html", context)
    



# ------------------- Profiles -------------------
@login_required
def user_profile(request, username):
    user = get_object_or_404(User, username=username)
    user_gigs = None
    user_reviews_as_client = []
    user_reviews_as_seller = None
    user_orders = None
    if user.is_work_freelancer:
        user_gigs = Gig.objects.filter(user=user)
        user_reviews_as_seller = Review.objects.filter(gig__user=user, is_client_review=True)
    else:
        user_orders = Order.objects.filter(user=user)
        order_ids = user_orders.values_list('id', flat=True)
        user_reviews_as_client = Review.objects.filter(order_id__in=order_ids, is_client_review=False)

    rating_range = range(1, 6)

    context = {
        'user': user,
        'user_gigs': user_gigs,
        'user_orders': user_orders,
        'rating_range': rating_range,
        'user_reviews_as_client': user_reviews_as_client,
        'user_reviews_as_seller': user_reviews_as_seller
    }
    return render(request, 'work_prenair/work_user_profile.html', context)

@login_required
def edit_profile(request):
    if request.method == 'POST':
        user = request.user
        user.name = request.POST.get('name') if request.POST.get('name') else user.name
        user.work_bio = request.POST.get('work_bio') if request.POST.get('work_bio') else user.work_bio
        user.profile_pic = request.FILES.get('profile_pic') if request.FILES.get('profile_pic') else user.profile_pic
        user.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('work_user_profile', username=user.username)
    return render(request, 'work_prenair/work_edit_profile.html')



# ------------------- TODO -------------------

def todos(request):
    todos = Todo.objects.filter(user=request.user)
    context = {
        'todos': todos
    }
    return render(request, 'work_prenair/todos.html', context)

@login_required
@require_http_methods(['POST'])
def create_todo(request):
    if not request.user.is_work_freelancer:
        return JsonResponse({'status': 'error', 'message': 'Un-Authurized'})
    title = request.POST.get('title')
    description = request.POST.get('description')
    todo = Todo.objects.create(
        user=request.user,
        title=title,
        description=description
    )
    return JsonResponse({
        'id': todo.id,
        'title': todo.title,
        'description': todo.description,
        'created_at': todo.created_at.strftime("%b %d, %Y %H:%M"),
        'is_completed': todo.is_completed
    })

@require_http_methods(["POST"])
def update_todo(request, pk):
    todo = Todo.objects.get(pk=pk, user=request.user)
    todo.title = request.POST.get('title') if request.POST.get('title') else todo.title
    todo.description = request.POST.get('description') if request.POST.get('description') else todo.description
    todo.is_completed = request.POST.get('is_completed') == 'true'
    if todo.is_completed:
        todo.completed_at = timezone.now()
    else:
        todo.completed_at = None
    todo.save()
    return JsonResponse({
        'id': todo.id,
        'title': todo.title,
        'description': todo.description,
        'is_completed': todo.is_completed,
        'completed_at': todo.completed_at.strftime("%b %d, %Y %H:%M") if todo.completed_at else None
    })

@require_http_methods(["DELETE"])
def delete_todo(request, pk):
    print(pk)
    todo = Todo.objects.get(pk=pk, user=request.user)
    todo.delete()
    return JsonResponse({'status': 'success'})


# ------------------- GIGS -------------------

def gigs(request):
    keyword = request.GET.get('keyword', '').strip()
    category_id = request.GET.get('category', '').strip()
    min_price = request.GET.get('min_price', '0').strip()
    max_price = request.GET.get('max_price', '3000').strip()
    delivery_time = request.GET.get('delivery_time', '').strip()
    country_filter = request.GET.get('location', '').strip()  # URL param still 'location' for backward compatibility
    sort_by = request.GET.get('sort_by', 'relevance')

    gigs = Gig.objects.all()

    if keyword:
        gigs = gigs.filter(
            Q(title__icontains=keyword) |
            Q(description__icontains=keyword) |
            Q(tags__name__icontains=keyword)
        ).distinct()

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

    country_mapping = {
        'United States': 'United States',
        'Canada': 'Canada',
        'United Kingdom': 'United Kingdom',
        'India': 'India',
        'Pakistan': 'Pakistan',
        'Bangladesh': 'Bangladesh',
    }
    if country_filter:
        country_filter = country_mapping.get(country_filter, country_filter)
        gigs = gigs.filter(user__country__iexact=country_filter)

    if sort_by == "price_low":
        gigs = gigs.order_by('basic_price')
    elif sort_by == "price_high":
        gigs = gigs.order_by('-basic_price')
    elif sort_by == "rating":
        gigs = gigs.annotate(avg_rating=Avg('gig_fivestar_reviews__rating')).order_by('-avg_rating')
    elif sort_by == "newest":
        gigs = gigs.order_by('-created_at')

    categories = Category.objects.filter(parent=None)

    paginator = Paginator(gigs, 20)
    page = request.GET.get('page', 1)
    try:
        gigs_page = paginator.page(page)
    except PageNotAnInteger:
        gigs_page = paginator.page(1)
    except EmptyPage:
        gigs_page = paginator.page(paginator.num_pages)


    context = {
        'gigs': gigs_page,
        'categories': categories,
        'keyword': keyword,
        'min_price': min_price,
        'max_price': max_price,
        'delivery_time': delivery_time,
        'location': country_filter,
        'sort_by': sort_by,
        'selected_category': Category.objects.get(id=category_id) if category_id else None,
    }
    return render(request, 'work_prenair/gigs.html', context)



def get_child_categories(request, parent_id):
    try:
        categories = Category.objects.filter(parent_id=parent_id).values('id', 'name')
        return JsonResponse({'status': 'success', 'categories': list(categories)})
    except Category.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Parent category not found'}, status=404)
    

def search_tags(request):
    query = request.GET.get('q', '')
    if query:
        tags = Tag.objects.filter(name__icontains=query).values('id', 'name')
    else:
        tags = Tag.objects.none()
    return JsonResponse({'status': 'success', 'tags': list(tags)})

@login_required
def gig_tags(request, gig_slug):
    try:
        gig = Gig.objects.get(slug=gig_slug)
        tags = gig.tags.all().values('id', 'name')
        return JsonResponse({'status': 'success', 'tags': list(tags)})
    except Gig.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Gig not found'})
    
@login_required
def create_tag(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'error': 'Invalid request method'}, status=405)

    try:
        data = json.loads(request.body)  # Correct way to get JSON data
        name = data.get('name')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'error': 'Invalid JSON'}, status=400)

    if not name:
        return JsonResponse({'status': 'error', 'error': 'Name is required'}, status=400)
    
    # Check if tag exists (case-insensitive)
    tag, created = Tag.objects.get_or_create(name__iexact=name, defaults={'name': name})

    return JsonResponse({'status': 'success', 'tag': {'id': tag.id, 'name': tag.name}})





@login_required
def user_gigs(request):
    if not request.user.is_work_freelancer:
        return redirect('buyer_dashboard')
    gigs = Gig.objects.filter(user=request.user)
    context = {
        'gigs': gigs
    }
    return render(request, 'work_prenair/user_gigs.html', context)


# views.py
@login_required
@require_POST
def suggest_gig_pricing(request, slug):
    gig = get_object_or_404(Gig, slug=slug)
    if request.user != gig.user:
        return JsonResponse({'error': 'Unauthorized access'}, status=403)

    try:
        related_gigs = Gig.objects.filter(
            Q(category_level_1=gig.category_level_1) |
            Q(category_level_2=gig.category_level_2) |
            Q(category_level_3=gig.category_level_3)
        ).exclude(id=gig.id)

        basic_prices = [g.basic_price for g in related_gigs if g.basic_price]
        standard_prices = [g.standard_price for g in related_gigs if g.standard_price]
        premium_prices = [g.premium_price for g in related_gigs if g.premium_price]

        market_data = {
            'basic': {
                'avg': sum(basic_prices)/len(basic_prices) if basic_prices else 0,
                'min': min(basic_prices) if basic_prices else 0,
                'max': max(basic_prices) if basic_prices else 0
            },
            'standard': {
                'avg': sum(standard_prices)/len(standard_prices) if standard_prices else 0,
                'min': min(standard_prices) if standard_prices else 0,
                'max': max(standard_prices) if standard_prices else 0
            },
            'premium': {
                'avg': sum(premium_prices)/len(premium_prices) if premium_prices else 0,
                'min': min(premium_prices) if premium_prices else 0,
                'max': max(premium_prices) if premium_prices else 0
            }
        }

        prompt = f"""
        Act as a professional pricing strategist for freelancers. Analyze this gig's pricing and suggest optimizations:

        Current Pricing:
        - Basic: ${gig.basic_price} (Delivery: {gig.basic_delivery_time} days)
        - Standard: ${gig.standard_price} (Delivery: {gig.standard_delivery_time} days)
        - Premium: ${gig.premium_price} (Delivery: {gig.premium_delivery_time} days)

        Market Data from similar gigs:
        - Basic Package: Average ${market_data['basic']['avg']:.2f}, Range ${market_data['basic']['min']}-${market_data['basic']['max']}
        - Standard Package: Average ${market_data['standard']['avg']:.2f}, Range ${market_data['standard']['min']}-${market_data['standard']['max']}
        - Premium Package: Average ${market_data['premium']['avg']:.2f}, Range ${market_data['premium']['min']}-${market_data['premium']['max']}

        Provide:
        1. Specific price suggestions for each package (formatted as numbers only)
        2. 3 service bundle ideas with pricing
        3. Brief explanations for each suggestion
        
        Return JSON format with keys: 
        'basic_suggestion', 'standard_suggestion', 'premium_suggestion',
        'bundles', 'explanations'
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )

        # Parse and validate response
        suggestions = json.loads(response.choices[0].message.content)
        print(suggestions)
        return JsonResponse(suggestions)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def create_gig(request):
    if not request.user.is_work_freelancer:
        messages.warning(request, "You are not authorized to create a gig, please become a freelancer first.")
        return redirect('become_seller')
    
    categories = Category.objects.filter(parent=None) 
    package_names = ['basic', 'standard', 'premium']
    
    if request.method == 'POST':
        title = request.POST.get('title')
        short_description = request.POST.get('short_description')
        description = request.POST.get('gig_description')
        image = request.FILES.get('image')
        
        additional_images = request.FILES.getlist('additional_images')
        promo_video = request.POST.get('promo_video')

        category_level_1_id = request.POST.get('category_level_1')
        category_level_2_id = request.POST.get('category_level_2')
        category_level_3_id = request.POST.get('category_level_3')

        category_level_1 = Category.objects.get(id=category_level_1_id) if category_level_1_id else None
        category_level_2 = Category.objects.get(id=category_level_2_id) if category_level_2_id else None
        category_level_3 = Category.objects.get(id=category_level_3_id) if category_level_3_id else None

        tags_data = request.POST.get('tags') 
        try:
            tag_ids = json.loads(tags_data) if tags_data else [] 
        except json.JSONDecodeError:
            tag_ids = [] 

        tag_objects = Tag.objects.filter(id__in=tag_ids) 

        packages = {
            'basic': {
                'basic_name': request.POST.get('basic_name'),
                'basic_description': request.POST.get('basic_description'),
                'basic_delivery_time': int(request.POST.get('basic_delivery_time')),
                'basic_revisions': int(request.POST.get('basic_revisions')),
                'basic_price': float(request.POST.get('basic_price')),
            },
            'standard': {
                'standard_name': request.POST.get('standard_name'),
                'standard_description': request.POST.get('standard_description'),
                'standard_delivery_time': int(request.POST.get('standard_delivery_time')),
                'standard_revisions': int(request.POST.get('standard_revisions')),
                'standard_price': float(request.POST.get('standard_price')),
            },
            'premium': {
                'premium_name': request.POST.get('premium_name'),
                'premium_description': request.POST.get('premium_description'),
                'premium_delivery_time': int(request.POST.get('premium_delivery_time')),
                'premium_revisions': int(request.POST.get('premium_revisions')),
                'premium_price': float(request.POST.get('premium_price')),
            },
        }

        u_id = uuid.uuid4()
        slug = slugify(f"{title}-{request.user.username}-{u_id}")
        
        gig = Gig.objects.create(
            user=request.user,
            title=title,
            # short_description=short_description,
            slug=slug,
            description=description,
            image=image,
            # promo_video=promo_video,
            category_level_1=category_level_1,
            category_level_2=category_level_2,
            category_level_3=category_level_3,
            **packages['basic'],
            **packages['standard'],
            **packages['premium'],
        )

        gig.tags.add(*tag_objects)

        request.user.is_work_freelancer = True
        request.user.save()
        
        # Return JSON response for AJAX submission
        return JsonResponse({
            'status': 'success',
            'message': 'Gig created successfully!',
            'redirect_url': reverse('gig_detail', kwargs={'slug': gig.slug})
        })

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'work_prenair/create_gig.html', {
            'package_names': package_names,
            'categories': categories,
        })
    
    return render(request, 'work_prenair/create_gig.html', {
        'package_names': package_names,
        'categories': categories,
    })


@login_required
def edit_gig(request, slug):
    gig = get_object_or_404(Gig, slug=slug, user=request.user)

    if request.user != gig.user:
        messages.warning(request, "You are not authorized to edit this gig.")
        return redirect('work_home')

    if request.method == 'POST':
        title = request.POST.get('title')
        # Handle both 'description' and 'gig_description' for compatibility
        description = request.POST.get('gig_description') or request.POST.get('description')
        short_description = request.POST.get('short_description')
        image = request.FILES.get('image') or gig.image
        
        additional_images = request.FILES.getlist('additional_images')
        promo_video = request.POST.get('promo_video')

        category_level_1_id = request.POST.get('category_level_1')
        category_level_2_id = request.POST.get('category_level_2')
        category_level_3_id = request.POST.get('category_level_3')

        category_level_1 = Category.objects.get(id=category_level_1_id) if category_level_1_id else None
        category_level_2 = Category.objects.get(id=category_level_2_id) if category_level_2_id else None
        category_level_3 = Category.objects.get(id=category_level_3_id) if category_level_3_id else None

        tags_data = request.POST.get('tags')
        try:
            tag_ids = json.loads(tags_data) if tags_data else []
        except json.JSONDecodeError:
            tag_ids = []

        tag_objects = Tag.objects.filter(id__in=tag_ids)

        packages = {
            'basic': {
                'basic_name': request.POST.get('basic_name'),
                'basic_description': request.POST.get('basic_description'),
                'basic_delivery_time': int(request.POST.get('basic_delivery_time')),
                'basic_revisions': int(request.POST.get('basic_revisions')),
                'basic_price': float(request.POST.get('basic_price')),
            },
            'standard': {
                'standard_name': request.POST.get('standard_name'),
                'standard_description': request.POST.get('standard_description'),
                'standard_delivery_time': int(request.POST.get('standard_delivery_time')),
                'standard_revisions': int(request.POST.get('standard_revisions')),
                'standard_price': float(request.POST.get('standard_price')),
            },
            'premium': {
                'premium_name': request.POST.get('premium_name'),
                'premium_description': request.POST.get('premium_description'),
                'premium_delivery_time': int(request.POST.get('premium_delivery_time')),
                'premium_revisions': int(request.POST.get('premium_revisions')),
                'premium_price': float(request.POST.get('premium_price')),
            },
        }

        gig.title = title
        gig.description = description
        gig.image = image
        gig.category_level_1 = category_level_1
        gig.category_level_2 = category_level_2
        gig.category_level_3 = category_level_3

        for key, value in packages.items():
            setattr(gig, f'{key}_name', value[f'{key}_name'])
            setattr(gig, f'{key}_description', value[f'{key}_description'])
            setattr(gig, f'{key}_delivery_time', value[f'{key}_delivery_time'])
            setattr(gig, f'{key}_revisions', value[f'{key}_revisions'])
            setattr(gig, f'{key}_price', value[f'{key}_price'])

        try:
            gig.tags.clear()
            gig.tags.add(*tag_objects)
            gig.save()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Gig updated successfully!',
                    'redirect_url': reverse('gig_detail', kwargs={'slug': gig.slug})
                })

            return redirect('gig_detail', slug=gig.slug)
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'error': str(e)
                }, status=400)
            messages.error(request, f'Error updating gig: {str(e)}')
            return redirect('edit_gig', slug=gig.slug)
    

    categories = Category.objects.filter(parent=None)
    all_categories = Category.objects.all()
    package_names = ['basic', 'standard', 'premium']
    
    # Get selected categories for pre-filling
    selected_category_l_1 = gig.category_level_1.id if gig.category_level_1 else None
    selected_category_l_2 = gig.category_level_2.id if gig.category_level_2 else None
    selected_category_l_3 = gig.category_level_3.id if gig.category_level_3 else None
    
    # Get existing tags
    existing_tags = list(gig.tags.values('id', 'name'))
    
    context = {
        'gig': gig,
        'categories': categories,
        'package_names': package_names,
        'all_categories': all_categories,
        'selected_category_l_1': selected_category_l_1,
        'selected_category_l_2': selected_category_l_2,
        'selected_category_l_3': selected_category_l_3,
        'existing_tags': existing_tags,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'work_prenair/create_gig.html', context)
    
    return render(request, 'work_prenair/create_gig.html', context)



def gig_detail(request, slug):
    gig = get_object_or_404(Gig, slug=slug)
    prev_gig = Gig.objects.filter(created_at__lt=gig.created_at).order_by('-created_at').first()
    next_gig = Gig.objects.filter(created_at__gt=gig.created_at).order_by('created_at').first()

    print(prev_gig, next_gig)

    description_html = markdown.markdown(gig.description)

    rating_range = range(1, 6)

    context = {
        'gig': gig,
        'rating_range': rating_range,
        'description_html': description_html, 
        'prev_gig': prev_gig,
        'next_gig': next_gig,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        template = "work_prenair/gig_modal_content.html"

    else:
        template = "work_prenair/gig_detail.html"

    return render(request, template, context)

@login_required
@require_POST
def optimize_gig(request, slug):
    gig = get_object_or_404(Gig, slug=slug)
    
    if request.user != gig.user:
        return JsonResponse({'error': 'Unauthorized access'}, status=403)

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
        
        if cleaned_content.startswith('```json'):
            cleaned_content = cleaned_content[7:-3].strip()
        elif cleaned_content.startswith('```'):
            cleaned_content = cleaned_content[3:-3].strip()

        cleaned_content = re.sub(r',\s*}', '}', cleaned_content)
        cleaned_content = re.sub(r',\s*]', ']', cleaned_content)
        suggestions = json.loads(cleaned_content)
        required_keys = ['titles', 'descriptions', 'keywords']
        if not all(key in suggestions for key in required_keys):
            raise ValueError("Invalid AI response structure")
            
        return JsonResponse(suggestions)

    except json.JSONDecodeError as e:
        print(f"Failed to parse AI response: {cleaned_content}")
        return JsonResponse({'error': f'Invalid JSON format from AI: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
def apply_gig_ai_suggestion(request):
    if not request.user.is_authenticated:
        return JsonResponse({"status": "error", "message": "Authentication required"},status=401)

    try:
        data = json.loads(request.body)
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

@login_required
def delete_gig(request, slug):
    gig = Gig.objects.get(slug=slug)
    if request.user != gig.user:
        messages.warning(request, "You are not authorized to perform this action.")
        return redirect('work_home')
    gig.delete()
    messages.success(request, "Gig deleted successfully.")
    return redirect('user_gigs')


# ------------------- ORDERS -------------------
@login_required
def order_detail(request, order_slug):
    order = Order.objects.get(slug=order_slug)
    if request.user != order.user and request.user != order.gig.user:
        messages.warning(request, "You are not authorized to view this page.")
        return redirect('work_home')
    rating_range = range(1, 6)
    context = {
        'order': order,
        'rating_range': rating_range
    }
    return render(request, 'work_prenair/order_detail.html', context)


@login_required
def submit_requirements(request, order_id):
    order = Order.objects.get(id=order_id)
    if request.user != order.user:
        messages.warning(request, "You are not authorized to view this page.")
        return redirect('work_home')
    if request.method == 'POST':
        requirements = request.POST.get('requirements')
        order.requirements = requirements
        order.status = "active"
        order.delivery_date = now() + timedelta(days=order.delivery_days)
        order.save()
        Notification.objects.create(user=order.gig.user, app_name="workprenair", message=f"Requirements submitted for Order #{order.id}. Start working on it now.")
        messages.success(request, "Requirements submitted successfully, Order is now active!")
                # Send email to buyer
        buyer_url = request.build_absolute_uri(reverse("order_detail", args=[order.slug]))
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

                    <!-- Footer -->
                    <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                        <p style="margin: 0; font-size: 14px;">Thank you for choosing FirePrenair! 🚀</p>
                    </div>
                </div>
            </body>
            </html>
        """
        send_email(request.user.email, f"Order #{order.id} is Now Active!", buyer_email_content)

        # Send email to seller
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

                    <!-- Footer -->
                    <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                        <p style="margin: 0; font-size: 14px;">Best Regards, The FirePrenair Team</p>
                    </div>
                </div>
            </body>
            </html>
        """
        send_email(order.gig.user.email, f"Order #{order.id} is now Active!", seller_email_content)

        messages.success(request, "Requirements submitted successfully, Order is now active!")
        return redirect('order_detail', order_slug=order.slug)

    context = {
        'order': order
    }
    return render(request, 'work_prenair/order_detail.html', context)


@login_required
def order_delivery(request, order_slug):
    order = Order.objects.get(slug=order_slug)
    if request.user != order.gig.user:
        messages.warning(request, "You are not authorized to view this page.")
        return redirect('work_home')

    if request.method == 'POST':
        message = request.POST.get('message')
        file = request.FILES.get('file')
        if not file.name.endswith('.zip'):
            messages.warning(request, "Please upload a ZIP file.")
            return redirect('order_detail', order_slug=order.slug)

        u_id = uuid.uuid4()
        slug = slugify(f"Delivery-for-Order-{order.slug}-{u_id}")

        prev_delivery = Delivery.objects.filter(order=order).first()
        if prev_delivery:
            prev_delivery.delete()

        delivery = Delivery.objects.create(order=order, developer=request.user, message=message, file=file, slug=slug)

        order.is_delivered = True
        order.status = "delivered"
        order.save()
        Notification.objects.create(user=order.user, app_name="workprenair", message=f"Your order has been delivered by {request.user.name}.")
        delivery_review_url = request.build_absolute_uri(reverse('order_detail', args=[order.slug]))
        # Send Email to Client
        client_email_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
            <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                <!-- Header -->
                <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                    <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo"  style="max-width: 150px;">
                </div>

                <!-- Body -->
                <div style="padding: 20px;">
                    <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">📦 Your Order #{order.id} Has Been Delivered!</h2>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {order.user.username},</p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                        The seller has delivered your order on <strong>FirePrenair</strong>. You can review and download the delivered work at your earliest convenience.
                    </p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Order Details:</strong></p>
                    <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                        <li style="margin-bottom: 10px;"><strong>Order ID:</strong> {order.id}</li>
                        <li style="margin-bottom: 10px;"><strong>Seller:</strong> {order.gig.user.username}</li>
                        <li style="margin-bottom: 10px;"><strong>Product/Service:</strong> {order.gig.title}</li>
                        <li style="margin-bottom: 10px;"><strong>Amount:</strong> ${order.price}</li>
                    </ul>
                    <p style="text-align: center; margin: 20px 0;">
                        <a href="{delivery_review_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">📂 Review & Download</a>
                    </p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">If you have any issues with the delivered work, feel free to contact support.</p>
                </div>

                <!-- Footer -->
                <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                    <p style="margin: 0; font-size: 14px;">Thank you for choosing FirePrenair! 🚀</p>
                    <p style="margin: 0; font-size: 14px;">The FirePrenair Team</p>
                </div>
            </div>
        </body>
        </html>
        """

        send_email(order.user.email, f"📦 Order Delivered! #{order.id}", client_email_content)

        messages.success(request, "Delivery submitted successfully.")

        return redirect('order_detail', order_slug=order.slug)

    context = {
        'order': order
    }
    return render(request, 'work_prenair/order_delivery.html', context)


@login_required
def request_revision(request, delivery_slug):
    delivery = Delivery.objects.get(slug=delivery_slug)
    order = delivery.order
    if request.user != delivery.order.user:
        messages.warning(request, "You are not authorized to view this page.")
        return redirect('work_home')
    
    if order.is_completed:
        messages.warning(request, "Order has already been completed.")
        return redirect('order_detail', order_slug=order.slug)
    
    if not order.is_delivered:
        messages.warning(request, "Order is not yet delivered.")
        return redirect('order_detail', order_slug=order.slug)
    
    if request.method == 'POST':
        message = request.POST.get('message')
        u_id = uuid.uuid4()
        slug = slugify(f"Revision-Request-for-Delivery-{delivery.slug}-{u_id}")
        RevisionRequest.objects.create(delivery=delivery, client=order.user, message=message, slug=slug)
        order.is_completed = False
        order.is_delivered = False
        order.status = "active"
        order.completed_on = None
        order.save()
        messages.success(request, "Revision request sent.")
        Notification.objects.create(user=delivery.developer, app_name="workprenair", message=f"Revision request received for order.")
        revision_request_url = request.build_absolute_uri(reverse('order_detail', args=[order.slug]))
        # Send Email to Seller
        seller_revision_email_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
            <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                <!-- Header -->
                <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                    <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                </div>

                <!-- Body -->
                <div style="padding: 20px;">
                    <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🔄 Revision Requested for Order #{order.id}</h2>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {delivery.developer.username},</p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                        The client has requested a revision for the delivery of <strong>Order #{order.id}</strong> on <strong>FirePrenair</strong>. Please review the client's feedback and make the necessary updates.
                    </p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Order Details:</strong></p>
                    <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                        <li style="margin-bottom: 10px;"><strong>Order ID:</strong> {order.id}</li>
                        <li style="margin-bottom: 10px;"><strong>Client:</strong> {order.user.username}</li>
                        <li style="margin-bottom: 10px;"><strong>Product/Service:</strong> {order.gig.title}</li>
                        <li style="margin-bottom: 10px;"><strong>Amount:</strong> ${order.price}</li>
                    </ul>
                    <p style="text-align: center; margin: 20px 0;">
                        <a href="{revision_request_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">📂 View Revision Request</a>
                    </p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                        Thank you for your commitment to excellence. Let’s ensure the client’s requirements are met.
                    </p>
                </div>

                <!-- Footer -->
                <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                    <p style="margin: 0; font-size: 14px;">Thank you for choosing FirePrenair! 🚀</p>
                    <p style="margin: 0; font-size: 14px;">The FirePrenair Team</p>
                </div>
            </div>
        </body>
        </html>
        """
        send_email(delivery.developer.email, f"🔄 Revision Requested for Order #{order.id}", seller_revision_email_content)

        return redirect('order_detail', order_slug=delivery.order.slug)
    
    context = {
        'delivery': delivery
    }

    return render(request, 'work_prenair/request_revision.html', context)



@login_required
def complete_order(request, order_slug):
    order = Order.objects.get(slug=order_slug)
    if request.user != order.user and request.user != order.gig.user:
        messages.warning(request, "You are not authorized to view this page.")
        return redirect('work_home')

    order.is_completed = True
    order.completed_on = timezone.now()
    order.status = "completed"
    order.save()

    order_amount = order.price - (order.price * Decimal('0.17'))

    order.gig.user.work_total_earnings += order_amount
    order.gig.user.total_earnings += order_amount
    order.gig.user.available_earnings += order_amount
    order.gig.user.save()
    messages.success(request, "Order marked as completed.")
    Notification.objects.create(user=order.gig.user, app_name="workprenair", message=f"Order completed by {order.user.username}.")
    # Build Client Email Content
    client_email_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
        <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
            <!-- Header -->
            <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
            </div>

            <!-- Body -->
            <div style="padding: 20px;">
                <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🎉 Order Completed Successfully! #{order.id}</h2>
                <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {order.user.username},</p>
                <p style="color: #333; font-size: 16px; line-height: 1.6;">
                    Your order for <strong>{order.gig.title}</strong> has been successfully completed on <strong>FirePrenair</strong>. Thank you for trusting us!
                </p>
                <p style="color: #333; font-size: 16px; line-height: 1.6;">
                    <strong>Order Summary:</strong>
                </p>
                <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                    <li style="margin-bottom: 10px;"><strong>Order ID:</strong> {order.id}</li>
                    <li style="margin-bottom: 10px;"><strong>Product/Service:</strong> {order.gig.title}</li>
                    <li style="margin-bottom: 10px;"><strong>Amount Paid:</strong> ${order.price}</li>
                    <li style="margin-bottom: 10px;"><strong>Completion Date:</strong> {order.completed_on.strftime('%B %d, %Y')}</li>
                </ul>
                <p style="color: #333; font-size: 16px; line-height: 1.6;">We hope to see you again for your future needs. 🚀</p>
            </div>

            <!-- Footer -->
            <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                <p style="margin: 0; font-size: 14px;">Thank you for choosing FirePrenair!</p>
                <p style="margin: 0; font-size: 14px;">The FirePrenair Team</p>
            </div>
        </div>
    </body>
    </html>
    """
    send_email(order.user.email, f"🎉 Order #{order.id} Completed Successfully!", client_email_content)

    # Build Seller Email Content
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
                <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🎉 Order Completed and Earnings Added! #{order.id}</h2>
                <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {order.gig.user.username},</p>
                <p style="color: #333; font-size: 16px; line-height: 1.6;">
                    Great job! Your order for <strong>{order.gig.title}</strong> has been marked as completed by the client on <strong>FirePrenair</strong>.
                </p>
                <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Order Summary:</strong></p>
                <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                    <li style="margin-bottom: 10px;"><strong>Order ID:</strong> {order.id}</li>
                    <li style="margin-bottom: 10px;"><strong>Client:</strong> {order.user.username}</li>
                    <li style="margin-bottom: 10px;"><strong>Product/Service:</strong> {order.gig.title}</li>
                    <li style="margin-bottom: 10px;"><strong>Earnings Added:</strong> ${order_amount}</li>
                    <li style="margin-bottom: 10px;"><strong>Completion Date:</strong> {order.completed_on.strftime('%B %d, %Y')}</li>
                </ul>
                <p style="color: #333; font-size: 16px; line-height: 1.6;">
                    Your earnings have been added to your account and are now available. Thank you for delivering excellence!
                </p>
            </div>

            <!-- Footer -->
            <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                <p style="margin: 0; font-size: 14px;">Thank you for being an amazing seller on FirePrenair!</p>
                <p style="margin: 0; font-size: 14px;">The FirePrenair Team</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Send email to seller
    send_email(order.gig.user.email, f"🎉 Order #{order.id} Completed and Earnings Added!", seller_email_content)
    return redirect('order_detail', order_slug=order.slug)

@login_required
def review_order(request, order_slug):
    order = Order.objects.get(slug=order_slug)
    if request.user != order.user and request.user != order.gig.user:
        return redirect('work_home')

    if request.method == 'POST':
        rating = request.POST.get('rating')
        review = request.POST.get('review')
        is_client_review = True if request.user == order.user else False

        Review.objects.create(order=order, gig= order.gig, user=request.user, rating=rating, review=review, is_client_review=is_client_review)
        order.has_client_reviewed = True
        order.has_seller_reviewed = True if request.user == order.gig.user else False
        order.save()
        messages.success(request, "Review submitted successfully.")
        if is_client_review:
            Notification.objects.create(user=order.gig.user, app_name="workprenair", message=f"Order reviewed by {request.user.username}.")
        else:
            Notification.objects.create(user=order.user, app_name="workprenair", message=f"Order reviewed by {request.user.username}.")
        return redirect('order_detail', order_slug=order.slug)

    context = {
        'order': order
    }
    return render(request, 'work_prenair/order_detail.html', context)


# ------------------- Stripe -------------------

stripe.api_key = settings.STRIPE_SECRET_KEY
from decimal import Decimal


@login_required
def gig_checkout(request, gig_slug, package_type):
    user = request.user
    gig = get_object_or_404(Gig, slug=gig_slug)

    if package_type == "basic":
        # add 5% processing fee
        price = gig.basic_price + (gig.basic_price * Decimal('0.05'))
    elif package_type == "standard":
        price = gig.standard_price + (gig.standard_price * Decimal('0.05'))
    elif package_type == "premium":
        price = gig.premium_price + (gig.premium_price * Decimal('0.05'))
    else:
        return render(request, "profiles/error.html", {"error": "Invalid package type selected."})

    try:
        success_url = request.build_absolute_uri(reverse("buyer_dashboard"))
        cancel_url = request.build_absolute_uri(reverse("gig_detail", args=[gig.slug]))

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": f"{gig.title} - {package_type.capitalize()} \n Price: ${price} With 5% Processing Fee"},
                        "unit_amount": int(price * 100),
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

        return redirect(checkout_session.url, code=303)

    except Exception as e:
        return render(request, "profiles/error.html", {"error": str(e)})
    
@login_required
def custom_offer_checkout(request, offer_id):
    user = request.user
    offer = get_object_or_404(CustomOffer, id=offer_id, recipient=user)

    if offer.is_accepted:
        return render(request, "profiles/error.html", {"error": "This offer has already been paid for."})

    try:
        success_url = request.build_absolute_uri(reverse("buyer_dashboard"))
        cancel_url = request.build_absolute_uri(reverse("custom_offers_list"))

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": f"Custom Offer - {offer.description[:50]}... \n Price: ${offer.price} + 5% Processing Fee"},
                        "unit_amount": int((offer.price + offer.price*Decimal('0.05')) * 100),
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

        return redirect(checkout_session.url, code=303)

    except Exception as e:
        return render(request, "profiles/error.html", {"error": str(e)})
    

# ------------------- Email Notifications -------------------
import smtplib
from django.core.mail import EmailMultiAlternatives

def send_email(to_email, subject, html_content, plain_text="This is a plain text fallback."):
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        print("✅ Email sent successfully.")
    except smtplib.SMTPAuthenticationError as e:
        print("❌ Authentication error:", e)
    except smtplib.SMTPConnectError as e:
        print("❌ Connection error:", e)
    except smtplib.SMTPRecipientsRefused as e:
        print("❌ Recipient refused:", e.recipients)
    except smtplib.SMTPException as e:
        print("❌ General SMTP error:", e)
    except Exception as e:
        print("❌ Other error:", e)
        # Handle other errors
    
# ------------------- Stripe Webhooks -------------------

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET_GIG_ORDER
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        return JsonResponse({"error": str(e)}, status=400)

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
            order = Order.objects.create(user=user,gig=gig,package_type=package_type,price=price,is_paid=True, delivery_days=delivery)

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
                        <!-- Header -->
                        <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                            <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                        </div>

                        <!-- Body -->
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


            send_email(user.email, f"🛒 Order Confirmed! Your Order #{order.id} is Awaiting your requirements!", buyer_email_content)
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
                                    <li style="margin-bottom: 10px;"><strong>Buyer:</strong> {user.username}</li>
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
                delivery_days = offer.delivery_time
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
                    <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0,                 0.1);">
                        <!-- Header -->
                        <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                            <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                        </div>

                        <!-- Body -->
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
                                <a href="{buyer_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;                ">Submit Requirements</a>
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
                                <li style="margin-bottom: 10px;"><strong>Buyer:</strong> {user.username}</li>
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
    
    return JsonResponse({"status": "success"})



# ------------------- PayPal Checkouts -------------------
import paypalrestsdk
from paypalrestsdk import Payment

paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})

@login_required
def paypal_checkout(request, gig_slug, package_type):
    user = request.user
    gig = get_object_or_404(Gig, slug=gig_slug)

    if package_type == "basic":
        price = gig.basic_price + (gig.basic_price * Decimal('0.05'))
    elif package_type == "standard":
        price = gig.standard_price + (gig.standard_price * Decimal('0.05'))
    elif package_type == "premium":
        price = gig.premium_price + (gig.premium_price * Decimal('0.05'))
    else:
        return render(request, "profiles/error.html", {"error": "Invalid package type selected."})

    success_url = request.build_absolute_uri(reverse("paypal_success"))
    cancel_url = request.build_absolute_uri(reverse("paypal_cancel"))

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
        for link in payment.links:
            if link.rel == "approval_url":
                return redirect(link.href)
    else:
        return render(request, "profiles/error.html", {"error": "Failed to create PayPal payment."})
    

def paypal_success(request):
    payment_id = request.GET.get("paymentId")
    payer_id = request.GET.get("PayerID")

    if not payment_id or not payer_id:
        return render(request, "profiles/error.html", {"error": "Invalid PayPal payment details."})

    payment = Payment.find(payment_id)
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

        order = Order.objects.create(
            user=request.user,
            gig=gig,
            package_type=package_type,
            price=price,
            is_paid=True,
            delivery_days=delivery_date
        )

        Notification.objects.create(
            user=gig.user,
            app_name="workprenair",
            message=f"You have received a new order from {request.user.username}. Let's Wait for client's Requirements"
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
        send_email(gig.user.email, f"🎉 New Order Received! #{order.id}", seller_email_content)
        messages.success(request, "Order placed successfully, Submit your requirements to activate the order.")
        return redirect("buyer_dashboard")
    else:
        return render(request, "profiles/error.html", {"error": "PayPal payment execution failed."})
    

@login_required
def custom_offer_paypal_checkout(request, offer_id):
    user = request.user
    offer = get_object_or_404(CustomOffer, id=offer_id, recipient=user)

    if offer.is_accepted:
        return render(request, "profiles/error.html", {"error": "This offer has already been paid for."})

    price = offer.price + (offer.price * Decimal('0.05'))
    success_url = request.build_absolute_uri(reverse("custom_offer_paypal_success"))
    cancel_url = request.build_absolute_uri(reverse("paypal_cancel"))

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

    if payment.create():
        for link in payment.links:
            if link.rel == "approval_url":
                return redirect(link.href)
    else:
        return render(request, "profiles/error.html", {"error": "Failed to create PayPal payment."})


@login_required
def custom_offer_paypal_success(request):
    payment_id = request.GET.get("paymentId")
    payer_id = request.GET.get("PayerID")

    if not payment_id or not payer_id:
        return render(request, "profiles/error.html", {"error": "Invalid PayPal payment details."})

    payment = Payment.find(payment_id)
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
            message=f"You have received a new order from {request.user.username}. Let's Wait for client's Requirements"
        )

        buyer_url = request.build_absolute_uri(reverse("order_detail", args=[order.slug]))
        # Send Email to Buyer
        buyer_email_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
                <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0,                 0.1);">
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
                            <a href="{buyer_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;                ">Submit Requirements</a>
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
        messages.success(request, "Payment successful. Order placed successfully, Submit your requirements to start the order.")
        return redirect("buyer_dashboard")
    else:
        return render(request, "profiles/error.html", {"error": "PayPal payment execution failed."})


    
def paypal_cancel(request):
    return render(request, "profiles/error.html", {"error": "Payment canceled by the user."})




# --------------  Custom Offers ---------------------------
@login_required
def custom_offers_list(request):
    custom_offers_sent = None
    custom_offers_received = None
    if request.user.is_work_freelancer:
        custom_offers_sent = CustomOffer.objects.filter(sender=request.user)

    else:
        custom_offers_received = CustomOffer.objects.filter(recipient=request.user, is_declined=False)

    context = {
        'custom_offers_sent': custom_offers_sent,
        'custom_offers_received': custom_offers_received
    }
    return render(request, 'work_prenair/custom_offers_list.html', context)


@login_required
def create_offer(request):
    if not request.user.is_work_freelancer:
        messages.warning(request, "You must be a freelancer to send offers.")
        return redirect('work_home')

    if request.method == "POST":
        gig_slug = request.POST.get('gig')
        recipient_slug = request.POST.get('recipient')
        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        delivery_time = request.POST.get('delivery_time')

        gig = get_object_or_404(Gig, slug=gig_slug, user=request.user)
        recipient = get_object_or_404(User, username=recipient_slug)

        CustomOffer.objects.create(
            gig=gig,
            sender=request.user,
            recipient=recipient,
            title=title,
            description=description,
            price=price,
            delivery_time=delivery_time,
        )
        messages.success(request, "Offer sent successfully.")
        Notification.objects.create(user=recipient, app_name="workprenair", message=f"New offer received from {request.user.username}.")
        # Build absolute URL for the custom offers list
        custom_offers_url = request.build_absolute_uri(reverse('custom_offers_list'))

        # Email Content for Client
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
        send_email(
            recipient.email,
            subject=f"🎉 New Offer Received from {request.user.username}",
            html_content=offer_email_content
        )

        return redirect('custom_offers_list')

    return render(request, 'work_prenair/custom_offers_list.html')


@login_required
@require_POST
def generate_proposal_description(request):
    if not request.user.is_work_freelancer:
        return JsonResponse({'error': 'You are not authorized to perform this action.'}, status=403)
    try:
        data = json.loads(request.body)
        prompt = data.get('prompt', '')
        gig_slug = data.get('gig_slug', '')
        
        if not prompt or not gig_slug:
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        gig = get_object_or_404(Gig, slug=gig_slug)
        if gig.user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        ai_prompt = f"""
        Act as a professional freelance proposal writer. Generate a compelling project proposal description based on:
        
        Client's Requirements: {prompt}
        Service Being Offered: {gig.title}
        Service Description: {gig.description}
        Service Category: {gig.category_level_1}, {gig.category_level_2}, {gig.category_level_3}
        
        Guidelines:
        - Keep it professional yet friendly
        - Highlight key benefits for the client
        - Mention relevant experience
        - 300-500 characters
        - Use bullet points if needed
        - Focus on client outcomes
        
        Return ONLY the proposal text without any formatting or markdown.
        """

        # Get AI response
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": ai_prompt}],
            temperature=0.7,
            max_tokens=500
        )

        description = response.choices[0].message.content.strip()
        return JsonResponse({'description': description})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def decline_offer(request, offer_id):
    offer = CustomOffer.objects.get(id=offer_id)
    if request.user != offer.recipient:
        messages.warning(request, "You are not authorized to perform this action.")
        return redirect('work_home')
    offer.is_declined = True
    offer.save()
    messages.success(request, "Offer declined successfully.")
    Notification.objects.create(user=offer.sender, app_name="workprenair", message=f"Your offer has been declined by {request.user.username}.")
    return redirect('custom_offers_list')


@login_required
def delete_offer(request, offer_id):
    offer = CustomOffer.objects.get(id=offer_id)
    if request.user != offer.sender:
        messages.warning(request, "You are not authorized to perform this action.")
        return redirect('work_home')
    offer.delete()
    messages.success(request, "Offer deleted successfully.")
    return redirect('custom_offers_list')








# ------------------- MESSAGES -------------------
@login_required
def user_chats(request):
    search_query = request.GET.get('search', '') 
    user_chats = request.user.get_work_chats()

    if search_query:
        user_chats = user_chats.filter(
            Q(user1__name__icontains=search_query) | Q(user2__name__icontains=search_query)
        )

    chats_with_last_message = []
    for user_chat in user_chats:
        time = timezone.now()
        last_message = user_chat.chat_messages.order_by('-timestamp').first()
        unread_count = user_chat.chat_messages.filter(is_read=False, receiver=request.user).count()
        if last_message:
            time = last_message.timestamp
        chats_with_last_message.append((user_chat, last_message, time, unread_count))

    context = {
        'user_chats': chats_with_last_message,
        'search_query': search_query, 
    }

    return render(request, 'work_prenair/user_chats.html', context)


@login_required
def user_chat(request, chatSlug):

    chat = PrivateChat.objects.filter(slug=chatSlug, commu_prenair_chat=False).first()

    if not chat:
        other_user_slug = request.GET.get('user_slug')
        other_user = get_object_or_404(User, slug=other_user_slug)

        chat = PrivateChat.objects.filter(
            (Q(user1=request.user, commu_prenair_chat=False) & Q(user2=other_user, commu_prenair_chat=False)) | (Q(user1=other_user, commu_prenair_chat=False) & Q(user2=request.user, commu_prenair_chat=False))
        ).first()

        if not chat:
            unique_uuid = uuid.uuid4()
            slug = slugify(f"{request.user.username}-{other_user.username}-work-{unique_uuid}")
            chat = PrivateChat.objects.create(user1=request.user, user2=other_user, slug=slug, commu_prenair_chat=False)
            Notification.objects.create(user=other_user, app_name="workprenair", message=f"{request.user.username} has Started a Chat on Workprenair!.")
        return redirect('user_chat', chatSlug=chat.slug)

    
    chat_messages = chat.chat_messages.all()
    other_user = chat.user1 if chat.user1 != request.user else chat.user2
    chat.chat_messages.filter(is_read=False, receiver=request.user).update(is_read=True)
    user_chats = request.user.get_work_chats()
    
    chats_with_last_message = []
    for user_chat in user_chats:
        last_message = user_chat.chat_messages.order_by('-timestamp').first()
        unread_count = user_chat.chat_messages.filter(is_read=False, receiver=request.user).count()
        time = timezone.now()
        if last_message:
            time = last_message.timestamp
        chats_with_last_message.append((user_chat, last_message, time, unread_count))

    user_gigs = Gig.objects.filter(user=request.user)

    context = {
        'chatSlug': chatSlug,
        'chat_with': chat,
        'chat_messages': chat_messages,
        'other_user': other_user,
        'user_chats': chats_with_last_message,
        'user_gigs': user_gigs,
    }
    return render(request, 'work_prenair/user_chat.html', context)


@require_POST
@login_required
def ai_chat_assist(request, chatSlug):
    chat = get_object_or_404(PrivateChat, slug=chatSlug)
    if request.user not in [chat.user1, chat.user2]:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        context = data.get('context', '')
        recent_messages = data.get('recent_messages', [])
        formatted_messages = []
        for msg in recent_messages:
            if isinstance(msg, dict):
                # New format with sender_role and content
                formatted_messages.append(f"{msg.get('sender_role', 'Unknown')}: {msg.get('content', '')}")
            else:
                # Fallback for old string format
                formatted_messages.append(str(msg))

        role = "freelancer" if request.user.is_work_freelancer else "client"
        
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

        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200
        )
        
        raw_output = response.choices[0].message.content.strip()
        suggestions = []
        
        for line in raw_output.split('\n'):
            cleaned = re.sub(r'^\d+\.\s*', '', line).strip()
            if cleaned and len(cleaned) > 10:  
                suggestions.append(cleaned)
        print(suggestions)
        return JsonResponse({
            'suggestions': suggestions[:3]  
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)






# ------------------- Categories -------------------
# Get top-level categories
def get_top_categories(request):
    top_categories = Category.objects.filter(parent__isnull=True).values('id', 'name', 'description')
    return JsonResponse({'categories': list(top_categories)})


def get_subcategories(request, category_id):
    level_2_categories = Category.objects.filter(parent_id=category_id)

    data = []
    for category in level_2_categories:
        children = category.subcategories.all()
        child_data = [
            {"id": child.id, "name": child.name, "url": f"#"}
            for child in children
        ]
        data.append({
            "id": category.id,
            "name": category.name,
            "children": child_data
        })

    return JsonResponse({"level_2_categories": data})




# becom seller
@login_required
def become_seller(request):
    if request.user.is_work_profile_approved:
        messages.warning(request, "You are already a seller on Workprenair.")
        return redirect('sellor_dashboard')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        phone_no = request.POST.get('phone')
        country = request.POST.get('country')
        bio = request.POST.get('about')
        portfolio_link = request.POST.get('portfolio')
        expertise = request.POST.get('expertise')

        if not name or not phone_no or not country or not bio or not expertise:
            messages.warning(request, "All fields are required.")
            return redirect('become_seller')
        
        request.user.name = name
        request.user.phone_no = phone_no
        request.user.country = country
        request.user.work_bio = bio
        request.user.work_expertise = expertise
        request.user.portfolio_link = portfolio_link
        request.user.is_work_profile_approved = True
        request.user.is_work_freelancer = True
        request.user.save()
        messages.success(request, "You are now a seller on Workprenair.")
        return redirect('create_gig')
    return render(request, 'work_prenair/become_seller.html')


@login_required
def toggle_profile(request):
    """
    Toggle between Workprenair Buyer and Seller profile for the logged-in user.
    """
    if request.user.is_work_freelancer:
        request.user.is_work_freelancer = False
        request.user.save() 
        messages.success(request, "Switched to Workprenair Buyer")
        return redirect('buyer_dashboard')  
    else:
        if request.user.is_work_profile_approved:
            request.user.is_work_freelancer = True
            request.user.save()  
            messages.success(request, "Switched to Workprenair Seller")
            return redirect('sellor_dashboard')  
        else:
            messages.error(request, "Your seller profile is not approved. Please approve it.")
            return redirect('buyer_dashboard')



# response = client.images.generate(
#     model="dall-e-3",
#     prompt="a white siamese cat",
#     size="1024x1024",
#     quality="standard",
#     n=1,
# )

# print(response.data[0].url)
