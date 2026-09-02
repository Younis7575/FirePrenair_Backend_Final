from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from digi_prenair.models import *
from edu_prenair.models import *
from work_prenair.models import *
from work_prenair.models import Order as WorkOrder
from commu_prenair.models import *
from .forms import *
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.http import Http404
from django.db.models import Sum, Count, Max, functions
from django.db.models.functions import ExtractMonth
import calendar
from profiles.models import Notification
from decimal import Decimal
from django.core.paginator import Paginator
from django.db.models import Q
from .decorators import admin_not_allowed  
from openai import OpenAI
import requests
import time
import dateutil.relativedelta
from datetime import datetime, timedelta
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.db import transaction, IntegrityError
from django.db.models import Avg
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
import docraptor
from django.core.mail import EmailMessage
from .utils.plans import get_active_plan_name
from django.http import HttpResponseNotFound
import stripe

# ai
from django.views.decorators.csrf import csrf_exempt
import json
from groq import Groq
from django.utils.html import mark_safe
import markdown
from django.http import JsonResponse, HttpResponseForbidden
from django.conf import settings
from work_prenair.views import send_email
import os

client = OpenAI(api_key=settings.OPENAI_API_KEY)
# knowledge_base = {
#     "main_dashboard": {
#         "description": (
#             "The main dashboard of Fireprenair provides access to the individual dashboards of the four apps "
#             "(Workprenair, Digiprenair, Eduprenair, and Commuprenair), along with sections for user settings and payouts."
#         ),
#         "sections": {
#             "workprenair_dashboard": {
#                 "description": (
#                     "The Workprenair dashboard allows freelancers and clients to manage their services, view ongoing projects, "
#                     "and communicate with clients or freelancers. Key features include managing gigs, tracking earnings, and reviewing feedback."
#                 ),
#                 "faq": {
#                     "How do I manage my services as a freelancer?": (
#                         "In the Workprenair dashboard, go to the 'My Gigs' section to create, update, or remove services you offer. "
#                         "You can also track ongoing projects and manage client communication."
#                     ),
#                     "Can I track my earnings?": (
#                         "Yes, the 'Earnings' section provides a detailed view of your income, including completed and ongoing projects."
#                     ),
#                 }
#             },
#             "digiprenair_dashboard": {
#                 "description": (
#                     "The Digiprenair dashboard helps digital product sellers manage their products, view sales data, and track customer orders."
#                 ),
#                 "faq": {
#                     "How do I add new products?": (
#                         "Go to the 'Products' section and click 'Add Product'. Fill in the product details, upload media, and set the price."
#                     ),
#                     "Can I view customer orders?": (
#                         "Yes, the 'Orders' section provides a list of all customer orders, allowing you to manage each sale."
#                     ),
#                 }
#             },
#             "eduprenair_dashboard": {
#                 "description": (
#                     "The Eduprenair dashboard enables course creators to manage their courses, track student enrollments, and analyze course performance."
#                 ),
#                 "faq": {
#                     "How do I create a new course?": (
#                         "In the 'Courses' section, click 'Create New Course', and fill in the course content, description, and pricing."
#                     ),
#                     "How can I track student progress?": (
#                         "The 'Students' section provides detailed insights into student enrollments, progress, and feedback."
#                     ),
#                 }
#             },
#             "commupenair_dashboard": {
#                 "description": (
#                     "The Commuprenair dashboard allows users to manage their professional connections, create posts, and explore networking opportunities."
#                 ),
#                 "faq": {
#                     "How do I connect with other professionals?": (
#                         "You can search for professionals in the 'Explore' section and send connection requests to those you wish to connect with."
#                     ),
#                     "Can I create posts or share updates?": (
#                         "Yes, the 'Feed' section allows you to create posts, share updates, and engage with your network."
#                     ),
#                 }
#             },
#             "user_settings": {
#                 "description": (
#                     "The user settings section allows users to update their personal information, change passwords, and adjust their notification preferences."
#                 ),
#                 "faq": {
#                     "How do I change my password?": (
#                         "Go to 'Settings', select 'Security', and click 'Change Password'. Follow the prompts to reset your password."
#                     ),
#                     "Can I update my email address?": (
#                         "Yes, in the 'Profile' section, you can update your email address along with other personal information."
#                     ),
#                 }
#             },
#             "payouts": {
#                 "description": (
#                     "The payouts section enables freelancers and sellers to withdraw their earnings. Users can manage payout methods and view transaction history."
#                 ),
#                 "faq": {
#                     "How do I withdraw my earnings?": (
#                         "In the 'Payouts' section, click 'Withdraw' and choose your preferred payout method (e.g., PayPal, bank transfer)."
#                     ),
#                     "Can I view my payout history?": (
#                         "Yes, the 'Transaction History' section displays a log of all past payouts and related details."
#                     ),
#                 }
#             }
#         }
#     }
# }


# @csrf_exempt
# def dashboard_chatbot_view(request):
#     if request.method == 'POST':
#         user_message = request.POST.get('message', '').lower()

#         # Predefined responses for quick replies
#         predefined_responses = {
#             "name": "I am your customer support assistant, here to help you with any questions about Workprenair.",
#             "who_created_you": "I was created by the development team of Fireprenair.",
#             "what_can_you_do": "I can help you navigate our platform, answer questions about our services, and provide consultation details.",
#         }

#         for key, response in predefined_responses.items():
#             if key in user_message:
#                 return JsonResponse({"message": response})

#         # Interact with Groq API
#         client = Groq(api_key=settings.GROQ_API_KEY)
#         groq_response = client.chat.completions.create(
#             messages=[
#                 {"role": "system", "content": json.dumps({
#                     "knowledge_base": knowledge_base,
#                     "instruction": "Please generate short, clear, and professional responses. "
#                                    "Limit unnecessary details, ensure the tone is formal, and provide concise answers. "
#                                    "Avoid elaboration and keep responses to the point."
#                                    "Give answer according to question."
#                 })},
#                 {"role": "user", "content": user_message},
#             ],
#             model="llama3-8b-8192",
#         )

#         # Process the Groq response
#         bot_reply = groq_response.choices[0].message.content.strip()
#         bot_reply_html = markdown.markdown(bot_reply)
#         bot_reply_html = mark_safe(bot_reply_html)

#         return JsonResponse({"message": bot_reply_html})

#     return JsonResponse({"message": "Only POST requests are allowed."}, status=400)


@admin_not_allowed
@login_required
def dashboard_home(request):
    user = request.user
    completion_percentage = user.profile_completion_percentage()
    missing_fields = user.missing_profile_fields()
    
    all_fields = ['name', 'bio', 'profile_pic', 'phone_no', 'age', 'country']
    
    withdraw_requests = WithdrawalRequest.objects.filter(user=user).order_by(
        "-created_at"
    )
    context = {
        "user": user,
        "withdraw_requests": withdraw_requests,
        "completion_percentage": completion_percentage,
        "missing_fields": missing_fields,
        "all_fields": all_fields,
    }
    return render(request, "dashboard/dashboard_home.html", context)


@login_required
def my_referrals(request):
    user = request.user
    
    # Handle POST request for setting referral code
    if request.method == 'POST':
        referral_code = request.POST.get('referral_code', '').strip()
        
        # Validate referral code
        if not referral_code:
            messages.error(request, 'Please enter a referral code.')
            return redirect('my_referrals')
        
        # Check if referral code contains only letters and numbers
        if not re.match("^[A-Za-z0-9]+$", referral_code):
            messages.error(request, 'Referral code can only contain letters and numbers.')
            return redirect('my_referrals')
        
        # Check length (optional - adjust as needed)
        if len(referral_code) < 3 or len(referral_code) > 20:
            messages.error(request, 'Referral code must be between 3 and 20 characters.')
            return redirect('my_referrals')
        
        try:
            # Set the referral code for the user
            user.referral_code = referral_code
            user.save()
            messages.success(request, 'Your referral code has been set successfully!')
            return redirect('my_referrals')
        except IntegrityError:
            messages.error(request, 'This referral code is already taken. Please choose another one.')
            return redirect('my_referrals')
    
    # Get referrals (users who were referred by current user)
    referrals = user.referrals.all().order_by('-created_at')
    
    # Calculate stats
    total_referrals = referrals.count()
    active_referrals = referrals.filter(has_listed_and_sold=True).count()
    
    # Calculate success rate
    success_rate = 0
    if total_referrals > 0:
        success_rate = round((active_referrals / total_referrals) * 100, 1)
    
    # Generate referral link
    referral_link = None
    if user.referral_code:
        referral_link = f"https://fireprenair.com/?register=true&referral_code={user.referral_code}"
    
    context = {
        'referrals': referrals,
        'total_referrals': total_referrals,
        'active_referrals': active_referrals,
        'success_rate': success_rate,
        'referral_link': referral_link,
    }
    
    return render(request, "dashboard/my_referrals.html", context)


# ----------------------------------------- Website Builder ---------------
@login_required
def my_websites(request):
    user_websites = UserWebsite.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'dashboard/my_webs.html', {'user_websites': user_websites})


@login_required
def create_website(request):
    user = request.user
    plan_name = get_active_plan_name(user)

    existing_count = UserWebsite.objects.filter(user=user).count()

    if plan_name == "FreeTier" and existing_count >= 1:
        messages.error(request, "FreeTier users can create only 1 website. Upgrade to create more.")
        return redirect('my_websites') 
    elif plan_name == "StartPrenair" and existing_count >= 5:
        messages.error(request, "StartPrenair users can create up to 5 websites. Upgrade to create more.")
        return redirect('my_websites') 

    if request.method == 'POST':
        request.session['new_website_name'] = request.POST.get('website_name')
        request.session['selected_parent_category_id'] = request.POST.get('parent_category')
        request.session['selected_child_category_id'] = request.POST.get('child_category')
        return redirect('select_template')
    
    parent_categories = TemplateCategory.objects.filter(parent__isnull=True)
    return render(request, 'dashboard/website_name.html', {'parent_categories': parent_categories})



def get_template_categories(request):
    parent_id = request.GET.get('parent_id')
    child_categories = TemplateCategory.objects.filter(parent_id=parent_id).values('id', 'name')
    return JsonResponse(list(child_categories), safe=False)

def select_template(request):
    if 'new_website_name' not in request.session or 'selected_child_category_id' not in request.session:
        messages.error(request, 'Please provide a website name and select a category first.')
        return redirect('create_website')
    
    child_category_id = request.session.get('selected_child_category_id')
    templates = Template.objects.filter(category_id=child_category_id)
    category = TemplateCategory.objects.get(id=child_category_id) if child_category_id else None

    return render(request, 'dashboard/select_template.html', {'templates': templates, 'selected_category': category})


@login_required
def create_from_template(request, template_id):
    # Step 3: Create website and open editor
    if 'new_website_name' not in request.session:
        return redirect('create_website')
    
    template = get_object_or_404(Template, id=template_id)
    website_name = request.session.pop('new_website_name')
    
    user_website = UserWebsite.objects.create(
        user=request.user,
        name=website_name,
        template=template,
        edited_html=template.html_content
    )
    return redirect('edit_website', website_id=user_website.id)


@login_required
def edit_website(request, website_id):
    user_website = get_object_or_404(UserWebsite, id=website_id, user=request.user)
    parent_category = None
    product_type = None
    
    if user_website.template and user_website.template.category:
        parent_category = user_website.template.category.parent.name
        # Determine product type
        if parent_category == 'Digiprenair':
            product_type = 'product'
            products = Product.objects.filter(seller=request.user)
        elif parent_category == 'Workprenair':
            product_type = 'gig'
            products = Gig.objects.filter(user=request.user)
        elif parent_category == 'Eduprenair':
            product_type = 'course'
            products = Course.objects.filter(instructor=request.user)
        else:
            products = []
    else:
        products = []

    return render(request, 'dashboard/editor.html', {
        'user_website': user_website,
        'products': products,
        'product_type': product_type
    })

@login_required
@csrf_exempt
def publish_website_ajax(request, website_id):
    if request.method == "POST":
        website = get_object_or_404(UserWebsite, id=website_id, user=request.user)
        publish_type = request.POST.get("publish_type")
        
        # Subdomain publishing
        if publish_type == "subdomain":
            subdomain = request.POST.get("subdomain", "").strip().lower()
            full_subdomain = f"{subdomain}.fireprenair.com"
            
            if not subdomain or " " in subdomain:
                return JsonResponse({"success": False, "error": "Invalid subdomain."})
                
            if UserWebsite.objects.filter(subdomain=full_subdomain).exclude(id=website.id).exists():
                return JsonResponse({"success": False, "error": "Subdomain is already taken."})
            
            website.subdomain = full_subdomain
            website.custom_domain = None 
            website.is_published = True
            website.save()
            return JsonResponse({"success": True, "url": f"https://{full_subdomain}"})
        
        # Custom domain publishing
        elif publish_type == "custom_domain":
            custom_domain = request.POST.get("custom_domain", "").strip().lower()
            
            if not custom_domain:
                return JsonResponse({"success": False, "error": "Please enter a domain."})
                
            if " " in custom_domain or not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", custom_domain):
                return JsonResponse({"success": False, "error": "Invalid domain format."})
                
            if UserWebsite.objects.filter(custom_domain=custom_domain).exclude(id=website.id).exists():
                return JsonResponse({"success": False, "error": "Domain is already in use."})
            
            website.custom_domain = custom_domain
            website.subdomain = None 
            website.is_published = True
            website.save()
            return JsonResponse({
                "success": True,
                "dns_info": {
                    "record_type": "A",
                    "host": "@",
                    "value": "3.21.28.122"
                }
            })
        
        return JsonResponse({"success": False, "error": "Invalid publish type."})

    return JsonResponse({"success": False, "error": "Invalid request."})

def live_website_view(request):
    website = getattr(request, "website", None)
    if website is None:
        return HttpResponseNotFound("Website not found")
    # return HttpResponse(website.html_code)
    return render(request, 'dashboard/live_website.html', {'website': website})

@login_required
def delete_website(request, website_id):
    user_website = get_object_or_404(UserWebsite, id=website_id, user=request.user)
    user_website.delete()
    messages.success(request, 'Website deleted successfully.')
    return redirect('my_websites')

@login_required
def get_user_site_html(request, website_id):
    user_website = get_object_or_404(UserWebsite, id=website_id, user=request.user)
    return JsonResponse({'html': user_website.edited_html})

@csrf_exempt
@login_required
def save_website(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        website_id = data.get('website_id')
        html = data.get('html')
        user_website = get_object_or_404(UserWebsite, id=website_id, user=request.user)
        user_website.edited_html = html
        user_website.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)





# --------------------------- Funnels ----------------------
def serve_funnel_entry(request):
    if not getattr(request, "is_funnel", False) or not request.funnel:
        return HttpResponse("Invalid funnel or not published.", status=404)

    funnel = request.funnel
    first_step = funnel.steps.order_by("step_order").first()

    if not first_step:
        return HttpResponse("No steps configured for this funnel.", status=404)

    return redirect("funnel_step", step_order=first_step.step_order)


def serve_funnel_step(request, step_order):
    if not getattr(request, "is_funnel", False) or not request.funnel:
        return HttpResponse("Invalid funnel or not published.", status=404)

    funnel = request.funnel
    step = get_object_or_404(FunnelStep, funnel=funnel, step_order=step_order)

    # Track visitor
    if request.user.is_authenticated:
        funnel.visitors.add(request.user)

    # Handle form submissions based on step type
    if request.method == "POST":
        # Check if this is the lead capture form
        if 'email' in request.POST:
            FunnelLead.objects.create(
                funnel=funnel,
                name=request.POST.get("name", ""),
                email=request.POST.get("email"),
            )
            next_step = funnel.get_next_step(step_order)
            if next_step:
                return redirect("funnel_step", step_order=next_step.step_order)

    next_step = funnel.get_next_step(step_order)
    products = funnel.get_products()
    
    context = {
        "funnel": funnel,
        "step": step,
        "step_order": step_order,
        "next_step": next_step,
        "products": products,
        "step_html_content": step.user_website.edited_html,
    }

    # For step 2, add free product download URL
    if step_order == 2:
        context['product'] = products.filter(price__gt=0).first()
        free_product = products.filter(price=0).first()
        if free_product:
            context['free_product_download_url'] = (
                free_product.downloadable_file.url
                if free_product.downloadable_file
                else free_product.external_link
            )

    # For step 3 (thank you + premium upsell)
    if step_order == 3:
        # Get the first paid product for the upsell
        paid_products = products.filter(price__gt=0)
        if paid_products.exists():
            context['product'] = paid_products.first()
        else:
            # Fallback to any product if no paid products
            context['product'] = products.first()

    # For step 4 (final thank you), we'll handle separately
    if step_order == 4:
        order_id = request.GET.get('order_id')
        if order_id:
            context['order'] = get_object_or_404(FunnelOrder, id=order_id, funnel=funnel)

    return render(request, 'dashboard/run_funnel.html', context)


@require_POST
@csrf_exempt
def funnel_lead_api(request):
    try:
        data = json.loads(request.body)
        
        name = data.get('name', '')
        email = data.get('email')
        step_order = data.get('step_order')
        
        if not email:
            return JsonResponse({'success': False, 'error': 'Email is required'})
        
        # Get the funnel from the request (since you have request.funnel)
        if not getattr(request, "is_funnel", False) or not request.funnel:
            return JsonResponse({'success': False, 'error': 'Invalid funnel'})
        
        funnel = request.funnel
        
        # Create the lead
        FunnelLead.objects.create(
            funnel=funnel,
            name=name,
            email=email,
        )
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


stripe.api_key = settings.STRIPE_SECRET_KEY
def create_checkout_session(request, funnel_id, product_id):
    funnel = get_object_or_404(Funnel, id=funnel_id)
    product = get_object_or_404(FunnelProduct, id=product_id, funnel=funnel)

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': product.name,
                        'description': product.description,
                    },
                    'unit_amount': int(product.price * 100),
                },
                'quantity': 1,
            }],
            mode='payment',

            # redirect to payment success view
            success_url=request.build_absolute_uri(
                reverse("handle_payment_success", args=[funnel_id]) + "?session_id={CHECKOUT_SESSION_ID}"
            ),

            cancel_url=request.build_absolute_uri(
                reverse("funnel_step", args=[1])
            ),

            metadata={
                'funnel_id': funnel_id,
                'product_id': product_id,
            }
        )

        return redirect(checkout_session.url)

    except Exception as e:
        return JsonResponse({'error': str(e)})


def handle_payment_success(request, funnel_id):
    session_id = request.GET.get('session_id')

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        
        funnel = get_object_or_404(Funnel, id=funnel_id)
        product = FunnelProduct.objects.get(id=session.metadata['product_id'])

        order = FunnelOrder.objects.create(
            funnel=funnel,
            buyer=request.user if request.user.is_authenticated else None,
            product=product,
            stripe_payment_intent=session.payment_intent,
            stripe_session_id=session_id,
            amount_paid=product.price,
            status='paid'
        )

        # Redirect to Step 4 (Thank You Step)
        next_step = funnel.get_next_step(3)
        return redirect(
            reverse("funnel_step", args=[next_step.step_order]) + f"?order_id={order.id}"
        )

    except Exception as e:
        return HttpResponse(f"Error processing payment: {str(e)}")


@login_required
def funnel_list(request):
    funnels = Funnel.objects.filter(user=request.user)
    return render(request, 'dashboard/funnel_list.html', {'funnels': funnels})

@login_required
def create_funnel(request):
    if request.method == 'POST':
        name = request.POST['name']
        department = request.POST['department']
        tag = request.POST['tag']
        
        custom_tag = request.POST.get('custom_tag', '').strip()
        if custom_tag:
            custom_tag = custom_tag.lower().replace(' ', '_')
        funnel = Funnel.objects.create(
            user=request.user, 
            name=name, 
            department=department,
            tag=tag,
            custom_tag=custom_tag
        )
        return redirect('edit_funnel', funnel.id)
    
    existing_custom_tags = Funnel.objects.filter(
        user=request.user, 
        tag='custom',
        custom_tag__isnull=False
    ).exclude(custom_tag='').values_list('custom_tag', flat=True).distinct()

    return render(request, 'dashboard/create_funnel.html', {
        'existing_custom_tags': existing_custom_tags
    })


@login_required
def edit_funnel(request, funnel_id):
    funnel = get_object_or_404(Funnel, id=funnel_id, user=request.user)
    user_websites = UserWebsite.objects.filter(user=request.user)
    
    if request.method == 'POST':
        page_id = request.POST['user_website_id']
        goal = request.POST['goal_type']
        order = request.POST['step_order']
        FunnelStep.objects.create(
            funnel=funnel,
            user_website_id=page_id,
            goal_type=goal,
            step_order=order
        )
        return redirect('edit_funnel', funnel.id)

    steps = FunnelStep.objects.filter(funnel=funnel).order_by('step_order')
    return render(request, 'dashboard/edit_funnel.html', {
        'funnel': funnel,
        'steps': steps,
        'user_websites': user_websites
    })

@login_required
def delete_funnel(request, funnel_id):
    funnel = get_object_or_404(Funnel, id=funnel_id)
    funnel.delete()
    messages.success(request, f'Funnel "{funnel.name}" deleted successfully.')
    return redirect('funnel_list') 


def run_funnel(request, id):
    funnel = get_object_or_404(Funnel, id=id)
    steps = funnel.steps.order_by('step_order')

    current_step = int(request.GET.get('step', 1))

    try:
        step = steps[current_step - 1]
    except IndexError:
        return render(request, 'dashboard/finished.html') 

    return render(request, 'dashboard/run_step.html', {
        'funnel': funnel,
        'step': step,
        'next_step': current_step + 1 if current_step < len(steps) else None
    })


def live_funnel_view(request):
    funnel = getattr(request, "funnel", None)
    if funnel is None:
        return HttpResponseNotFound("Funnel not found")

    if request.user.is_authenticated and not request.user in funnel.visitors.all() and not request.user ==  funnel.user:
        funnel.visitors.add(request.user)
        funnel.save()
    return render(request, 'dashboard/live_funnel.html', {'funnel': funnel})


@login_required
def funnel_emails_by_tag_view(request):
    funnels = Funnel.objects.filter(user=request.user)
    tag_emails = {}
    predefined_tags = dict(Funnel.TAG_CHOICES).keys()

    for funnel in funnels:
        if funnel.tag == 'custom' and funnel.custom_tag:
            tag = funnel.custom_tag
        elif funnel.tag:
            tag = funnel.tag
        else:
            continue  

        if tag not in tag_emails:
            tag_emails[tag] = set()

        emails = funnel.visitors.values_list('email', flat=True)
        tag_emails[tag].update(emails)

    tag_emails = {tag: sorted(list(emails)) for tag, emails in tag_emails.items()}
    
    tag_display_names = {}
    for tag in tag_emails.keys():
        if tag in predefined_tags:
            tag_display_names[tag] = dict(Funnel.TAG_CHOICES).get(tag, tag)
        else:
            tag_display_names[tag] = tag.replace('_', ' ').title()

    return render(request, 'dashboard/funnel_emails_by_tag.html', {
        'tag_emails': tag_emails,
        'tag_display_names': tag_display_names
    })

@csrf_exempt
@login_required
def send_tag_email_view(request):
    if request.method == 'POST':
        tag = request.POST.get('tag')
        subject = request.POST.get('subject')
        body = request.POST.get('body')
        
        funnels = Funnel.objects.filter(user=request.user, tag=tag)
        emails = set()
        for funnel in funnels:
            emails.update(funnel.visitors.values_list('email', flat=True))

        try:
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[],
                bcc=list(emails)
            )
            email.send(fail_silently=False)
            return JsonResponse({'status': 'success', 'message': f'Email sent to {len(emails)} contacts'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)



@csrf_exempt
@login_required
def publish_funnel_ajax(request, funnel_id):
    funnel = get_object_or_404(Funnel, id=funnel_id, user=request.user)

    if request.method == "POST":
        publish_type = request.POST.get("publish_type")

        if publish_type == "subdomain":
            subdomain = request.POST.get("subdomain", "").strip().lower()
            full_subdomain = f"{subdomain}.fireprenair.com"

            if not subdomain or " " in subdomain:
                return JsonResponse({"success": False, "error": "Invalid subdomain."})

            if Funnel.objects.filter(subdomain=full_subdomain).exclude(id=funnel.id).exists() or  UserWebsite.objects.filter(subdomain=full_subdomain).exists():
                return JsonResponse({"success": False, "error": "Subdomain already taken."})

            funnel.subdomain = full_subdomain
            funnel.custom_domain = None
            funnel.is_published = True
            funnel.save()
            return JsonResponse({"success": True, "url": f"https://{full_subdomain}"})

        elif publish_type == "custom_domain":
            custom_domain = request.POST.get("custom_domain", "").strip().lower()

            if not custom_domain:
                return JsonResponse({"success": False, "error": "Domain is required."})

            if " " in custom_domain or not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", custom_domain):
                return JsonResponse({"success": False, "error": "Invalid domain format."})

            if Funnel.objects.filter(custom_domain=custom_domain).exclude(id=funnel.id).exists() or UserWebsite.objects.filter(custom_domain=custom_domain).exists():
                return JsonResponse({"success": False, "error": "Domain already in use."})

            funnel.custom_domain = custom_domain
            funnel.subdomain = None
            funnel.is_published = True
            funnel.save()
            return JsonResponse({
                "success": True,
                "dns_info": {
                    "record_type": "A",
                    "host": "@",
                    "value": "3.21.28.122"
                }
            })

    return JsonResponse({"success": False, "error": "Invalid request."})

@login_required
def dashboard_notifications(request):
    user = request.user
    notifications = Notification.objects.filter(user=user).order_by("-created_at")
    work_notifications = notifications.filter(app_name="workprenair")
    digi_notifications = notifications.filter(app_name="digiprenair")
    edu_notifications = notifications.filter(app_name="eduprenair")
    commu_notifications = notifications.filter(app_name="commuprenair")
    
    context = {
        "work_notifications": work_notifications,
        "digi_notifications": digi_notifications,
        "edu_notifications": edu_notifications,
        "commu_notifications": commu_notifications,
    }
    return render(request, "dashboard/dashboard_notifications.html", context)

@login_required
def user_profile(request, user_id):
    user = User.objects.get(id=user_id)
    context = {
        "user": user,
    }
    return render(request, "dashboard/profile.html", context)

# Digiprenair
@admin_not_allowed
@login_required
def dashboard_digiprenair(request):
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
    ).order_by("-created_at")[0:5]
    

    context = {
        "user": user,
        "digi_total_items": digi_total_items,
        "digi_total_reviews": digi_total_reviews,
        "total_earnings": total_earnings,
        "total_sales": total_sales,
        "recent_sales": recent_sales,
        "orders": orders,
        "chart_data": chart_data,  # Pass chart data to template
        "notifications": notifications,
    }
    return render(request, "dashboard/dashboard_digiprenair.html", context)

@admin_not_allowed
@login_required
def get_child_categories_digi(request):
    parent_id = request.GET.get("parent_id")
    if parent_id:
        categories = Category.objects.filter(parent_id=parent_id)
    else:
        categories = Category.objects.none()

    category_data = [{"id": cat.id, "name": cat.name} for cat in categories]
    return JsonResponse({"categories": category_data})



# Allowed extensions and max size for direct S3 upload (production only)
DIGIPRENAIR_DOWNLOADABLE_ALLOWED_EXTENSIONS = {
    "zip", "rar", "7zip", "7z", "pdf", "psd", "ai", "eps", "doc", "docx", "png"
}
DIGIPRENAIR_DOWNLOADABLE_MAX_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB
DIGIPRENAIR_PRESIGNED_UPLOAD_EXPIRY = 600  # 10 minutes
DIGIPRENAIR_PRESIGNED_GET_EXPIRY = 3600   # 1 hour for public_url


@login_required
@admin_not_allowed
def generate_digiprenair_upload_url(request):
    if not getattr(settings, 'USE_S3_STORAGE', False):
        return JsonResponse(
            {"error": "S3 storage is not configured."},
            status=503
        )

    user = request.user
    if not user.is_digi_seller:
        return JsonResponse(
            {"error": "You are not a seller. Access denied."},
            status=403
        )

    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed."}, status=405)

    try:
        data = json.loads(request.body) if request.body else {}
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid JSON body. Send filename and file_size."}, status=400)

    filename = (data.get('filename') or '').strip()
    file_size = data.get('file_size')
    if not filename:
        return JsonResponse(
            {"error": "filename is required."},
            status=400
        )
    if file_size is None:
        return JsonResponse(
            {"error": "file_size is required."},
            status=400
        )

    try:
        file_size = int(file_size)
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "file_size must be a number."},
            status=400
        )

    if file_size <= 0 or file_size > DIGIPRENAIR_DOWNLOADABLE_MAX_SIZE_BYTES:
        return JsonResponse(
            {"error": f"File size must be between 1 and {DIGIPRENAIR_DOWNLOADABLE_MAX_SIZE_BYTES // (1024*1024)} MB."},
            status=400
        )

    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in DIGIPRENAIR_DOWNLOADABLE_ALLOWED_EXTENSIONS:
        return JsonResponse(
            {"error": "File type not allowed. Allowed: zip, rar, 7z, pdf, psd, ai, eps, doc, docx, png."},
            status=400
        )

    bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
    if not bucket:
        return JsonResponse(
            {"error": "S3 bucket is not configured."},
            status=503
        )

    import uuid
    safe_name = "".join(c for c in filename if c.isalnum() or c in "._- ").strip() or "file"
    file_key = f"digiprenair_product_files/{user.id}/{uuid.uuid4().hex}/{safe_name}"

    try:
        import boto3
        from botocore.config import Config
        s3_config = Config(signature_version='s3v4', region_name=getattr(settings, 'AWS_S3_REGION_NAME', None))
        s3_client = boto3.client(
            's3',
            aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
            aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
            config=s3_config
        )
        upload_url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': bucket, 'Key': file_key},
            ExpiresIn=DIGIPRENAIR_PRESIGNED_UPLOAD_EXPIRY
        )
        public_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': file_key},
            ExpiresIn=DIGIPRENAIR_PRESIGNED_GET_EXPIRY
        )
    except Exception:
        return JsonResponse(
            {"error": "Failed to generate upload URL."},
            status=500
        )

    return JsonResponse({
        "upload_url": upload_url,
        "file_key": file_key,
        "public_url": public_url
    }, status=200)


@admin_not_allowed
@login_required
def upload_item_digiprenair(request):
    user = request.user

    if not user.is_digi_seller:
        messages.error(request, "You are not a seller. Access denied.")
        return redirect("digi_become_seller")

    plan_name = get_active_plan_name(user)
    product_count = Product.objects.filter(seller=user).count()

    plan_limits = {
        "FreeTier": 3,
        "StartPrenair": 25,
        "BizPrenair": 500,
    }

    if plan_name in plan_limits and product_count >= plan_limits[plan_name]:
        messages.error(request, f"{plan_name} users can upload up to {plan_limits[plan_name]} products. Upgrade to increase your limit.")
        return redirect("dashboard_digiprenair")

    categories = Category.objects.filter(parent=None)

    if request.method == "POST":
        form = ProductUploadForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = user
            if getattr(settings, 'USE_S3_STORAGE', False) and request.POST.get('downloadable_file_key'):
                product.downloadable_file_s3_key = request.POST.get('downloadable_file_key').strip() or None
                if product.downloadable_file:
                    product.downloadable_file = None
            product.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Product uploaded successfully!',
                    'redirect_url': reverse('dashboard_digiprenair')
                })
            
            messages.success(request, "Product uploaded successfully!")
            return redirect("dashboard_digiprenair")
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'error': 'Please correct the errors below.',
                    'form_errors': form.errors
                })
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductUploadForm()

    context = {
        "form": form,
        "categories": categories,
        "product": None,
        "selected_category_l_1": None,
        "selected_category_l_2": None,
        "selected_category_l_3": None,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "dashboard/upload_item_digiprenair.html", context)
    
    return render(request, "dashboard/upload_item_digiprenair.html", context)

@admin_not_allowed
@login_required
def manage_item_digiprenair(request):
    user = request.user

    if not user.is_digi_seller:
        messages.error(request, "You are not a seller. Access denied.")
        return redirect("digi_home")

    products = Product.objects.filter(
        seller=request.user
    )  # Fetch products for the current user
    context = {
        "products": products,
    }
    return render(request, "dashboard/manage_item_digiprenair.html", context)

@admin_not_allowed
@login_required
def edit_item_digiprenair(request, slug):
    user = request.user

    if not user.is_digi_seller:
        messages.error(request, "You are not a seller. Access denied.")
        return redirect("digi_home")

    product = get_object_or_404(Product, slug=slug, seller=request.user)
    categories = Category.objects.filter(parent=None)

    selected_category_l_1 = None
    selected_category_l_2 = None
    selected_category_l_3 = None

    if product.category:
        selected_category_l_1 = product.category.id

    if product.category_l_2:
        selected_category_l_2 = product.category_l_2.id

    if product.category_l_3:
        selected_category_l_3 = product.category_l_3.id

    if request.method == "POST":
        form = ProductUploadForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save(commit=False)
            # S3: store file_key from direct upload when USE_S3_STORAGE is True
            if getattr(settings, 'USE_S3_STORAGE', False) and request.POST.get('downloadable_file_key'):
                product.downloadable_file_s3_key = request.POST.get('downloadable_file_key').strip() or None
                if product.downloadable_file:
                    product.downloadable_file = None
            product.save()
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "status": "success",
                        "message": "Product updated successfully!",
                        "redirect_url": reverse("manage_item_digiprenair"),
                    }
                )

            messages.success(request, "Product updated successfully!")
            return redirect("manage_item_digiprenair")
        else:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "status": "error",
                        "error": "Please correct the errors below.",
                        "form_errors": form.errors,
                    }
                )
    else:
        form = ProductUploadForm(instance=product)

    context = {
        "form": form,
        "product": product,
        "categories": categories,
        "selected_category_l_1": selected_category_l_1,
        "selected_category_l_2": selected_category_l_2,
        "selected_category_l_3": selected_category_l_3,
    }

    return render(request, "dashboard/upload_item_digiprenair.html", context)

@admin_not_allowed
@login_required
def digi_projects(request):
    return render(request, "dashboard/digi_projects.html")


@admin_not_allowed
@login_required
def digi_project_detail(request, id):
    project = get_object_or_404(Project, id=id, user=request.user)
    context = {
        'project': project
    }
    return render(request, "dashboard/digi_project.html", context)


def download_product_file(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Please log in to download files.")
    
    has_purchased = OrderItem.objects.filter(
        order__user=request.user, 
        product=product
    ).exists()
    
    if not has_purchased:
        return HttpResponseForbidden("You don't own this product.")
    
    # S3: redirect to presigned URL when USE_S3_STORAGE is True
    if product.downloadable_file_s3_key and getattr(settings, 'USE_S3_STORAGE', False):
        try:
            import boto3
            from botocore.config import Config
            s3_config = Config(signature_version='s3v4', region_name=getattr(settings, 'AWS_S3_REGION_NAME', None))
            s3_client = boto3.client(
                's3',
                aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
                config=s3_config
            )
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                    'Key': product.downloadable_file_s3_key,
                    'ResponseContentDisposition': f'attachment; filename="{product.downloadable_file_s3_key.split("/")[-1]}"'
                },
                ExpiresIn=3600
            )
            return redirect(presigned_url)
        except Exception:
            return HttpResponse("File not available.", status=404)
    
    if product.downloadable_file:
        file_path = product.downloadable_file.path
        if os.path.exists(file_path):
            with open(file_path, 'rb') as file:
                response = HttpResponse(file.read(), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                return response
        else:
            return HttpResponse("File not found.", status=404)
    
    return HttpResponse("No file available.", status=404)



@admin_not_allowed
@login_required
def delete_notification(request, notification_id):
    # Get the notification or return 404 if not found
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )

    # Delete the notification
    notification.delete()

    # Redirect to the previous page or a fallback URL
    previous_url = request.META.get("HTTP_REFERER", "/")
    return redirect(previous_url)

@login_required
@admin_not_allowed
def logo_gen(request):
    if request.method == 'POST':
        required_fields = ['companyName', 'industry', 'colorScheme', 'style']
        data = request.POST
        missing = [field for field in required_fields if not data.get(field)]
        if missing:
            return JsonResponse({"error": f"Missing required fields: {', '.join(missing)}"}, status=400)

        base_prompt = (
            f"Professional logo design for {data['companyName']} in the {data['industry']} industry. "
            f"Style: {data['style']}, Color scheme: {data['colorScheme']}. "
            f"Modern, minimalist, vector-style design suitable for business use."
        )

        if data.get('tagline'):
            base_prompt += f" Include tagline: '{data['tagline']}'."
        if data.get('additional_notes'):
            base_prompt += f" Additional requirements: {data['additional_notes']}."

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {settings.LEONARDO_API_KEY}"
        }

        payload = {
            "alchemy": True,
            "height": 768,
            "modelId": "6b645e3a-d64f-4341-a6d8-7a3690fbf042",
            "num_images": 1,
            "presetStyle": "DYNAMIC",
            "prompt": base_prompt,
            "width": 1024,
            "negative_prompt": "low quality, amateurish, text, watermark, blurry"
        }

        try:
            post_response = requests.post(
                "https://cloud.leonardo.ai/api/rest/v1/generations",
                json=payload,
                headers=headers,
            )
            post_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": f"API connection failed: {str(e)}"}, status=500)

        try:
            response_data = post_response.json()
            generation_id = response_data["sdGenerationJob"]["generationId"]
        except (KeyError, ValueError):
            return JsonResponse({"error": "Invalid API response format"}, status=500)

        get_url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
        max_retries = 12
        retry_delay = 5
        image_url = None

        for _ in range(max_retries):
            try:
                get_response = requests.get(get_url, headers=headers, timeout=10)
                get_response.raise_for_status()
                generation_data = get_response.json()["generations_by_pk"]

                status = generation_data.get("status", "PENDING")
                if status == "COMPLETE":
                    if generation_data.get("generated_images"):
                        image_url = generation_data["generated_images"][0].get("url")
                        break
                elif status in ["FAILED", "CANCELLED"]:
                    return JsonResponse({"error": f"Generation failed: {status}"}, status=500)

                time.sleep(retry_delay)
            except requests.exceptions.RequestException as e:
                time.sleep(retry_delay)

        if image_url:
            return JsonResponse({
                "image_url": image_url,
                "prompt": base_prompt
            })
        return JsonResponse({"error": "Image generation timed out"}, status=504)
    return render(request, "dashboard/logo_generation.html")



@login_required
@admin_not_allowed
def video_generation(request):
    return render(request, 'dashboard/video_generation.html')

@csrf_exempt
@require_POST
@login_required
def generate_video(request):
    try:
        data = request.POST
        prompt = data.get('prompt')
        duration = int(data.get('duration', 5))
        width = int(data.get('width', 1344))
        height = int(data.get('height', 768))
        style = data.get('style', 'cinematic')
        seed = data.get('seed', 0)
        
        # Construct the prompt with style
        full_prompt = f"{style}, {prompt}"
        
        # Prepare API request
        generate_url = "https://api.aivideoapi.com/runway/generate/text"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": "Bearer daca7ae01c0ea004d6906d5c7e223d1f"
        }
        payload = {
            "text_prompt": full_prompt,
            "model": "gen3",
            "width": width,
            "height": height,
            "seed": seed,
            "time": duration
        }
        
        # Submit generation request
        response = requests.post(generate_url, json=payload, headers=headers)
        print(response)
        print(response.text)
        response.raise_for_status()
        task_data = response.json()
        task_uuid = task_data.get('uuid')
        print(task_uuid)
        
        if not task_uuid:
            return JsonResponse({'error': 'Failed to start generation task'}, status=500)

        # Poll for task completion
        status_url = "https://api.aivideoapi.com/status"
        max_attempts = 60  # 5 minutes with 5s intervals
        attempt = 0
        
        while attempt < max_attempts:
            # Get task status with UUID parameter
            status_response = requests.get(
                status_url,
                params={'uuid': task_uuid},
                headers=headers
            )
            status_response.raise_for_status()
            status_data = status_response.json()
            
            current_status = status_data.get('status')
            print(current_status)
            # Handle terminal states
            if current_status == 'success':
                video_url = status_data.get('url')
                print(video_url)
                if video_url:
                    return JsonResponse({
                        'video_url': video_url,
                        'duration': duration
                    })
                return JsonResponse({'error': 'Video URL missing in response'}, status=500)
            
            elif current_status == 'failed':
                error_info = status_data.get('error', 'Unknown error')
                error_code = status_data.get('error_code', '000')
                return JsonResponse({
                    'error': f'Video generation failed: {error_info}',
                    'error_code': error_code
                }, status=500)
            
            # Continue polling for intermediate states
            elif current_status in ['in queue', 'submitted']:
                # Wait before next poll
                time.sleep(5)
                attempt += 1
                continue
            
            # Handle unknown status
            return JsonResponse({
                'error': f'Unexpected status: {current_status}',
                'response': status_data
            }, status=500)

        return JsonResponse({
            'error': 'Video generation timed out',
            'uuid': task_uuid,
            'last_status': current_status
        }, status=504)

    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'API request failed: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



@login_required
@admin_not_allowed
def image_generation(request):
    user = request.user
    if request.method == "POST":
        prompt = request.POST.get("prompt")
        width = int(request.POST.get("width", 1024))
        height = int(request.POST.get("height", 768))
        mode = request.POST.get("mode", "quality")

        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {settings.LEONARDO_API_KEY}"
        }
        
        payload = {
            "alchemy": mode == "quality", 
            "height": height,
            "modelId": "6b645e3a-d64f-4341-a6d8-7a3690fbf042",
            "num_images": 1, 
            "presetStyle": "DYNAMIC",
            "prompt": prompt,
            "width": width,
        }
        
        post_response = requests.post(
            "https://cloud.leonardo.ai/api/rest/v1/generations",
            json=payload,
            headers=headers
        )
        
        if not post_response.ok:
            return JsonResponse(
                {"error": "Failed to create generation job"},
                status=post_response.status_code
            )
        
        try:
            generation_id = post_response.json()["sdGenerationJob"]["generationId"]
        except KeyError:
            return JsonResponse({"error": "Invalid API response"}, status=500)
        
        get_url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
        image_urls = []
        
        max_retries = 10
        retry_delay = 3  
        
        for _ in range(max_retries):
            get_response = requests.get(get_url, headers=headers)
            
            if get_response.ok:
                try:
                    generation_data = get_response.json()["generations_by_pk"]
                    status = generation_data["status"]
                    
                    if status == "COMPLETE":
                        images = generation_data.get("generated_images", [])
                        image_urls = [img["url"] for img in images if img.get("url")]
                        break
                    elif status in ["PENDING", "PROCESSING"]:
                        time.sleep(retry_delay)
                    else:
                        return JsonResponse({"error": f"Generation failed: {status}"}, status=500)
                except KeyError:
                    return JsonResponse({"error": "Invalid API response format"}, status=500)
            else:
                time.sleep(retry_delay)
        
        if image_urls:
            return JsonResponse({"image_url": image_urls[0]})
        
        return JsonResponse({"error": "Image generation timed out"}, status=504)
    
    context = {"user": user}
    return render(request, "dashboard/image_generation.html", context)

generation_tasks = {}

def generate_image_for_section(prompt, section_name):
    try:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {settings.LEONARDO_API_KEY}"
        }
        enhanced_prompt = (
            f"Professional business illustration for an entrepreneur ebook, {prompt}, "
            "digital art, vibrant colors, detailed, 4k, modern flat design"
        )
        payload = {
            "alchemy": True, 
            "height": 768,
            "modelId": "6b645e3a-d64f-4341-a6d8-7a3690fbf042",
            "num_images": 1, 
            "presetStyle": "DYNAMIC",
            "prompt": enhanced_prompt,
            "width": 1024,
        }

        post_response = requests.post(
            "https://cloud.leonardo.ai/api/rest/v1/generations",
            json=payload,
            headers=headers
        )

        if not post_response.ok:
            print(f"Leonardo API error: {post_response.status_code} - {post_response.text}")
            return None

        generation_id = post_response.json()["sdGenerationJob"]["generationId"]
        get_url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"

        for _ in range(10): 
            get_response = requests.get(get_url, headers=headers)
            if get_response.ok:
                generation_data = get_response.json()["generations_by_pk"]
                if generation_data["status"] == "COMPLETE":
                    return generation_data.get("generated_images", [{}])[0].get("url")
                elif generation_data["status"] in ["FAILED", "CANCELLED"]:
                    print(f"Image generation failed for {section_name}")
                    return None
            time.sleep(3)

        return None

    except Exception as e:
        print(f"Error generating image for {section_name}: {str(e)}")
        return None



def generate_ai_ebook_content(topic, style, additional_comments=""):
    text_prompt = f"""
    You are an expert in creating high-quality entrepreneurial eBook content.
    Generate a comprehensive eBook structure with engaging content based on these parameters:
    
    Topic: {topic}
    Style: {style}
    Additional Comments: {additional_comments if additional_comments else "None"}
    
    Generate content in the following JSON structure:
    {{
        "title": "{topic}",
        "intro": "Engaging introduction (300-400 words) that hooks the reader, sets the context, and outlines the eBook's value",
        "chapters": [
            {{
                "chapter_title": "Chapter 1 title",
                "introduction": "Chapter intro (200-300 words) introducing the chapter's focus",
                "sections": [
                    {{
                        "section_title": "Section 1 title",
                        "content": "Detailed actionable content (300-450 words)",
                        "key_takeaways": ["Takeaway 1", "Takeaway 2"]
                    }},
                    {{
                        "section_title": "Section 2 title",
                        "content": "Detailed actionable content (300-450 words)",
                        "key_takeaways": ["Takeaway 1", "Takeaway 2"]
                    }}
                ]
            }},
            {{
                "chapter_title": "Chapter 2 title",
                "introduction": "Chapter intro (200-300 words)",
                "sections": [
                    {{
                        "section_title": "Section 1 title",
                        "content": "Detailed actionable content (300-450 words)",
                        "key_takeaways": ["Takeaway 1", "Takeaway 2"]
                    }},
                    {{
                        "section_title": "Section 2 title",
                        "content": "Detailed actionable content (300-450 words)",
                        "key_takeaways": ["Takeaway 1", "Takeaway 2"]
                    }}
                ]
            }},
            {{
                "chapter_title": "Chapter 3 title",
                "introduction": "Chapter intro (200-300 words)",
                "sections": [
                    {{
                        "section_title": "Section 1 title",
                        "content": "Detailed actionable content (300-450 words)",
                        "key_takeaways": ["Takeaway 1", "Takeaway 2"]
                    }},
                    {{
                        "section_title": "Section 2 title",
                        "content": "Detailed actionable content (300-450 words)",
                        "key_takeaways": ["Takeaway 1", "Takeaway 2"]
                    }}
                ]
            }},
        ],
        "case_studies": [
            {{
                "title": "Case Study 1 title",
                "content": "Detailed case study (400-500 words) showing real-world application",
                "key_lessons": ["Lesson 1", "Lesson 2"]
            }},
            {{
                "title": "Case Study 2 title",
                "content": "Detailed case study (400-500 words) showing real-world application",
                "key_lessons": ["Lesson 1", "Lesson 2"]
            }}
        ],
        "conclusion": "Motivating conclusion (400-500 words) summarizing key points and providing a call to action",
        "resources": [
            {{
                "title": "Resource 1 title",
                "description": "Resource description (150-200 words)",
                "link": "Optional URL or reference"
            }},
            {{
                "title": "Resource 2 title",
                "description": "Resource description (150-200 words)",
                "link": "Optional URL or reference"
            }}
        ]
    }}
    
    Requirements:
    - Maintain a {style.lower()} tone throughout
    - Include practical, actionable advice in each section
    - Use real-world examples where possible
    - Make content engaging, motivational, and professional for publication
    - Address any specific requests in the additional comments
    - Ensure content is unique and tailored to the topic
    - Total word count should aim for 12,000-20,000 words to achieve 20 - 30 pages
    - Include at least 8 chapters if additional_comments specify more content
    
    Important: Return ONLY valid JSON, no additional text or explanations.
    """
    
    try:
        text_response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": text_prompt}],
            response_format={"type": "json_object"}
        )
        
        content = json.loads(text_response.choices[0].message.content)
        
        # Adjust chapters if additional_comments request more content
        if "more content" in additional_comments.lower() or "longer" in additional_comments.lower():
            content['chapters'].extend([
                {
                    "chapter_title": f"Chapter {i} title",
                    "introduction": f"Chapter {i} intro (200-300 words)",
                    "sections": [
                        {
                            "section_title": f"Section 1 title",
                            "content": f"Detailed actionable content for Chapter {i} Section 1 (400-600 words)",
                            "key_takeaways": ["Takeaway 1", "Takeaway 2", "Takeaway 3"]
                        },
                        {
                            "section_title": f"Section 2 title",
                            "content": f"Detailed actionable content for Chapter {i} Section 2 (400-600 words)",
                            "key_takeaways": ["Takeaway 1", "Takeaway 2", "Takeaway 3"]
                        }
                    ]
                } for i in range(5, 9)
            ])
        
        # # Generate images for each section
        # images = {
        #     "cover": generate_image_for_section(f"Cover image for {topic} eBook, {style} style", "Cover"),
        #     "intro": generate_image_for_section(f"Introduction image for {topic} eBook, {style} style", "Introduction"),
        #     "chapters": [
        #         generate_image_for_section(f"Chapter {i+1} image for {topic} eBook, {style} style", f"Chapter {i+1}")
        #         for i in range(len(content['chapters']))
        #     ],
        #     "case_studies": [
        #         generate_image_for_section(f"Case Study {i+1} image for {topic} eBook, {style} style", f"Case Study {i+1}")
        #         for i in range(len(content['case_studies']))
        #     ],
        #     "conclusion": generate_image_for_section(f"Conclusion image for {topic} eBook, {style} style", "Conclusion"),
        #     "resources": generate_image_for_section(f"Resources image for {topic} eBook, {style} style", "Resources")
        # }
        
        return  content
        
    except Exception as e:
        print(f"Error generating AI content: {str(e)}")
        return {
            "text_content": {
                "title": topic,
                "intro": "Introduction content...",
                "chapters": [
                    {
                        "chapter_title": f"Chapter {i}",
                        "introduction": "Chapter intro...",
                        "sections": [
                            {
                                "section_title": "Section 1",
                                "content": "Section content...",
                                "key_takeaways": ["Takeaway 1", "Takeaway 2"]
                            }
                        ]
                    } for i in range(1, 5)
                ],
                "case_studies": [
                    {
                        "title": "Case Study 1",
                        "content": "Case study content...",
                        "key_lessons": ["Lesson 1", "Lesson 2"]
                    }
                ],
                "conclusion": "Conclusion content...",
                "resources": [
                    {
                        "title": "Resource 1",
                        "description": "Resource description...",
                        "link": ""
                    }
                ]
            },
            "images": {}
        }


@login_required
def generate_ebook_images(request):
    ebook_data = request.session.get('ebook_data', {})
    if not ebook_data:
        return JsonResponse({'error': 'Session expired. Please start over.'}, status=400)
    
    # Check if images already exist in session
    if ebook_data.get('images'):
        return JsonResponse({'images': ebook_data['images']})
    
    try:
        topic = ebook_data['title']
        style = ebook_data['style']
        
        cover_img = generate_image_for_section(f"Cover image for {topic} eBook, {style} style", "Cover")
        intro_img = generate_image_for_section(f"Introduction image for {topic} eBook, {style} style", "Introduction")
        
        chapter_img1 = generate_image_for_section(f"Chapter 1 image for {topic} eBook, {style} style", "Chapter 1")
        chapter_img2 = generate_image_for_section(f"Chapter 2 image for {topic} eBook, {style} style", "Chapter 2")
        
        casestudy_img1 = generate_image_for_section(f"Case Study 1 image for {topic} eBook, {style} style", "Case Study 1")
        casestudy_img2 = generate_image_for_section(f"Case Study 2 image for {topic} eBook, {style} style", "Case Study 2")
        
        num_chapters = len(ebook_data['content']['chapters'])
        num_case_studies = len(ebook_data['content']['case_studies'])
        
        images = {
            "cover": cover_img,
            "intro": intro_img,
            "chapters": [
                chapter_img1 if i % 2 == 0 else chapter_img2 
                for i in range(num_chapters)
            ],
            "case_studies": [
                casestudy_img1 if i % 2 == 0 else casestudy_img2 
                for i in range(num_case_studies)
            ],
            "conclusion": cover_img,  
            "resources": intro_img
        }
        
        ebook_data['images'] = images
        request.session['ebook_data'] = ebook_data
        request.session.modified = True
        
        return JsonResponse({'images': images})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def generate_ebook(request):
    if request.method == "POST":
        title = request.POST.get('title', '')
        ebook_type = request.POST.get('ebook_type', 'ebook')
        style = request.POST.get('style', 'Motivational')
        additional_comments = request.POST.get('additional_comments', '')

        if not title:
            return JsonResponse({"error": "Please provide a title for the eBook."}, status=400)

        try:
            text_content = generate_ai_ebook_content(title, style, additional_comments)
            request.session['ebook_data'] = {
                'title': title,
                'type': ebook_type,
                'style': style,
                'additional_comments': additional_comments,
                'content': text_content,
                'images': {} 
            }
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                return JsonResponse({"status": "success", "redirect_url": "/dashboard/preview-ebook/"}, status=200)
            else:
                return redirect('preview_ebook')
        except Exception as e:
            if request.is_ajax():
                return JsonResponse({"error": str(e)}, status=500)
            else:
                return JsonResponse({"error": str(e)}, status=500)

    return render(request, "dashboard/generate_ebook.html")


@login_required
def ebook_preview(request):
    ebook_data = request.session.get('ebook_data', {})
    if not ebook_data:
        return HttpResponse("Session expired. Please start over.")
    
    return render(request, 'dashboard/preview_ebook.html', {'ebook': ebook_data})


def generate_pdf(request):
    ebook_data = request.session.get('ebook_data', {})
    if not ebook_data:
        return HttpResponse("Session expired. Please start over.")

    html_string = render_to_string('dashboard/ebook_template.html', {'ebook': ebook_data})

    doc_api = docraptor.DocApi()
    doc_api.api_client.configuration.username = 'DapRe7ClVi6odJBoDDrR'  

    try:
        response = doc_api.create_doc({
            'test': False, 
            'document_type': 'pdf',
            'document_content': html_string,
            'javascript': True,
            'prince_options': {
                'media': 'print',
                'baseurl': 'http://localhost:8000', 
            },
        })

        filename = f'{ebook_data["title"].replace(" ", "_")}.pdf'
        return HttpResponse(response, content_type='application/pdf', headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        })

    except docraptor.rest.ApiException as error:
        print(f"Status: {error.status}")
        print(f"Reason: {error.reason}")
        print(f"Body: {error.body}")
        return HttpResponse("Error generating PDF using DocRaptor.")

# EduPrenair
@admin_not_allowed
@login_required
def dashboard_eduprenair(request):
    user = request.user

    listed_courses = (
        user.course_set.filter(is_published=True)
        .annotate(enrollment_count=Count("enrolled_students") - 1)
        .order_by("-created_at")[:5]
    )
    
    enrolled_courses = StudentEnrollment.objects.filter(user=user).exclude(course__instructor=user)
    # recent_reviews = CourseRating.objects.filter(course__instructor=user).order_by(
    #     "-created_at"
    # )[:5]

    edu_total_earnings = user.edu_total_earnings
    edu_total_reviews = CourseRating.objects.filter(course__instructor=user).count()
    edu_instrcutor_courses = user.edu_instrcutor_courses
    edu_instructor_total_students = user.edu_instructor_total_students

    course_titles = [course.title for course in listed_courses]
    enrollment_counts = [course.enrollment_count for course in listed_courses]
    
    unread_notifications = Notification.objects.filter(
        user=user, is_read=False, app_name="eduprenair"
    )

    unread_notifications.update(is_read=True)
    notifications = Notification.objects.filter(
        user=user, app_name="eduprenair"
    ).order_by("-created_at")[0:5]
    
    

    context = {
        "user": user,
        "listed_courses": listed_courses,
        "enrolled_courses": enrolled_courses,
        "edu_total_earnings": edu_total_earnings,
        "edu_total_reviews": edu_total_reviews,
        "edu_instrcutor_courses": edu_instrcutor_courses,
        "edu_instructor_total_students": edu_instructor_total_students,
        "course_titles": course_titles, 
        "enrollment_counts": enrollment_counts, 
        "notifications": notifications,
        
    }
    return render(request, "dashboard/dashboard_eduprenair.html", context)

@admin_not_allowed
@login_required
def manage_courses_eduprenair(request):
    user = request.user

    # Fetch courses categorized by their state
    published_courses = user.course_set.filter(is_published=True).order_by(
        "-created_at"
    )
    not_published_courses = user.course_set.filter(
        is_published=False, submit_for_approval=False
    ).order_by("-created_at")
    pending_courses = user.course_set.filter(
        submit_for_approval=True, is_published=False
    ).order_by("-created_at")

    context = {
        "user": user,
        "published_courses": published_courses,
        "not_published_courses": not_published_courses,
        "pending_courses": pending_courses,
    }
    return render(request, "dashboard/manage_courses_eduprenair.html", context)

@require_POST
@login_required
def analyze_student_progress(request):
    try:
        data = json.loads(request.body)
        course_slug = data.get('course_slug')
        user_id = data.get('user_id')
        
        if request.user.id != int(user_id):
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        enrollment = StudentEnrollment.objects.get(
            user=request.user,
            course__slug=course_slug
        )
        course = enrollment.course
        prompt = f"""
        Analyze student progress for course: {course.title}
        Current Progress: {enrollment.progress}%
        Completion Status: {'Completed' if enrollment.is_completed else 'In Progress'}
        Enrollment Date: {enrollment.enrolled_date.strftime('%Y-%m-%d')}
        
        Provide:
        1. Dropout risk prediction (low/medium/high) and percentage
        2. 3 key learning strengths
        3. 3 actionable improvement suggestions
        
        Format response as JSON with keys: risk_prediction, risk_percentage, strengths, improvements

        Note: Do not format the response in any other way. Just return the JSON object. I dont need any other text. out my json key values.
        """
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "system",
                "content": "You are an AI learning analytics assistant. Provide clear, educational insights."
            }, {
                "role": "user", 
                "content": prompt
            }]
        )
        analysis = response.choices[0].message.content
        analysis = json.loads(analysis)
        return JsonResponse({'analysis': analysis})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@admin_not_allowed
@login_required
def get_child_categories(request):
    parent_id = request.GET.get("parent_id")
    if parent_id:
        categories = CourseCategory.objects.filter(parent_id=parent_id)
    else:
        categories = CourseCategory.objects.none()

    category_data = [{"id": cat.id, "name": cat.name} for cat in categories]
    return JsonResponse({"categories": category_data})

@admin_not_allowed
@login_required
def course_create_eduprenair(request):
    user = request.user
    level_1_categories = CourseCategory.objects.filter(parent=None)

    if not user.is_edu_instructor:
        messages.error(request, "You are not a Instructor. Access denied.")
        return redirect("become_instructor")

    # Handle the form submission
    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.instructor = user
            course.save()
            course.enrolled_students.add(user)
            course.save()
            StudentEnrollment.objects.create(user=user, course=course)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Course Added to Draft. Modify there further for Submission!',
                    'redirect_url': reverse('dashboard_eduprenair')
                })
            
            messages.success(
                request, "Course Added to Draft. Modify there further for Submission!"
            )
            return redirect("dashboard_eduprenair")
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'error': 'Please correct the errors below.',
                    'form_errors': form.errors
                })
            messages.error(request, "Please correct the errors below.")
    else:
        form = CourseForm()

    # Render the form in the custom template
    context = {
        "form": form,
        "level_1_categories": level_1_categories,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "dashboard/course_create_eduprenair.html", context)
    
    return render(request, "dashboard/course_create_eduprenair.html", context)

@admin_not_allowed
@login_required
def submit_for_approval(request, course_slug):
    if request.method == "POST":
        course = get_object_or_404(Course, slug=course_slug, instructor=request.user)
        if course.submit_for_approval:
            messages.info(
                request, "This course has already been submitted for approval."
            )
        else:
            course.submit_for_approval = True
            course.save()
            messages.success(request, "Your course has been submitted for approval.")
    else:
        messages.error(request, "Invalid request method.")
    return redirect("manage_courses_eduprenair")

@admin_not_allowed
@login_required
def course_edit_eduprenair(request, course_slug):
    user = request.user
    level_1_categories = CourseCategory.objects.filter(parent=None)
    selected_category_l_1 = None
    selected_category_l_2 = None
    selected_category_l_3 = None

    # Check if the user is an instructor
    if not user.is_edu_instructor:
        messages.error(request, "You are not an Instructor. Access denied.")
        return redirect("edu_home")

    # Fetch the course to be edited, ensuring it belongs to the logged-in instructor
    course = get_object_or_404(Course, slug=course_slug, instructor=user)

    if course.category_l_1:
        selected_category_l_1 = course.category_l_1.id

    if course.category_l_2:
        selected_category_l_2 = course.category_l_2.id

    if course.category_l_3:
        selected_category_l_3 = course.category_l_3.id

    if request.method == "POST":
        # Handle form submission
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Course updated successfully!',
                    'redirect_url': reverse('manage_courses_eduprenair')
                })
            
            messages.success(request, "Course updated successfully!")
            return redirect("dashboard_eduprenair")
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'error': 'Please correct the errors below.',
                    'form_errors': form.errors
                })
            print(form.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        # Pre-fill the form with course details
        form = CourseForm(instance=course)

    # Render the form in the custom template
    context = {
        "form": form,
        "level_1_categories": level_1_categories,
        "course": course,
        "selected_category_l_1": selected_category_l_1,
        "selected_category_l_2": selected_category_l_2,
        "selected_category_l_3": selected_category_l_3,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, "dashboard/course_create_eduprenair.html", context)
    
    return render(request, "dashboard/course_create_eduprenair.html", context)

@admin_not_allowed
@login_required
def delete_course(request, slug):
    user = request.user

    # Check if the user is an instructor
    if not user.is_edu_instructor:
        messages.error(request, "You are not an Instructor. Access denied.")
        return redirect("edu_home")

    # Fetch the course to be deleted, ensuring it belongs to the logged-in instructor
    course = get_object_or_404(Course, slug=slug, instructor=user)

    # Delete the course
    course.delete()
    messages.success(request, "Course deleted successfully!")
    return redirect("dashboard_eduprenair")

@admin_not_allowed
@login_required
def add_module_course_eduprenair(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug, instructor=request.user)
    modules = Module.objects.filter(course=course)

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        order = request.POST.get("order")

        if Module.objects.filter(course=course, order=order).exists():
            messages.error(
                request, "A module with this order already exists in the course."
            )
            return redirect("add_module_course_eduprenair", course_slug=course.slug)

        if title and description and order:
            module = Module.objects.create(
                course=course, title=title, description=description, order=order
            )
            messages.success(
                request, f'Module "{module.title}" has been added successfully!'
            )
            return redirect("add_module_course_eduprenair", course_slug=course.slug)
        else:
            messages.error(request, "All fields are required to add a module.")

    return render(
        request,
        "dashboard/module_lessons_eduprenair.html",
        {
            "course": course,
            "modules": modules,
        },
    )

@admin_not_allowed
@login_required
def add_lesson_course_eduprenair(request, module_id):
    # Fetch the module and ensure it's related to the logged-in instructor's course
    module = get_object_or_404(Module, id=module_id, course__instructor=request.user)

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        video = request.FILES.get("video")
        order = request.POST.get("order")

        # Ensure that user only uploads video or PDF
        if video and not video.name.endswith((".mp4", ".avi", ".mov", ".pdf")):
            messages.error(
                request, "Only video files (mp4, avi, mov) or PDF files are allowed."
            )
            return redirect(
                "add_module_course_eduprenair", course_slug=module.course.slug
            )

        if Lesson.objects.filter(module=module, order=order).exists():
            messages.error(
                request, "A lesson with this order already exists in the module."
            )
            return redirect(
                "add_module_course_eduprenair", course_slug=module.course.slug
            )

        if video and video.size > 100 * 1024 * 1024:
            messages.error(request, "The file size should not be greater than 100MB.")
            return redirect(
                "add_module_course_eduprenair", course_slug=module.course.slug
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
            messages.success(
                request, f'Lesson "{lesson.title}" has been added successfully!'
            )
            return redirect(
                "add_module_course_eduprenair", course_slug=module.course.slug
            )
        else:
            messages.error(request, "All fields are required to add a lesson.")

    return render(request, "dashboard/module_lessons_eduprenair.html", {"module": module})


@admin_not_allowed
@login_required
def edit_lesson_course_eduprenair(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course__instructor=request.user)
    module = lesson.module

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        video = request.FILES.get("video")
        order = request.POST.get("order")
        remove_video = request.POST.get("remove_video")

        if not title or not order:
            messages.error(request, "Title and Order are required fields.")
            return redirect("edit_lesson_course_eduprenair", lesson_id=lesson.id)

        try:
            order = int(order)
            if order < 1:
                raise ValueError
        except ValueError:
            messages.error(request, "Invalid order value. Must be a positive integer.")
            return redirect("edit_lesson_course_eduprenair", lesson_id=lesson.id)

        if Lesson.objects.filter(module=module, order=order).exclude(id=lesson.id).exists():
            messages.error(request, "Another lesson already uses this order number.")
            return redirect("edit_lesson_course_eduprenair", lesson_id=lesson.id)

        if remove_video and lesson.video:
            lesson.video.delete()
            lesson.video = None

        if video:
            if not video.name.endswith((".mp4", ".avi", ".mov", ".pdf")):
                messages.error(request, "Invalid file type. Allowed formats: mp4, avi, mov, pdf.")
                return redirect("edit_lesson_course_eduprenair", lesson_id=lesson.id)
            
            if video.size > 100 * 1024 * 1024:
                messages.error(request, "File size exceeds 100MB limit.")
                return redirect("edit_lesson_course_eduprenair", lesson_id=lesson.id)
            
            if lesson.video:
                lesson.video.delete()
            lesson.video = video

        # Update lesson fields
        lesson.title = title
        lesson.description = description
        lesson.order = order
        lesson.save()

        messages.success(request, "Lesson updated successfully!")
        return redirect("add_module_course_eduprenair", course_slug=module.course.slug)

    return render(request, "dashboard/edit_lesson.html", {"lesson": lesson})

@login_required
@require_POST
def generate_module_lessons_eduprenair(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug, instructor=request.user)
    
    try:
        data = json.loads(request.body)
        description = data.get('description')
        lesson_count = min(int(data.get('lesson_count', 1)), 4)
        
        last_module = Module.objects.filter(course=course).order_by('-order').first()
        next_order = last_module.order + 1 if last_module else 1

        prompt = f"""
        You are helping to create an educational course module based on this course description:
        \"\"\"
        {description}
        \"\"\"

        Generate **one module** with **{lesson_count} lessons**.  
        Return the result strictly in the following JSON format:
        {{
            "module_title": "string",
            "module_description": "string",
            "module_order": {next_order},
            "lessons": [
                {{
                    "title": "string",
                    "description": "string",
                    "order": integer
                }}
            ]
        }}

        **Important Requirements:**

        - Create a **detailed and engaging module title** and a **comprehensive, informative module description** (around 150-200 words).
        - For each lesson:
          - Write an **engaging, clear, and specific lesson title**.
          - Each lesson must be a full, detailed teaching article (~500-700 words).
            - NOT a preview, NOT a summary, but an actual tutorial that fully teaches the lesson topic.
            - Imagine you are writing a full university-level chapter for each lesson.
        - Each lesson must include:
              - An engaging introduction to the topic.
              - A detailed, step-by-step explanation of the core concepts.
              - Real-world examples and simple analogies** to make complex ideas easy.
              - Mini-activities or exercises learners can do immediately.
              - Explain why the topic matters, how it is used in practice, and common mistakes to avoid.
              - End each lesson with a short summary of key takeaways.

        - Ensure lessons are **logically ordered from 1 to {lesson_count}**.
        - The tone must be **educational, motivating, and beginner-friendly**, but detailed enough for mastery.
        - Focus on **clarity, structure, depth, and progression**.
        - Avoid unnecessary technical jargon unless clearly explained.
        - **Strictly output valid JSON format** without any extra text outside the JSON. Do not include any explanations or additional information outside the JSON structure, like: ```json or anything else.

        Write as if you are creating content for a high-quality online course or university-level material designed for self-paced learning.
        """

        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
        )
        
        content = response.choices[0].message.content
        try:
            ai_data = json.loads(content)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid AI response format'}, status=500)

        with transaction.atomic():
            module = Module.objects.create(
                course=course,
                title=ai_data['module_title'],
                description=ai_data['module_description'],
                order=ai_data['module_order']
            )
            
            for lesson_data in ai_data['lessons']:
                Lesson.objects.create(
                    module=module,
                    title=lesson_data['title'],
                    description=lesson_data.get('description', ''),
                    order=lesson_data['order'],
                    slug=f"{slugify(lesson_data['title'])}-{module.id}-{lesson_data['order']}_{str(uuid.uuid4().int)[:6]}",
                    video=None 
                )
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@admin_not_allowed
@login_required
def delete_lesson(request, lesson_id):
    lesson = get_object_or_404(
        Lesson, id=lesson_id, module__course__instructor=request.user
    )

    if request.method == "POST":
        lesson_title = lesson.title

        # if lesson.video:
        #     file_path = lesson.video.path
        #     if settings.USE_S3_STORAGE:
        #         lesson.video.delete(save=False)
        #     elif os.path.exists(file_path):
        #         os.remove(file_path)
        lesson.delete() 
        messages.success(request, f'Lesson "{lesson_title}" has been deleted successfully!')
        return redirect('add_module_course_eduprenair', course_slug=lesson.module.course.slug)
    messages.error(request, 'Invalid request. Lesson could not be deleted.')
    return redirect('add_module_course_eduprenair', course_slug=lesson.module.course.slug)  

@admin_not_allowed
@login_required
def course_stats(request, course_slug):
    user = request.user
    course = get_object_or_404(Course, slug=course_slug, instructor=user)
    if not course.is_published:
        messages.error(request, 'This course is not published yet.')
        return redirect('manage_courses_eduprenair')

    if course.instructor != user:
        messages.error(request, 'You are not authorized to view this page.')
        return redirect('manage_courses_eduprenair')
    
    students = StudentEnrollment.objects.filter(course=course).exclude(user=user)
    context = {
        'course': course,
        'students': students,
    }
    return render(request, 'dashboard/course_stats.html', context)

@login_required
@admin_not_allowed
def digi_reviews(request):
    user = request.user
    if not user.is_digi_seller:
        messages.error(request, 'You are not a seller. Access denied.')
        return redirect('digi_become_seller')

    product_id = request.GET.get('product')
    rating = request.GET.get('rating')
    sort = request.GET.get('sort', 'newest')

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

    context = {
        'reviews': reviews,
        'products': products,
        'avg_rating': avg_rating,
        'five_star_count': five_star_count,
        'reviewed_products_count': reviewed_products_count,
        'selected_product': product_id,
        'selected_rating': rating,
        'selected_sort': sort,
    }
    return render(request, 'dashboard/digi_reviews.html', context)


# CommuPrenair
@admin_not_allowed
@login_required
def dashboard_commuprenair(request):
    user = request.user

    # CommuPrenair
    recent_posts = Post.objects.filter(author=user).order_by("-created_at")[:3]

    # Retrieve both sent and received connections for the user
    connections_sent = Connection.objects.filter(from_user=user).select_related(
        "to_user"
    )
    connections_received = Connection.objects.filter(to_user=user).select_related(
        "from_user"
    )

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
    
    
        # notifications
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
    
    

    context = {
        "recent_posts": recent_posts,
        "connections": connections,
        "user_messages": user_messages,
        "notifications": notifications,
    }
    return render(request, "dashboard/dashboard_commuprenair.html", context)



# Common
@login_required
def dashboard_edit_profile(request):
    user = request.user  # Get the logged-in user
    is_username_changed = user.is_username_changed  # Check if the user has already changed their username

    if request.method == "POST":
        # Pass `is_username_changed` to the form
        form = ProfileUpdateForm(
            request.POST, request.FILES, instance=user, is_username_changed=is_username_changed
        )
        if form.is_valid():
            if 'username' in form.changed_data:
                user.is_username_changed = True
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("dashboard_home") 
    else:
        form = ProfileUpdateForm(instance=user, is_username_changed=is_username_changed)

    context = {"form": form}
    return render(request, "dashboard/dashboard_edit_profile.html", context)


@login_required
def dashboard_change_password(request):
    if request.method == "POST":
        password_form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(
                request, password_form.user
            )  # Prevents logout after password change
            messages.success(request, "Your password has been updated successfully!")
            return redirect(
                "dashboard_change_password"
            )  # Redirect back to the same page or elsewhere
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        password_form = CustomPasswordChangeForm(user=request.user)

    context = {
        "password_form": password_form,
    }
    return render(request, "dashboard/dashboard_change_password.html", context)


# ai


@csrf_exempt
def generate_description_eduprenair(request):
    if request.method == "POST":
        try:
            # Parse the JSON data
            data = json.loads(request.body)
            title = data.get("title", "")

            if not title.strip():
                return JsonResponse(
                    {"error": "Title is required for description generation."},
                    status=400,
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
                model="llama-3.3-70b-versatile",
            )

            # Extract the generated description
            description_raw = groq_response.choices[0].message.content

            # Convert Markdown to HTML
            description_html = markdown.markdown(description_raw)
            description_html_safe = mark_safe(
                description_html
            )  # Mark as safe for HTML rendering

            return JsonResponse(
                {
                    "description": description_raw,  # Plain text for the textarea
                    "description_html": description_html_safe,  # Rendered HTML for preview
                }
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method."}, status=405)


@csrf_exempt
def generate_description_digiprenair(request):
    if request.method == "POST":
        try:
            # Parse the JSON data
            data = json.loads(request.body)
            title = data.get("title", "")

            if not title.strip():
                return JsonResponse(
                    {"error": "Title is required for description generation."},
                    status=400,
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
                model="llama-3.3-70b-versatile",
            )

            # Extract the generated description
            description_d = groq_response.choices[0].message.content
            bot_reply_html = markdown.markdown(
                description_d
            )  # Convert to HTML with Markdown
            description = mark_safe(bot_reply_html)  # Mark as safe HTML
            return JsonResponse({"description": description})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method."}, status=405)


@csrf_exempt
def generate_description_workprenair(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            title = data.get("title", "")

            if not title.strip():
                return JsonResponse(
                    {"error": "Title is required for description generation."},
                    status=400,
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
                model="llama-3.3-70b-versatile",
            )

            description_md = groq_response.choices[0].message.content
            description_html = markdown.markdown(description_md)
            return JsonResponse({"description": description_html}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=405)


# ----------------------------------- Admin -----------------------------------------------------------------
@login_required
def admin_dash(request):
    if request.user.role != "admin":
        messages.error(request, "Access Denied!")
        return redirect("home")

    search_query = request.GET.get("search", "")
    
    if search_query:
        users = CustomUser.objects.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone_no__icontains=search_query)
        )
    else:
        users = CustomUser.objects.all()

    paginator = Paginator(users, 100)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_query": search_query,  
    }

    return render(request, "dashboard/admin_dash.html", context)


@login_required
def admin_online_users(request):
    if request.user.role != "admin":
        messages.error(request, "Access Denied!")
        return redirect("home")
    
    search_query = request.GET.get("search", "")

    if search_query:
        users = CustomUser.objects.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone_no__icontains=search_query),
            is_online=True
        )
    else:
        users = CustomUser.objects.filter(is_online=True)

    paginator = Paginator(users, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_query": search_query, 
    }


    return render(request, "dashboard/admin_online_users.html", context)

@login_required
def admin_stats(request):
    if request.user.role != "admin":
        messages.error(request, "Access Denied!")
        return redirect("home")

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
    
    context = {
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
    }

    return render(request, "dashboard/admin_stats.html", context)

from django.core.serializers import serialize

# Deparmental sales views
def digi_sales(request):
    if request.user.role != "admin":
        messages.error(request, "Access Denied!")
        return redirect("home")

    # Get orders and serialize them properly
    orders = Order.objects.all().order_by("-created_at")[:50]  # Limit for performance
    
    # Calculate analytics data
    total_sales = Order.objects.filter(is_paid=True).aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    total_orders = orders.count()
    
    # Last 30 days sales
    thirty_days_ago = timezone.now() - timedelta(days=30)
    monthly_sales = Order.objects.filter(
        is_paid=True, 
        created_at__gte=thirty_days_ago
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Last 7 days sales
    seven_days_ago = timezone.now() - timedelta(days=7)
    weekly_sales = Order.objects.filter(
        is_paid=True, 
        created_at__gte=seven_days_ago
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Today's sales
    today = timezone.now().date()
    daily_sales = Order.objects.filter(
        is_paid=True, 
        created_at__date=today
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Last sale
    last_sale = Order.objects.filter(is_paid=True).order_by('-created_at').first()
    
    # Sales data for charts (last 30 days)
    sales_data = []
    dates = []
    for i in range(30):
        date = timezone.now().date() - timedelta(days=29-i)
        daily_total = Order.objects.filter(
            is_paid=True, 
            created_at__date=date
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        sales_data.append(float(daily_total))
        dates.append(date.strftime('%Y-%m-%d'))
    
    # Top selling products
    top_products = Product.objects.annotate(
        total_sold=Sum('orderitem__quantity'),
        total_revenue=Sum('orderitem__price')
    ).filter(total_sold__gt=0).order_by('-total_sold')[:10]
    
    top_products_data = []
    for product in top_products:
        top_products_data.append({
            'title': product.title,
            'sales': product.total_sold or 0,
            'revenue': float(product.total_revenue or 0)
        })
    
    # Prepare orders data for JSON serialization
    orders_data = []
    for order in orders:
        orders_data.append({
            'id': order.id,
            'user': {'username': order.user.username},
            'created_at': order.created_at.isoformat(),
            'total_amount': float(order.total_amount),
            'is_paid': order.is_paid
        })
    
    analytics_data = {
        "total_sales": float(total_sales),
        "total_orders": total_orders,
        "monthly_sales": float(monthly_sales),
        "weekly_sales": float(weekly_sales),
        "daily_sales": float(daily_sales),
        "last_sale": {
            "amount": float(last_sale.total_amount) if last_sale else 0,
            "date": last_sale.created_at.isoformat() if last_sale else None,
            "user": last_sale.user.username if last_sale else None
        } if last_sale else None,
        "sales_chart": {
            "dates": dates,
            "amounts": sales_data
        },
        "top_products": top_products_data
    }
    
    context = {
        "orders": orders,  # Keep for template if needed
        "orders_json": json.dumps(orders_data),
        "analytics_json": json.dumps(analytics_data),
        "analytics": analytics_data  # Keep for debugging
    }
    return render(request, "dashboard/admin_digi_sales.html", context)


def work_sales(request):
    if request.user.role != "admin":
        messages.error(request, "Access Denied!")
        return redirect("home")

    orders = WorkOrder.objects.all().order_by("-created_at")[:50]  # Limit for performance
    
    # Calculate analytics data
    total_sales = WorkOrder.objects.filter(is_paid=True).aggregate(
        total=Sum('price')
    )['total'] or 0
    
    total_orders = WorkOrder.objects.filter(is_paid=True).count()
    
    # Completed orders count
    completed_orders = WorkOrder.objects.filter(is_paid=True, status="completed").count()
    
    # Active orders count
    active_orders = WorkOrder.objects.filter(is_paid=True, status="active").count()
    
    # Last 30 days sales
    thirty_days_ago = timezone.now() - timedelta(days=30)
    monthly_sales = WorkOrder.objects.filter(
        is_paid=True, 
        created_at__gte=thirty_days_ago
    ).aggregate(total=Sum('price'))['total'] or 0
    
    # Last 7 days sales
    seven_days_ago = timezone.now() - timedelta(days=7)
    weekly_sales = WorkOrder.objects.filter(
        is_paid=True, 
        created_at__gte=seven_days_ago
    ).aggregate(total=Sum('price'))['total'] or 0
    
    # Today's sales
    today = timezone.now().date()
    daily_sales = WorkOrder.objects.filter(
        is_paid=True, 
        created_at__date=today
    ).aggregate(total=Sum('price'))['total'] or 0
    
    # Last sale
    last_sale = WorkOrder.objects.filter(is_paid=True).order_by('-created_at').first()
    
    # Sales data for charts (last 30 days)
    sales_data = []
    dates = []
    for i in range(30):
        date = timezone.now().date() - timedelta(days=29-i)
        daily_total = WorkOrder.objects.filter(
            is_paid=True, 
            created_at__date=date
        ).aggregate(total=Sum('price'))['total'] or 0
        
        sales_data.append(float(daily_total))
        dates.append(date.strftime('%Y-%m-%d'))
    
    # Package type distribution
    package_stats = WorkOrder.objects.filter(is_paid=True).values('package_type').annotate(
        count=Count('id'),
        revenue=Sum('price')
    ).order_by('-revenue')
    
    package_data = []
    for stat in package_stats:
        package_data.append({
            'package': dict(WorkOrder.GIG_PACKAGE_CHOICES).get(stat['package_type'], stat['package_type']),
            'count': stat['count'],
            'revenue': float(stat['revenue'] or 0)
        })
    
    # Top performing gigs
    top_gigs = Gig.objects.annotate(
        total_orders=Count('orders', filter=Q(orders__is_paid=True)),
        total_revenue=Sum('orders__price', filter=Q(orders__is_paid=True))
    ).filter(total_orders__gt=0).order_by('-total_revenue')[:10]
    
    top_gigs_data = []
    for gig in top_gigs:
        top_gigs_data.append({
            'title': gig.title,
            'seller': gig.user.username,
            'orders': gig.total_orders or 0,
            'revenue': float(gig.total_revenue or 0),
            'rating': gig.gig_average_rating()
        })
    
    # Order status distribution
    status_stats = WorkOrder.objects.filter(is_paid=True).values('status').annotate(
        count=Count('id')
    )
    
    status_data = []
    for stat in status_stats:
        status_data.append({
            'status': dict(WorkOrder.ORDER_STATUS_CHOICES).get(stat['status'], stat['status']),
            'count': stat['count']
        })
    
    # Prepare orders data for JSON serialization
    orders_data = []
    for order in orders:
        orders_data.append({
            'id': order.id,
            'user': {'username': order.user.username},
            'gig': {'title': order.gig.title},
            'package_type': order.package_type,
            'created_at': order.created_at.isoformat(),
            'price': float(order.price),
            'is_paid': order.is_paid,
            'status': order.status,
            'status_display': dict(WorkOrder.ORDER_STATUS_CHOICES).get(order.status, order.status)
        })
    
    analytics_data = {
        "total_sales": float(total_sales),
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "active_orders": active_orders,
        "monthly_sales": float(monthly_sales),
        "weekly_sales": float(weekly_sales),
        "daily_sales": float(daily_sales),
        "last_sale": {
            "amount": float(last_sale.price) if last_sale else 0,
            "date": last_sale.created_at.isoformat() if last_sale else None,
            "user": last_sale.user.username if last_sale else None,
            "gig": last_sale.gig.title if last_sale else None
        } if last_sale else None,
        "sales_chart": {
            "dates": dates,
            "amounts": sales_data
        },
        "package_stats": package_data,
        "top_gigs": top_gigs_data,
        "status_stats": status_data
    }
    
    context = {
        "orders": orders,  # Keep for template if needed
        "orders_json": json.dumps(orders_data),
        "analytics_json": json.dumps(analytics_data),
        "analytics": analytics_data  # Keep for debugging
    }
    return render(request, "dashboard/admin_work_sales.html", context)



@login_required
def withdrawl_requests(request):
    if request.user.role != "admin":
        messages.error(request, "Access Denied!")
        return redirect("home")

    pending_requests = WithdrawalRequest.objects.filter(
        status__in=["PENDING", "PROCESSING"]
    )

    context = {
        "pending_requests": pending_requests
    }
    return render(request, "dashboard/withdrawl_requests.html", context)

@login_required
def withdraw_admin_detail(request, withdraw_id):
    if request.user.role != "admin":
        messages.error(request, "Access Denied!")
        return redirect("home")

    withdraw_request = WithdrawalRequest.objects.get(id=withdraw_id)

    if request.method == "POST":
        status = request.POST.get("status")
        withdraw_request.status = status
        if status == "FAILED":
            withdraw_request.user.available_earnings += Decimal(withdraw_request.amount + 3)
            withdraw_request.user.amount_being_cleared -= Decimal(
                withdraw_request.amount
            )
        elif status == "COMPLETED":
            withdraw_request.user.amount_being_cleared -= Decimal(
                withdraw_request.amount
            )
        withdraw_request.save()
        withdraw_request.user.save()

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
                        <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">Your Withdrawal Request is {status.capitalize()}!</h2>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {withdraw_request.user.username},</p>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">
                            Your withdrawal request of <strong>${withdraw_request.amount}</strong> has been updated to <strong>{status.capitalize()}</strong>. 
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
        send_email(withdraw_request.user.email, f"Your Withdrawal Request is {status.capitalize()}!", email_content)
        send_email('zainaligondal121@gmail.com', f"Our Admin took an Action on withdrawl from {withdraw_request.user.email}", email_content)

        Notification.objects.create(
            user=withdraw_request.user,
            app_name="workprenair",
            message=f"Your withdrawl request of ${withdraw_request.amount} is now {status.lower()}.",
        )
        messages.success(request, "Action on withdrawl request done!")
        return redirect("admin_withdrawal_requests")

    context = {
        "withdraw_request": withdraw_request,
    }

    return render(request, "dashboard/withdraw_admin_details.html", context)



def admin_traffic_logs(request):
    # Date filtering
    period = request.GET.get('period', 'day')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
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

    context = {
        'traffic_data': list(traffic_data),
        'total_visits': qs.count(),
        'countries': qs.values('country').annotate(total=Count('id'))
    }
    return render(request, 'dashboard/admin_traffic_logs.html', context)



def traffic_insights_json(request):
    period = request.GET.get('period', 'day')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
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
    
    return JsonResponse({
        'timeline': list(timeline_data),
        'countries': list(country_data),
        'devices': list(device_data),
        'top_pages': list(top_pages),
        'referrers': list(referrer_data),
        'total_visits': filtered_qs.count()
    })



#  ------------------------------ getch integration --------------------------------
from rest_framework.authtoken.models import Token


@login_required
def personal_access_token(request):
    token, created = Token.objects.get_or_create(user=request.user)
    
    if request.method == 'POST' and 'regenerate' in request.POST:
        token.delete()
        token = Token.objects.create(user=request.user)
        messages.success(request, "Token regenerated successfully.")

    return render(request, 'dashboard/access_token.html', {'token': token.key})


@csrf_exempt
def verify_access_token(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Token "):
        return JsonResponse({'error': 'Authorization header required'}, status=401)

    token_key = auth_header.split(" ")[1]

    try:
        token = Token.objects.get(key=token_key)
        user = token.user
        return JsonResponse({
            'username': user.username,
            'email': user.email,
            'status': 'valid'
        })
    except Token.DoesNotExist:
        return JsonResponse({'error': 'Invalid token'}, status=401)