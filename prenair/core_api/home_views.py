from django.shortcuts import render, redirect
from .models import *
from django.core.exceptions import ValidationError
from django.contrib import messages
from edu_prenair.models import *
from digi_prenair.models import *
from work_prenair.models import Category as WorkCategory, Gig
from commu_prenair.models import Groupcategory, Group, Post
from django.conf import settings


# ai 
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.safestring import mark_safe
import markdown
from groq import Groq





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





knowledge_base = {
    "platform_info": """
        Fireprenair is an all-in-one platform offering productivity tools, educational resources, networking opportunities, 
        and freelancing solutions through four integrated apps. Each app is designed to address unique user needs, 
        from learning and selling digital products to professional networking and service-based project collaborations. 
        All platforms are powered by AI to enhance user experience and productivity.
    """,
    "services": """
        Fireprenair provides a diverse range of services, including:
        - AI-powered tools for task automation and business optimization.
        - A learning platform with courses covering business management, technology, and skills enhancement.
        - Networking forums for professionals to connect and collaborate.
        - A marketplace for digital goods like templates, eBooks, and software.
        - A service exchange platform connecting freelancers and clients for project execution.
    """,
    "eduprenair": """
        Eduprenair is the learning hub of Fireprenair, offering:
        - Courses on business management, AI technology, digital marketing, and consultancy.
        - Resources designed to help users gain skills to succeed in competitive environments.
        - Accessible materials for beginners and advanced learners, ensuring comprehensive growth.
        - AI-driven personalization to match users with the most relevant courses and materials.
    """,
    "digiprenair": """
        Digiprenair serves as the marketplace for digital products, featuring:
        - A platform to buy and sell digital assets, including templates, graphics, and software.
        - Tools allowing creators to request and offer custom products tailored to specific needs.
        - Resources to help businesses and individuals enhance productivity through curated digital solutions.
        - AI-powered recommendations to optimize buying and selling experiences.
    """,
    "commuprenair": """
        Commuprenair facilitates professional networking and collaboration through:
        - Public and private forums for discussions, idea sharing, and problem-solving.
        - Direct messaging and group chats for meaningful conversations.
        - Opportunities to connect with experts and like-minded individuals.
        - AI-driven networking tools to suggest relevant connections and discussions.
    """,
    "workprenair": """
        Workprenair is a service exchange platform connecting freelancers and clients:
        - Users can offer or request services for various projects, from creative work to consultancy.
        - Tools to streamline freelancing workflows, ensuring seamless collaboration.
        - A user-friendly interface to post, manage, and complete projects efficiently.
        - AI-based project matching to connect users with suitable freelancers or clients.
    """,
    "community": """
        Fireprenair nurtures a vibrant community by providing:
        - Discussion forums to share insights and explore solutions.
        - Private and public chat groups to foster collaboration and professional relationships.
        - Support for project-based discussions aligning goals with actionable outcomes.
        - AI-enhanced features for tailored community interactions and recommendations.
    """,
    "consultations": """
        Fireprenair supports users with expert consultations through:
        - Personalized guidance for business strategies, AI integration, and project management.
        - Custom project execution services tailored to specific business needs.
        - A streamlined process for users to connect with professionals for tailored advice.
        - AI-backed tools to provide data-driven insights and recommendations during consultations.
    """,
    "marketplace": """
        The Fireprenair marketplace, powered by Digiprenair, features:
        - Digital products, including eBooks, software, graphics, templates, and courses.
        - Tools to help users improve efficiency, acquire new skills, and grow their businesses.
        - AI-driven insights to highlight trending and high-demand products.
    """,
    "ai_creation": """
        Fireprenair was created by the talented duo Zain Ali and Hamza Abdul Jabbar, skilled Django and Python developers. 
        They designed the platform to integrate AI-powered solutions, enhancing user productivity and enabling businesses to thrive.
    """,
    "developer_info": """
        Zain Ali and Hamza Abdul Jabbar, lead developers of Fireprenair, bring extensive experience in Python and Django. 
        Their collaborative effort and expertise have built a comprehensive platform tailored to help businesses and individuals achieve success.
    """
}


@api_view(["POST"])
@permission_classes([AllowAny])
def home_chatbot_view_api(request):
    user_message = str(request.data.get('message') or '').strip()
    if not user_message:
        return Response({"error": "Message is required."}, status=400)
    lowered = user_message.lower()

    # Predefined responses for quick replies
    predefined_responses = {
        "name": "I am your customer support assistant, here to help you with any questions about Fireprenair.",
        "who_created_you": "I was created by the development team of Fireprenair.",
        "what_can_you_do": "I can help you navigate our platform, answer questions about our services, and provide consultation details.",
    }

    for key, response in predefined_responses.items():
        if key in lowered:
            return Response({"message": response})

    # Interact with Groq API. `llama3-8b-8192` was retired, so fall back
    # through the current models; any provider failure answers 503.
    system_prompt = json.dumps({
        "knowledge_base": knowledge_base,
        "instruction": "Please generate short, clear, and professional responses. "
                       "Limit unnecessary details, ensure the tone is formal, and provide concise answers. "
                       "Avoid elaboration and keep responses to the point."
                       "Give answer according to question."
    })
    bot_reply = None
    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        for model in ("llama-3.1-8b-instant", "llama-3.3-70b-versatile", "llama3-8b-8192"):
            try:
                groq_response = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    model=model,
                )
                bot_reply = groq_response.choices[0].message.content.strip()
                break
            except Exception:
                continue
    except Exception:
        bot_reply = None
    if not bot_reply:
        return Response({"error": "The assistant is unavailable right now. Please try again later."}, status=503)

    bot_reply_html = mark_safe(markdown.markdown(bot_reply))
    return Response({"message": bot_reply_html})
from django.utils.translation import gettext as _
from digi_prenair.models import Category as digiCategory


def _home_top_sellers():
    try:
        from dashboard.decorators import get_top_sellers
        return get_top_sellers(count=1)
    except Exception:
        return []

@api_view(["GET"])
@permission_classes([AllowAny])
def home_api(request):
    try:
            
        best_courses = list(Course.objects.filter(is_published=True, best_selling=True))
        best_products = list(Product.objects.filter(is_featured=True))
        best_services = list(Gig.objects.filter(featured=True))
        best_groups = list(Group.objects.filter(is_featured=True))

        show_register_popup = request.GET.get('register') == 'true'
        show_login_popup = 'login' in request.GET and request.GET.get('login') in ('true', '')

        work_featured_categories = list(WorkCategory.objects.filter(is_featured=True))
        edu_featured_categories = list(CourseCategory.objects.filter(is_featured=True))
        digi_featured_categories = digiCategory.objects.filter(is_featured=True)
        commu_featured_categories = list(Groupcategory.objects.filter(is_featured=True))

        data = {
            "best_courses": CourseSerializer(best_courses, many=True).data,
            "best_products": ProductSerializer(best_products, many=True).data,
            "best_services": GigSerializer(best_services, many=True).data,
            "best_groups": GroupSerializer(best_groups, many=True).data,
            "work_featured_categories": WorkCategorySerializer(work_featured_categories, many=True).data,
            "edu_featured_categories": CourseCategorySerializer(edu_featured_categories, many=True).data,
            "digi_featured_categories": digiCategorySerializer(digi_featured_categories, many=True).data,
            "commu_featured_categories": GroupCategorySerializer(commu_featured_categories, many=True).data,
            "show_register_popup": show_register_popup,
            "show_login_popup": show_login_popup,
            # homepage.html's hero "LEADS THE PLATFORM" card (no. 1 seller)
            "top_sellers": _home_top_sellers(),
        }
        _add_home_card_fields(data, best_courses, best_products, best_services, best_groups,
                              work_featured_categories, edu_featured_categories,
                              commu_featured_categories)
        return Response(data)


    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    
    

def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _media(f):
    try:
        return f.url if f else None
    except Exception:
        return None


def _add_home_card_fields(data, courses, products, gigs, groups, work_cats, edu_cats, commu_cats):
    """Additive keys for homepage.html's cards/carousels (the template reads
    these off model methods: gig_count, course_count, group_count,
    course_price, effective_price, five-star counts ...)."""
    for key, qs, attr in (
        ("work_featured_categories", work_cats, "gig_count"),
        ("edu_featured_categories", edu_cats, "course_count"),
        ("commu_featured_categories", commu_cats, "group_count"),
    ):
        for row, obj in zip(data[key], qs):
            row["count"] = _safe(lambda: getattr(obj, attr)(), 0)
    for row in data["digi_featured_categories"]:
        row["count"] = row.get("item_count", 0)
    for row, g in zip(data["best_services"], gigs):
        u = g.user
        row["card"] = {
            "price": _safe(lambda: str(g.basic_price)),
            "delivery_days": _safe(lambda: g.basic_delivery_time),
            "category": _safe(lambda: g.category_level_1.name),
            "seller_name": _safe(lambda: u.username),
            "seller_pic": _safe(lambda: _media(u.profile_pic)),
            "review_count": _safe(lambda: g.gig_fivestar_reviews().count(), 0),
            "image": _safe(lambda: _media(g.image)),
        }
    for row, c in zip(data["best_courses"], courses):
        ins = c.instructor
        row["card"] = {
            "price": _safe(lambda: str(c.course_price())),
            "old_price": _safe(lambda: str(c.price) if c.is_course_on_discount() else None),
            "lessons": _safe(lambda: c.total_lessons(), 0),
            "duration": _safe(lambda: c.duration),
            "instructor_name": _safe(lambda: ins.name),
            "instructor_pic": _safe(lambda: _media(ins.profile_pic)),
            "review_count": _safe(lambda: (c.courserating_set.filter(rating=5).count()), 0),
            "image": _safe(lambda: _media(c.thumbnail)),
        }
    for row, p in zip(data["best_products"], products):
        sel = p.seller
        row["card"] = {
            "price": _safe(lambda: str(p.effective_price())),
            "category": _safe(lambda: p.category.name),
            "seller_name": _safe(lambda: sel.username),
            "seller_pic": _safe(lambda: _media(sel.profile_pic)),
            "review_count": _safe(lambda: p.five_star_rating(), 0),
            "image": row.get("image") or _safe(lambda: _media(p.image)),
        }
    for row, grp in zip(data["best_groups"], groups):
        adm = grp.admin
        row["card"] = {
            "category": _safe(lambda: grp.category_l_1.name),
            "admin_name": _safe(lambda: adm.username),
            "admin_pic": _safe(lambda: _media(adm.profile_pic)),
            "image": _safe(lambda: _media(grp.profile_img)),
        }


from django.core.validators import validate_email
from django.core.exceptions import ValidationError

@api_view(["POST"])
@permission_classes([AllowAny])
def home_subscribe_api(request):
    name = request.data.get("name")
    email = request.data.get("email")
    errors = {}

    if not name:
        errors["name"] = "Name is required."
    
    if not email:
        errors["email"] = "Email is required."
    else:
        try:
            validate_email(email)
        except ValidationError:
            errors["email"] = "Enter a valid email address."

        if Subscribe.objects.filter(email=email).exists():
            errors["email"] = "This email is already subscribed."

    if errors:
        return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    # Create subscription
    Subscribe.objects.create(name=name, email=email)
    return Response({"message": "You have successfully subscribed!"}, status=status.HTTP_201_CREATED)

# ------------------------- Category API's -------------------------
@api_view(["GET"])
@permission_classes([AllowAny])
def work_parent_categories_api(request):
    categories = WorkCategory.objects.filter(parent=None)[:5]
    serializer = WorkCategorySerializer(categories, many=True)
    return Response(serializer.data)



@api_view(["GET"])
@permission_classes([AllowAny])
def edu_parent_categories_api(request):
    categories = CourseCategory.objects.filter(parent=None)[:5]
    serializer = CourseCategorySerializer(categories, many=True)
    return Response(serializer.data)


class DigiParentCategoriesView(APIView):
    # Public: the explore screen renders these before the user signs in.
    permission_classes = [AllowAny]

    def get(self, request):
        # This class is DigiPrenair's; it served WorkPrenair's categories, whose
        # ids mean nothing to a digi Product. Use the digi Category table.
        from digi_prenair.models import Category as DigiCategory
        categories = DigiCategory.objects.filter(parent=None)[:5]
        data = [
            {
                'id': c.id,
                'name': c.name,
                'description': c.description or '',
                'img': c.img.url if c.img else None,
                'item_count': c.item_count,
                'color': c.color,
                'is_featured': c.is_featured,
                'parent': c.parent_id,
                'subcategories': [
                    {'id': ch.id, 'name': ch.name}
                    for ch in c.digi_subcategories.all()
                ],
            }
            for c in categories
        ]
        return Response(data)

@api_view(["GET"])
@permission_classes([AllowAny])
def commu_parent_categories_api(request):
    categories = Groupcategory.objects.filter(parent=None)
    data = []
    for category in categories[:5]:
        data.append({
            'id': category.id,
            'name': category.name,
            'description': category.desc
        })
    return JsonResponse(data, safe=False)







# ------------------------- Static page content -------------------------
# The legal / company / resource pages carry no database content: their text is
# in the website templates.  ``page_content.build_page`` renders the template
# and returns it as a block tree (see page_content.py) so the apps can show the
# same copy.  The original ``message`` key is kept for older clients.
from .page_content import build_page as _build_page


def _page_response(template_name, message, extra=None):
    try:
        data = _build_page(template_name)
    except Exception as exc:  # never 500 a public page
        return Response({"message": message, "error": str(exc)},
                        status=status.HTTP_200_OK)
    data["message"] = message
    data["slug"] = template_name.replace('.html', '')
    if extra:
        data.update(extra)
    return Response(data)

# ------------------------- Legal Pages -------------------------
# Every page below is public, read-only content: the Flutter app renders the
# legal/company pages from the sign-up and login screens, before any token
# exists, so each view opts out of the global IsAuthenticated default.

@api_view(['GET'])
@permission_classes([AllowAny])
def terms_of_use_api(request):
    return _page_response('terms.html', " Render to Terms of Use page")

@api_view(['GET'])
@permission_classes([AllowAny])
def license_agreement_api(request):
    return _page_response('license_agreement.html', "Render to License Agreement page")

@api_view(['GET'])
@permission_classes([AllowAny])
def privacy_policy_api(request):
    return _page_response('privacy_policy.html', "Privacy Policy page")

@api_view(['GET'])
@permission_classes([AllowAny])
def copyright_info_api(request):
    return _page_response('copyright_info.html', "Render to Copyright Info page")

@api_view(['GET'])
@permission_classes([AllowAny])
def cookies_api(request):
    return _page_response('cookies.html', "Render to Cookies Policy page")

@api_view(['GET'])
@permission_classes([AllowAny])
def dmca_policy_api(request):
    return _page_response('dmca_policy.html', "Render to DMCA Policy page")

@api_view(['GET'])
@permission_classes([AllowAny])
def privacy_choice_policy_api(request):
    return _page_response('privacy_choice_policy.html', "Render to Privacy Choice Policy page")

@api_view(['GET'])
@permission_classes([AllowAny])
def refund_policy_api(request):
    return _page_response('refund_policy.html', "Render to Refund Policy page")

# ------------------------- Company Pages -------------------------
@api_view(['GET'])
@permission_classes([AllowAny])
def about_us_api(request):
    return _page_response('about_us.html', "Render to About Us page")

@api_view(['GET'])
@permission_classes([AllowAny])
def contact_support_api(request):
    return _page_response('contact_support.html', "Render to Contact Support page")

@api_view(['GET'])
@permission_classes([AllowAny])
def help_support_api(request):
    return _page_response('help_support.html', "Render to Help & Support page")

@api_view(['GET'])
@permission_classes([AllowAny])
def how_it_works_api(request):
    return _page_response('how_it_works.html', "Render to How It Works page")

@api_view(['GET'])
@permission_classes([AllowAny])
def pricing_api(request):
    plans = PricingPlan.objects.all().order_by('price_monthly')
    serializer = PricingPlanSerializer(plans, many=True)
    data = {"plans": serializer.data}
    # Additive: the website's per-plan bullet lists / key features (kept in the
    # template, not the DB), with the matching DB plan id and prices attached.
    try:
        from .page_content import build_pricing_cards
        by_title = {p['title']: p for p in serializer.data}
        extra = build_pricing_cards()
        for card in extra['plan_cards']:
            card['plan'] = by_title.get(card['db_title'])
        data.update(extra)
    except Exception as exc:
        data['plan_cards_error'] = str(exc)
    return Response(data)

@api_view(['GET'])
@permission_classes([AllowAny])
def fees_commisions_api(request):
    return _page_response('fees_commisions.html', "Render toFees & Commissions page")

@api_view(['GET'])
@permission_classes([AllowAny])
def faq_api(request):
    return _page_response('faq.html', "Render to FAQ page")

# ------------------------- Resources Pages -------------------------
@api_view(['GET'])
@permission_classes([AllowAny])
def training_api(request):
    return _page_response('training.html', "Render to Training page")

@api_view(['GET'])
@permission_classes([AllowAny])
def digital_products_api(request):
    return _page_response('digital_products.html', "Render to Digital Products page")

@api_view(['GET'])
@permission_classes([AllowAny])
def affiliates_api(request):
    return _page_response('affiliates.html', "Render to Affiliates page")

@api_view(['GET'])
@permission_classes([AllowAny])
def partnerships_api(request):
    return _page_response('partnerships.html', "Render to Partnerships page")

@api_view(['GET'])
@permission_classes([AllowAny])
def community_api(request):
    return _page_response('community.html', "Render to Community page")

# Extra Pages
@api_view(['GET'])
def custom_404_api(request, exception):
    return JsonResponse({"error": "Not Found", "message": "The requested resource was not found."}, status=404)
@api_view(['GET'])
def custom_500_api(request):
    return JsonResponse({"error": "Server Error", "message": "An internal server error occurred."}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def corporate_solutions_api(request):
    """corporate_solutions.html as a block tree + the project form choices."""
    from home.models import CorporateProject
    return _page_response('corporate_solutions.html', "Render to Corporate Solutions page", {
        'categories': [{'value': v, 'label': l} for v, l in CorporateProject.CATEGORY_CHOICES],
        'budgets': [{'value': v, 'label': l} for v, l in CorporateProject.BUDGET_CHOICES],
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def features_api(request):
    return _page_response('features.html', "Render to Features page")


@api_view(['GET'])
@permission_classes([AllowAny])
def feature_detail_api(request):
    feature_pg = request.GET.get('feature')
    if feature_pg not in ('work', 'edu', 'digi', 'commu'):
        return Response({"message": "Render to Feature detail page"}, status=status.HTTP_200_OK)
    return _page_response('features_detail_%s.html' % feature_pg,
                          "Render to Feature  page", {"feature": feature_pg})




# ------------------------- Subscriptions to our plans -------------------------
# from django.db.utils import IntegrityError
# def save_categories_with_hierarchy(top_category_name, subcategories):
#     """
#     Save a hierarchy of categories with a top category and its subcategories.
    
#     :param top_category_name: The name of the top-level category.
#     :param subcategories: A dictionary where keys are subcategory names and values are lists of child category names.
#     """
#     try:
#         top_category, created = Groupcategory.objects.get_or_create(name=top_category_name, parent=None)
#         if created:
#             print(f"Top category '{top_category_name}' created successfully.")
#         else:
#             print(f"Top category '{top_category_name}' already exists.")

#         for subcategory_name, child_categories in subcategories.items():
#             subcategory, created = Groupcategory.objects.get_or_create(name=subcategory_name, parent=top_category)
#             if created:
#                 print(f"Subcategory '{subcategory_name}' added successfully under '{top_category_name}'.")
#             else:
#                 print(f"Subcategory '{subcategory_name}' already exists under '{top_category_name}'.")

#             for child_name in child_categories:
#                 try:
#                     Groupcategory.objects.create(name=child_name, parent=subcategory)
#                     print(f"Child category '{child_name}' added under subcategory '{subcategory_name}'.")
#                 except IntegrityError:
#                     print(f"Child category '{child_name}' already exists under subcategory '{subcategory_name}'. Skipping.")
#                 except Exception as e:
#                     print(f"An error occurred while saving child category '{child_name}': {e}")

#     except Exception as e:
#         print(f"An error occurred while processing the hierarchy: {e}")


# # Example usage
# top_category = "Business Networking"
# subcategories_with_children = {
#     "Industry Networking": [
#         "Tech Guides",
#         "Healthcare Resources",
#         "Creative Strategies",
#         "Finance Templates",
#         "Education Resources",
#         "Real Estate Tools",
#         "Legal Guides",
#         "Marketing Templates",
#         "Entrepreneur Resources",
#         "Nonprofit Strategies",
#     ],
#     "Event Networking": [
#         "Event Checklists",
#         "Virtual Strategies",
#         "Conference Templates",
#         "Trade Show Guides",
#         "Speed Templates",
#         "Follow-Up Emails",
#         "Icebreaker Guides",
#         "Business Cards",
#         "Workshop Materials",
#         "Event Forms",
#     ],
#     "Online Networking": [
#         "LinkedIn Guides",
#         "Meeting Templates",
#         "Bio Templates",
#         "Social Strategies",
#         "Group Guidelines",
#         "Video Etiquette",
#         "Pitch Templates",
#         "Branding Tips",
#         "Collaboration Tools",
#         "Webinar Strategies",
#     ],
#     "Executive Networking": [
#         "C-Suite Strategies",
#         "Boardroom Guides",
#         "Leadership Templates",
#         "Partnership Tools",
#         "Investor Resources",
#         "Association Materials",
#         "Succession Guides",
#         "High-Level Checklists",
#         "Club Resources",
#         "Cross-Tools",
#     ],
#     "Mentorship & Peer Networking": [
#         "Mentorship Guides",
#         "Peer Templates",
#         "Mentor Agreements",
#         "Skill Exchange",
#         "Co-Working Guides",
#         "Growth Checklists",
#         "Accountability Templates",
#         "Alumni Strategies",
#         "Learning Guides",
#         "Leadership Resources",
#     ],
# }


# save_categories_with_hierarchy(top_category, subcategories_with_children)
