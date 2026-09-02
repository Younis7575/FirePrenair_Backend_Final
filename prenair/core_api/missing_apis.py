"""
Missing REST API endpoints for FirePrenair.
These endpoints exist as Django template views but had no API version.
Added to support the Flutter mobile app.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.db.models import Q, Sum, Count
from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json
import uuid
import stripe
import os

from .serializers import *
from profiles.models import CustomUser, Notification
from home.models import *
from commu_prenair.models import (
    Post, Comment, ReplyComment, Like, Groupcategory, Group,
    GroupMemberShipRequests, Connection, FriendRequest,
    PrivateChat, Message, Event
)
from work_prenair.models import Category as WorkCategory, Tag, Gig, Order as WorkOrder, Delivery, Review as WorkReview, CustomOffer, Badge, Todo
from digi_prenair.models import Product, Category as DigiCategory, Cart, CartItem, Order as DigiOrder, OrderItem, Review as DigiReview, Project
from edu_prenair.models import (
    Course, CourseCategory, Module, Lesson, StudentEnrollment,
    CourseRating, CourseWishlist, CourseAnnouncement, Quiz, QuizQuestion,
    QuizAttempt, QuizQuestionResponse
)
from dashboard.models import (
    PayoutAccount, WithdrawalRequest, TrafficLog, TemplateCategory,
    Template, UserWebsite, Funnel, FunnelStep, FunnelProduct,
    FunnelOrder, FunnelLead, KYCProfile
)


# =============================================================================
# COMMUPRENAIR EVENTS API ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def events_list_api(request):
    """List all events"""
    events = Event.objects.all().order_by('-created_at')
    category_id = request.GET.get('category')
    if category_id:
        events = events.filter(category_id=category_id)
    
    paginator_data = []
    for event in events:
        paginator_data.append({
            'id': event.id,
            'title': event.title,
            'description': event.description,
            'start_time': event.start_time,
            'end_time': event.end_time,
            'is_virtual': event.is_virtual,
            'virtual_link': event.virtual_link,
            'location': event.location,
            'event_image': event.event_image.url if event.event_image else None,
            'slug': event.slug,
            'attendee_count': event.attendees.count(),
            'creator': {
                'username': event.creator.username,
                'name': event.creator.name,
                'slug': event.creator.slug,
                'profile_pic': event.creator.profile_pic.url if event.creator.profile_pic else None,
            },
            'is_attending': event.attendees.filter(id=request.user.id).exists(),
        })
    return Response({'events': paginator_data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_event_api(request):
    """Create a new event"""
    title = request.data.get('title')
    description = request.data.get('description')
    start_time = request.data.get('start_time')
    end_time = request.data.get('end_time')
    is_virtual = request.data.get('is_virtual', True)
    virtual_link = request.data.get('virtual_link', '')
    location = request.data.get('location', '')
    category_id = request.data.get('category')
    event_image = request.FILES.get('event_image')

    if not all([title, description, start_time, end_time]):
        return Response({'error': 'Title, description, start_time, and end_time are required.'},
                        status=status.HTTP_400_BAD_REQUEST)

    slug = slugify(title) + '-' + str(uuid.uuid4())[:6]

    event = Event.objects.create(
        title=title,
        description=description,
        creator=request.user,
        start_time=start_time,
        end_time=end_time,
        is_virtual=bool(is_virtual),
        virtual_link=virtual_link,
        location=location,
        category_id=category_id,
        event_image=event_image,
        slug=slug,
    )
    event.attendees.add(request.user)

    return Response({
        'message': 'Event created successfully.',
        'event': {
            'id': event.id,
            'title': event.title,
            'slug': event.slug,
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def event_detail_api(request, slug):
    """Get event detail"""
    event = get_object_or_404(Event, slug=slug)
    return Response({
        'id': event.id,
        'title': event.title,
        'description': event.description,
        'start_time': event.start_time,
        'end_time': event.end_time,
        'is_virtual': event.is_virtual,
        'virtual_link': event.virtual_link,
        'location': event.location,
        'event_image': event.event_image.url if event.event_image else None,
        'slug': event.slug,
        'attendee_count': event.attendees.count(),
        'creator': UserSerializer(event.creator).data,
        'is_attending': event.attendees.filter(id=request.user.id).exists(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_event_api(request, slug):
    """Join an event"""
    event = get_object_or_404(Event, slug=slug)
    event.attendees.add(request.user)
    return Response({'message': 'You have joined the event.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def leave_event_api(request, slug):
    """Leave an event"""
    event = get_object_or_404(Event, slug=slug)
    event.attendees.remove(request.user)
    return Response({'message': 'You have left the event.'})


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def edit_event_api(request, slug):
    """Edit an event"""
    event = get_object_or_404(Event, slug=slug)
    if event.creator != request.user:
        return Response({'error': 'Only the creator can edit this event.'},
                        status=status.HTTP_403_FORBIDDEN)

    for field in ['title', 'description', 'start_time', 'end_time', 'is_virtual', 'virtual_link', 'location']:
        if field in request.data:
            setattr(event, field, request.data[field])
    if 'category' in request.data:
        event.category_id = request.data['category']
    if 'event_image' in request.FILES:
        event.event_image = request.FILES['event_image']
    event.save()
    return Response({'message': 'Event updated successfully.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_ai_event_api(request):
    """Generate event details using AI (Groq)"""
    prompt = request.data.get('prompt', '')
    if not prompt:
        return Response({'error': 'Prompt is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an event planning assistant. Generate event details as JSON with keys: title, description, start_time (ISO format), end_time (ISO format), location, is_virtual (bool)."},
                {"role": "user", "content": prompt}
            ],
            model="llama3-8b-8192",
        )
        import markdown
        from django.utils.safestring import mark_safe
        result = json.loads(response.choices[0].message.content)
        return Response(result)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# WEBSITE BUILDER API ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_websites_api(request):
    """List user's websites"""
    websites = UserWebsite.objects.filter(user=request.user).order_by('-created_at')
    data = [{
        'id': w.id,
        'name': w.name,
        'is_published': w.is_published,
        'subdomain': w.subdomain,
        'custom_domain': w.custom_domain,
        'created_at': w.created_at,
    } for w in websites]
    return Response({'websites': data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_website_api(request):
    """Create a new website"""
    name = request.data.get('name', 'Untitled Website')
    template_id = request.data.get('template_id')
    edited_html = request.data.get('edited_html', '')
    subdomain = request.data.get('subdomain', '')

    template = None
    if template_id:
        template = get_object_or_404(Template, id=template_id)
        if not edited_html:
            edited_html = template.html_content

    website = UserWebsite.objects.create(
        user=request.user,
        name=name,
        template=template,
        edited_html=edited_html,
        subdomain=subdomain or f"{request.user.username}-{str(uuid.uuid4())[:6]}",
    )
    return Response({'message': 'Website created.', 'id': website.id}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_template_categories_api(request):
    """Get template categories"""
    categories = TemplateCategory.objects.all()
    data = [{'id': c.id, 'name': c.name} for c in categories]
    return Response({'categories': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def select_template_api(request):
    """List available templates"""
    category_id = request.GET.get('category')
    templates = Template.objects.all()
    if category_id:
        templates = templates.filter(category_id=category_id)
    data = [{
        'id': t.id,
        'name': t.name,
        'thumbnail': t.thumbnail.url if t.thumbnail else None,
        'category': t.category.name if t.category else None,
    } for t in templates]
    return Response({'templates': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_website_html_api(request, website_id):
    """Get website HTML content"""
    website = get_object_or_404(UserWebsite, id=website_id, user=request.user)
    return Response({
        'id': website.id,
        'name': website.name,
        'edited_html': website.edited_html,
        'is_published': website.is_published,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_website_api(request):
    """Save website HTML"""
    website_id = request.data.get('website_id')
    edited_html = request.data.get('edited_html', '')
    website = get_object_or_404(UserWebsite, id=website_id, user=request.user)
    website.edited_html = edited_html
    website.save()
    return Response({'message': 'Website saved.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def publish_website_api(request, website_id):
    """Publish/unpublish website"""
    website = get_object_or_404(UserWebsite, id=website_id, user=request.user)
    website.is_published = not website.is_published
    website.save()
    return Response({'message': 'Website published.' if website.is_published else 'Website unpublished.',
                     'is_published': website.is_published})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_website_api(request, website_id):
    """Delete website"""
    website = get_object_or_404(UserWebsite, id=website_id, user=request.user)
    website.delete()
    return Response({'message': 'Website deleted.'}, status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# FUNNEL SYSTEM API ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def funnel_list_api(request):
    """List user's funnels"""
    funnels = Funnel.objects.filter(user=request.user).order_by('-created_at')
    data = [{
        'id': f.id,
        'name': f.name,
        'department': f.department,
        'tag': f.tag,
        'is_active': f.is_active,
        'is_published': f.is_published,
        'subdomain': f.subdomain,
        'created_at': f.created_at,
    } for f in funnels]
    return Response({'funnels': data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_funnel_api(request):
    """Create a funnel"""
    name = request.data.get('name')
    department = request.data.get('department', '')
    tag = request.data.get('tag', 'ebooks')
    custom_tag = request.data.get('custom_tag', '')

    if not name:
        return Response({'error': 'Name is required.'}, status=status.HTTP_400_BAD_REQUEST)

    funnel = Funnel.objects.create(
        user=request.user,
        name=name,
        department=department,
        tag=tag,
        custom_tag=custom_tag,
    )
    return Response({'message': 'Funnel created.', 'id': funnel.id}, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def edit_funnel_api(request, funnel_id):
    """Edit a funnel"""
    funnel = get_object_or_404(Funnel, id=funnel_id, user=request.user)
    for field in ['name', 'department', 'tag', 'custom_tag', 'is_active']:
        if field in request.data:
            setattr(funnel, field, request.data[field])
    funnel.save()
    return Response({'message': 'Funnel updated.'})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_funnel_api(request, funnel_id):
    """Delete a funnel"""
    funnel = get_object_or_404(Funnel, id=funnel_id, user=request.user)
    funnel.delete()
    return Response({'message': 'Funnel deleted.'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def publish_funnel_api(request, funnel_id):
    """Toggle funnel publish status"""
    funnel = get_object_or_404(Funnel, id=funnel_id, user=request.user)
    funnel.is_published = not funnel.is_published
    funnel.save()
    return Response({'message': 'Funnel published.' if funnel.is_published else 'Funnel unpublished.',
                     'is_published': funnel.is_published})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def funnel_emails_by_tag_api(request):
    """Get funnel leads by tag"""
    tag = request.GET.get('tag', '')
    leads = FunnelLead.objects.filter(funnel__user=request.user, funnel__tag=tag)
    data = [{'name': l.name, 'email': l.email, 'created_at': l.created_at} for l in leads]
    return Response({'leads': data})


# =============================================================================
# AI GENERATION API ENDPOINTS (Dashboard)
# =============================================================================

class ImageGenerationAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """Generate image using Leonardo AI"""
        prompt = request.data.get('prompt', '')
        if not prompt:
            return Response({'error': 'Prompt is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            leonardo_api_key = settings.LEONARDO_API_KEY
            if not leonardo_api_key:
                return Response({'error': 'Leonardo API key not configured.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            import requests as http_requests
            headers = {"Authorization": f"Bearer {leonardo_api_key}", "Content-Type": "application/json"}
            response = http_requests.post(
                'https://api.leonardo.ai/v1/generations',
                headers=headers,
                json={"prompt": prompt, "num_images": 1, "width": 1024, "height": 1024}
            )
            return Response(response.json())
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoGenerationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Generate logo using Leonardo AI"""
        prompt = request.data.get('prompt', '')
        if not prompt:
            return Response({'error': 'Prompt is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            leonardo_api_key = settings.LEONARDO_API_KEY
            if not leonardo_api_key:
                return Response({'error': 'Leonardo API key not configured.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            import requests as http_requests
            headers = {"Authorization": f"Bearer {leonardo_api_key}", "Content-Type": "application/json"}
            response = http_requests.post(
                'https://api.leonardo.ai/v1/generations',
                headers=headers,
                json={"prompt": f"Logo design: {prompt}", "num_images": 1, "width": 1024, "height": 1024}
            )
            return Response(response.json())
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VideoGenerationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Generate video - placeholder for future Leonardo/video API"""
        prompt = request.data.get('prompt', '')
        return Response({'message': 'Video generation endpoint ready. Configure video API provider.',
                         'prompt': prompt})


class EbookGenerationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Generate ebook content using AI"""
        prompt = request.data.get('prompt', '')
        if not prompt:
            return Response({'error': 'Prompt is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY)
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an expert ebook writer. Generate structured ebook content in markdown format."},
                    {"role": "user", "content": prompt}
                ],
                model="llama3-8b-8192",
            )
            content = response.choices[0].message.content
            return Response({'content': content})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GeneratePdfAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Generate PDF from content"""
        content = request.data.get('content', '')
        return Response({'message': 'PDF generation endpoint ready. Content received.',
                         'content_length': len(content)})


# =============================================================================
# WORK PRENAIR MISSING API ENDPOINTS
# =============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def suggest_gig_pricing_api(request, slug):
    """AI-suggested gig pricing"""
    gig = get_object_or_404(Gig, slug=slug, user=request.user)
    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        prompt = f"Suggest pricing for a gig titled '{gig.title}' with description: {gig.description[:200]}. Current basic price: ${gig.basic_price}, standard: ${gig.standard_price}, premium: ${gig.premium_price}. Suggest improved pricing as JSON with keys: basic_price, standard_price, premium_price, reasoning."
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a pricing expert for freelance services. Respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            model="llama3-8b-8192",
        )
        import json
        result = json.loads(response.choices[0].message.content)
        return Response({'suggestions': result})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_proposal_description_api(request):
    """Generate proposal/gig description using AI"""
    prompt = request.data.get('prompt', '')
    gig_title = request.data.get('gig_title', '')
    if not prompt and not gig_title:
        return Response({'error': 'Prompt or gig_title is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an expert copywriter for freelancing platforms. Generate professional proposals/descriptions."},
                {"role": "user", "content": prompt or f"Write a compelling gig description for: {gig_title}"}
            ],
            model="llama3-8b-8192",
        )
        return Response({'description': response.choices[0].message.content})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# EDUPRENAIR MISSING API ENDPOINTS
# =============================================================================

class GenerateSpeechAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Generate speech audio using ElevenLabs"""
        text = request.data.get('text', '')
        voice_id = request.data.get('voice_id', '')
        if not text:
            return Response({'error': 'Text is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from elevenlabs.client import ElevenLabs
            from elevenlabs import Voice
            client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY', ''))
            audio = client.generate(text=text, voice=voice_id or "Rachel")
            return Response({'audio': audio}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_module_lessons_api(request, course_slug):
    """AI-generate lessons for a module"""
    course = get_object_or_404(Course, slug=course_slug, instructor=request.user)
    module_title = request.data.get('module_title', '')
    count = int(request.data.get('count', 5))

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": f"Generate {count} lesson titles for module '{module_title}' in course '{course.title}'. Return JSON array of objects with keys: title, description."},
                {"role": "user", "content": f"Generate lessons for: {module_title}"}
            ],
            model="llama3-8b-8192",
        )
        lessons = json.loads(response.choices[0].message.content)
        return Response({'lessons': lessons})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_lesson_api(request, lesson_id):
    """Delete a lesson"""
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course__instructor=request.user)
    lesson.delete()
    return Response({'message': 'Lesson deleted.'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def edit_lesson_api(request, lesson_id):
    """Edit a lesson"""
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course__instructor=request.user)
    for field in ['title', 'description', 'order']:
        if field in request.data:
            setattr(lesson, field, request.data[field])
    if 'video' in request.FILES:
        lesson.video = request.FILES['video']
    lesson.save()
    return Response({'message': 'Lesson updated.'})


# =============================================================================
# DIGIPRENAIR MISSING API ENDPOINTS
# =============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_project_api(request):
    """Add product to project"""
    product_id = request.data.get('product_id')
    project_name = request.data.get('project_name', '')
    product = get_object_or_404(Product, id=product_id)

    project, created = Project.objects.get_or_create(
        user=request.user,
        name=project_name or 'My Project'
    )

    # Create order item for this product
    order_item = OrderItem.objects.create(
        order=None,
        product=product,
        quantity=1,
        price=product.price,
    )
    project.order_items.add(order_item)
    project.save()

    return Response({'message': f'Product added to project "{project.name}".'},
                    status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def digi_projects_api(request):
    """List user's projects"""
    projects = Project.objects.filter(user=request.user)
    data = [{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'created_at': p.created_at,
        'items_count': p.order_items.count(),
    } for p in projects]
    return Response({'projects': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def digi_project_detail_api(request, project_id):
    """Get project detail"""
    project = get_object_or_404(Project, id=project_id, user=request.user)
    items = OrderItemSerializer(project.order_items.all(), many=True).data
    return Response({
        'id': project.id,
        'name': project.name,
        'description': project.description,
        'items': items,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_product_file_api(request, product_id):
    """Download purchased product file"""
    product = get_object_or_404(Product, id=product_id)
    # Verify user has purchased
    has_purchased = OrderItem.objects.filter(
        order__user=request.user,
        product=product,
        order__is_paid=True
    ).exists()
    if not has_purchased:
        return Response({'error': 'You have not purchased this product.'},
                        status=status.HTTP_403_FORBIDDEN)
    if product.downloadable_file:
        from django.http import FileResponse
        return FileResponse(product.downloadable_file.open(), as_attachment=True,
                            filename=product.downloadable_file.name.split('/')[-1])
    return Response({'error': 'No file available for download.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_digiprenair_upload_url_api(request):
    """Generate presigned S3 URL for product upload"""
    if not settings.USE_S3_STORAGE:
        return Response({'error': 'S3 storage not configured.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    filename = request.data.get('filename', 'upload.zip')
    content_type = request.data.get('content_type', 'application/zip')

    try:
        import boto3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        key = f"digiprenair_product_files/{request.user.id}/{uuid.uuid4()}_{filename}"
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': key, 'ContentType': content_type},
            ExpiresIn=3600,
        )
        return Response({'upload_url': presigned_url, 'key': key})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# DASHBOARD MISSING API ENDPOINTS
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_referrals_api(request):
    """Get referral information"""
    referrals = CustomUser.objects.filter(referred_by=request.user)
    data = [{
        'id': u.id,
        'username': u.username,
        'name': u.name,
        'email': u.email,
        'created_at': u.created_at,
    } for u in referrals]
    return Response({
        'referral_code': request.user.referral_code,
        'referral_count': referrals.count(),
        'referrals': data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def personal_access_token_api(request):
    """Get or create personal access token"""
    from rest_framework.authtoken.models import Token
    token, created = Token.objects.get_or_create(user=request.user)
    return Response({'token': token.key, 'created': created})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_access_token_api(request):
    """Verify a personal access token"""
    from rest_framework.authtoken.models import Token
    token_key = request.data.get('token', '')
    try:
        token = Token.objects.get(key=token_key)
        return Response({'valid': True, 'user_id': token.user_id})
    except Token.DoesNotExist:
        return Response({'valid': False}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_student_progress_api(request):
    """AI-analyze student progress"""
    course_slug = request.data.get('course_slug', '')
    course = get_object_or_404(Course, slug=course_slug, instructor=request.user)
    enrollments = StudentEnrollment.objects.filter(course=course)

    total_students = enrollments.count()
    avg_progress = sum(e.progress for e in enrollments) / total_students if total_students > 0 else 0
    completed = enrollments.filter(is_completed=True).count()

    return Response({
        'course': course.title,
        'total_students': total_students,
        'average_progress': round(avg_progress, 2),
        'completed_students': completed,
        'completion_rate': round((completed / total_students * 100) if total_students > 0 else 0, 2),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def course_stats_api(request, course_slug):
    """Get course statistics"""
    course = get_object_or_404(Course, slug=course_slug, instructor=request.user)
    enrollments = StudentEnrollment.objects.filter(course=course)
    ratings = CourseRating.objects.filter(course=course)

    return Response({
        'total_enrolled': enrollments.count(),
        'completed': enrollments.filter(is_completed=True).count(),
        'average_progress': round(
            sum(e.progress for e in enrollments) / enrollments.count(), 2
        ) if enrollments.exists() else 0,
        'average_rating': round(
            sum(r.rating for r in ratings) / ratings.count(), 2
        ) if ratings.exists() else 0,
        'total_ratings': ratings.count(),
        'total_revenue': float(course.enrolled_students.count() * course.price),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def digi_reviews_api(request):
    """Get reviews for digiprenair products"""
    reviews = DigiReview.objects.filter(product__seller=request.user).order_by('-created_at')
    data = [{
        'id': r.id,
        'product': r.product.title,
        'user': r.user.username,
        'rating': r.rating,
        'body': r.body,
        'created_at': r.created_at,
    } for r in reviews]
    return Response({'reviews': data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def manage_item_digiprenair_api(request):
    """Manage digiprenair item (activate/deactivate)"""
    product_id = request.data.get('product_id')
    action = request.data.get('action', 'toggle')
    product = get_object_or_404(Product, id=product_id, seller=request.user)

    if action == 'delete':
        product.delete()
        return Response({'message': 'Product deleted.'})
    return Response({'message': 'Action completed.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_child_categories_digi_api(request):
    """Get digiprenair child categories"""
    parent_id = request.GET.get('parent_id')
    if not parent_id:
        return Response({'categories': []})
    categories = DigiCategory.objects.filter(parent_id=parent_id)
    data = [{'id': c.id, 'name': c.name} for c in categories]
    return Response({'categories': data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_description_eduprenair_api(request):
    """AI generate course description"""
    prompt = request.data.get('prompt', '')
    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Generate a compelling course description in markdown."},
                {"role": "user", "content": prompt}
            ],
            model="llama3-8b-8192",
        )
        return Response({'description': response.choices[0].message.content})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_description_digiprenair_api(request):
    """AI generate product description"""
    prompt = request.data.get('prompt', '')
    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Generate a compelling digital product description in markdown."},
                {"role": "user", "content": prompt}
            ],
            model="llama3-8b-8192",
        )
        return Response({'description': response.choices[0].message.content})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_description_workprenair_api(request):
    """AI generate gig description"""
    prompt = request.data.get('prompt', '')
    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Generate a compelling gig/service description for a freelancing platform."},
                {"role": "user", "content": prompt}
            ],
            model="llama3-8b-8192",
        )
        return Response({'description': response.choices[0].message.content})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# HOME API MISSING ENDPOINTS
# =============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def home_chatbot_api(request):
    """Home page chatbot"""
    user_message = request.data.get('message', '')
    if not user_message:
        return Response({'error': 'Message is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are FirePrenair's AI assistant. Help users with questions about the platform."},
                {"role": "user", "content": user_message}
            ],
            model="llama3-8b-8192",
        )
        import markdown
        from django.utils.safestring import mark_safe
        reply = markdown.markdown(response.choices[0].message.content)
        return Response({'message': mark_safe(reply)})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
