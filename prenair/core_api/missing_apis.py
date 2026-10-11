"""
Missing REST API endpoints for FirePrenair.
These endpoints exist as Django template views but had no API version.
Added to support the Flutter mobile app.
"""
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.http import Http404
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
from django.utils.dateparse import parse_datetime as _parse_dt
from django.db.models import Q as _Q


def _bool(value, default=False):
    """Form values arrive as strings ('true' / 'True' / 'on' / '1')."""
    if value is None or value == '':
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('true', '1', 'yes', 'on', 't')


def _dt(value):
    """Parse an ISO / datetime-local value; None when it is not a datetime."""
    if not value:
        return None
    if hasattr(value, 'isoformat'):
        return value
    text = str(value).strip().replace(' ', 'T', 1) if 'T' not in str(value) else str(value).strip()
    parsed = _parse_dt(text)
    if parsed is None:
        # 'YYYY-MM-DDTHH:MM' without seconds is accepted by parse_datetime;
        # a bare date is not -- treat it as midnight.
        from django.utils.dateparse import parse_date
        d = parse_date(text[:10])
        if d:
            import datetime as _d
            parsed = _d.datetime.combine(d, _d.time())
    if parsed is not None and timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _pic(user):
    return user.profile_pic.url if user and user.profile_pic else None


def _event_dict(event, request, detail=False):
    """One event, in the shape every events screen reads.

    Adds what the website's event_list.html / event_detail.html show and the
    app could not: the category (`category` id, `category_id`, `category_name`),
    `created_at` ("<n> ago"), who is registered, and whether the caller is the
    host (shows Edit). Existing keys are unchanged.
    """
    cat = event.category
    attendees = list(event.attendees.all()[:8])
    data = {
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
        'category': cat.id if cat else None,
        'category_id': cat.id if cat else None,
        'category_name': cat.name if cat else None,
        'created_at': event.created_at,
        'is_creator': event.creator_id == request.user.id,
        'is_attending': event.attendees.filter(id=request.user.id).exists(),
        'attendees': [
            {'username': a.username, 'name': a.name, 'slug': a.slug, 'profile_pic': _pic(a)}
            for a in attendees
        ],
    }
    if detail:
        creator = UserSerializer(event.creator, context={'request': request}).data
        creator['profile_pic'] = _pic(event.creator)
        data['creator'] = creator
    else:
        data['creator'] = {
            'username': event.creator.username,
            'name': event.creator.name,
            'slug': event.creator.slug,
            'profile_pic': _pic(event.creator),
        }
    return data


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def events_list_api(request):
    """List all events (?category=<id>&q=<text>, like the website's filters)."""
    events = Event.objects.all().order_by('-created_at')
    category_id = request.GET.get('category')
    if category_id:
        events = events.filter(category_id=category_id)
    q = request.GET.get('q')
    if q:
        events = events.filter(
            _Q(title__icontains=q) | _Q(description__icontains=q) | _Q(location__icontains=q)
        )
    return Response({'events': [_event_dict(e, request) for e in events]})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_event_api(request):
    """Create a new event"""
    title = request.data.get('title')
    description = request.data.get('description')
    start_time = _dt(request.data.get('start_time'))
    end_time = _dt(request.data.get('end_time'))
    is_virtual = _bool(request.data.get('is_virtual'), True)
    virtual_link = request.data.get('virtual_link') or None
    location = request.data.get('location') or None
    category_id = request.data.get('category') or None
    event_image = request.FILES.get('event_image')

    if not (title and description and start_time and end_time):
        return Response({'error': 'Title, description, start_time, and end_time are required.'},
                        status=status.HTTP_400_BAD_REQUEST)
    if end_time <= start_time:
        return Response({'error': 'The event must end after it starts.'},
                        status=status.HTTP_400_BAD_REQUEST)
    category = None
    if category_id:
        category = Groupcategory.objects.filter(id=category_id).first()
        if category is None:
            return Response({'error': 'Invalid category.'}, status=status.HTTP_400_BAD_REQUEST)

    slug = slugify(title) + '-' + str(uuid.uuid4())[:6]

    event = Event.objects.create(
        title=title,
        description=description,
        creator=request.user,
        start_time=start_time,
        end_time=end_time,
        is_virtual=is_virtual,
        virtual_link=virtual_link if is_virtual else None,
        location=location if not is_virtual else (location or None),
        category=category,
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
    return Response(_event_dict(event, request, detail=True))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_event_api(request, slug):
    """Join an event"""
    event = get_object_or_404(Event, slug=slug)
    event.attendees.add(request.user)
    return Response({'message': 'You have joined the event.',
                     'is_attending': True,
                     'attendee_count': event.attendees.count()})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def leave_event_api(request, slug):
    """Leave an event"""
    event = get_object_or_404(Event, slug=slug)
    event.attendees.remove(request.user)
    return Response({'message': 'You have left the event.',
                     'is_attending': False,
                     'attendee_count': event.attendees.count()})


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def edit_event_api(request, slug):
    """Edit an event"""
    event = get_object_or_404(Event, slug=slug)
    if event.creator != request.user:
        return Response({'error': 'Only the creator can edit this event.'},
                        status=status.HTTP_403_FORBIDDEN)

    for field in ['title', 'description']:
        if field in request.data and str(request.data[field]).strip():
            setattr(event, field, request.data[field])
    for field in ['start_time', 'end_time']:
        if field in request.data and request.data[field]:
            parsed = _dt(request.data[field])
            if parsed is None:
                return Response({'error': f'Invalid {field}.'}, status=status.HTTP_400_BAD_REQUEST)
            setattr(event, field, parsed)
    if event.end_time <= event.start_time:
        return Response({'error': 'The event must end after it starts.'},
                        status=status.HTTP_400_BAD_REQUEST)
    if 'is_virtual' in request.data:
        event.is_virtual = _bool(request.data['is_virtual'])
    if 'virtual_link' in request.data:
        event.virtual_link = request.data['virtual_link'] or None
    if 'location' in request.data:
        event.location = request.data['location'] or None
    if 'category' in request.data:
        cid = request.data['category']
        if cid:
            category = Groupcategory.objects.filter(id=cid).first()
            if category is None:
                return Response({'error': 'Invalid category.'}, status=status.HTTP_400_BAD_REQUEST)
            event.category = category
        else:
            event.category = None
    if 'event_image' in request.FILES:
        event.event_image = request.FILES['event_image']
    event.save()
    return Response({'message': 'Event updated successfully.',
                     'event': _event_dict(event, request, detail=True)})


def _ai_text(prompt, system=None):
    """One completion for the AI event endpoint.

    The website uses OpenAI (commu_prenair/views.py generate_ai_event); the
    previous API view used a Groq model that no longer exists. Try OpenAI
    first, then Groq. Kept as a module-level function so tests can stub it.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    last_error = None
    if getattr(settings, 'OPENAI_API_KEY', None):
        try:
            from openai import OpenAI
            resp = OpenAI(api_key=settings.OPENAI_API_KEY).chat.completions.create(
                model="gpt-3.5-turbo", messages=messages, max_tokens=500)
            return resp.choices[0].message.content
        except Exception as e:  # noqa: BLE001
            last_error = e
    if getattr(settings, 'GROQ_API_KEY', None):
        try:
            from groq import Groq
            resp = Groq(api_key=settings.GROQ_API_KEY).chat.completions.create(
                messages=messages, model="llama-3.1-8b-instant")
            return resp.choices[0].message.content
        except Exception as e:  # noqa: BLE001
            last_error = e
    raise RuntimeError(str(last_error) if last_error else 'No AI provider is configured.')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def generate_ai_event_api(request):
    """Create (or draft) an event from an idea, using AI.

    Two shapes, because two clients use it:

    * website / tablet dialog (multipart): `idea`, `start_time`, `end_time`,
      `is_virtual` ('true'/'false'), `virtual_link`, `location`, `category`,
      `event_image` -- the AI writes the title + description and the event is
      CREATED, exactly like the website's generate_ai_event view. Responds
      `{"success": true, "slug": ...}`.
    * phone "Draft it" (JSON): `prompt` only -- nothing is created; the
      generated fields come back as JSON for the create-event form.
    """
    idea = request.data.get('idea')
    if not idea and request.data.get('prompt') and 'event_image' not in request.FILES \
            and not request.data.get('start_time'):
        return _ai_event_draft(request)
    if not idea:
        return Response({'success': False, 'error': 'Describe your event idea.'},
                        status=status.HTTP_400_BAD_REQUEST)

    start_time = _dt(request.data.get('start_time'))
    end_time = _dt(request.data.get('end_time'))
    if not (start_time and end_time):
        return Response({'success': False, 'error': 'Start and end time are required.'},
                        status=status.HTTP_400_BAD_REQUEST)
    if end_time <= start_time:
        return Response({'success': False, 'error': 'The event must end after it starts.'},
                        status=status.HTTP_400_BAD_REQUEST)
    event_image = request.FILES.get('event_image')
    is_virtual = _bool(request.data.get('is_virtual'))
    virtual_link = request.data.get('virtual_link') or ''
    location = request.data.get('location') or ''
    category_id = request.data.get('category') or None
    category = None
    if category_id:
        category = Groupcategory.objects.filter(id=category_id).first()
        if category is None:
            return Response({'success': False, 'error': 'Invalid category.'},
                            status=status.HTTP_400_BAD_REQUEST)

    prompt = (
        "Create a compelling event title and professional description based on:\n"
        f"Idea: {idea}\nStart: {request.data.get('start_time')}\nEnd: {request.data.get('end_time')}\n"
        f"Type: {'Virtual' if is_virtual else 'Physical'}\n"
        "Format the title as the first line and description as markdown text following it. "
        "Do not include any **** in title"
    )
    try:
        content = _ai_text(prompt) or ''
    except Exception as e:  # noqa: BLE001
        return Response({'success': False, 'error': f'AI service unavailable: {e}'},
                        status=status.HTTP_502_BAD_GATEWAY)
    lines = [ln for ln in content.strip().split('\n')]
    title = (lines[0] if lines else '').replace('#', '').replace('*', '').strip()[:200]
    description = '\n'.join(lines[1:]).strip()
    if not title:
        title = str(idea).strip()[:80]
    if not description:
        description = str(idea).strip()

    event = Event.objects.create(
        title=title,
        description=description,
        creator=request.user,
        start_time=start_time,
        end_time=end_time,
        is_virtual=is_virtual,
        virtual_link=virtual_link if is_virtual else None,
        location=location if not is_virtual else None,
        event_image=event_image,
        category=category,
        slug=slugify(title) + '-' + str(uuid.uuid4())[:6],
    )
    event.attendees.add(request.user)
    return Response({'success': True, 'slug': event.slug, 'title': event.title,
                     'message': 'Event created successfully.'},
                    status=status.HTTP_201_CREATED)


def _ai_event_draft(request):
    prompt = request.data.get('prompt', '')
    system = ("You are an event planning assistant. Reply with ONLY a JSON object with keys: "
              "title, description, start_time (ISO format), end_time (ISO format), "
              "location, is_virtual (bool).")
    try:
        text = _ai_text(prompt, system=system) or ''
    except Exception as e:  # noqa: BLE001
        return Response({'error': f'AI service unavailable: {e}'}, status=status.HTTP_502_BAD_GATEWAY)
    # Models often wrap the JSON in prose or a code fence.
    start, end = text.find('{'), text.rfind('}')
    try:
        result = json.loads(text[start:end + 1])
    except Exception:  # noqa: BLE001
        lines = text.strip().split('\n')
        result = {'title': lines[0].replace('#', '').replace('*', '').strip(),
                  'description': '\n'.join(lines[1:]).strip()}
    return Response(result)


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
    """AI video generation (website `dashboard.views.generate_video`).

    Body: `prompt` (required), `duration` (5/10/15), `style`, `seed`, `width`,
    `height`. It runs the website view itself (same provider, same polling),
    so the call blocks until the video is ready - up to five minutes - and
    answers `{video_url, duration}` or `{error}`.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import json as _json
        from django.test import RequestFactory
        from dashboard import views as _dash_views

        prompt = (request.data.get('prompt') or '').strip()
        if not prompt:
            return Response({'error': 'Please enter a video description'},
                            status=status.HTTP_400_BAD_REQUEST)
        if len(prompt) > 4000:
            return Response({'error': 'The description is limited to 4000 characters.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            payload = {
                'prompt': prompt,
                'duration': int(request.data.get('duration', 5)),
                'width': int(request.data.get('width', 1344)),
                'height': int(request.data.get('height', 768)),
                'style': request.data.get('style', 'cinematic') or 'cinematic',
                'seed': int(request.data.get('seed', 0) or 0),
            }
        except (TypeError, ValueError):
            return Response({'error': 'duration, width, height and seed must be numbers.'},
                            status=status.HTTP_400_BAD_REQUEST)

        inner = RequestFactory().post('/dashboard/generate-video/', data=payload)
        inner.user = request.user
        resp = _dash_views.generate_video(inner)
        try:
            body = _json.loads(resp.content)
        except ValueError:
            body = {'error': 'Unexpected response from the video service.'}
        return Response(body, status=resp.status_code)


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

def _work_ai_client():
    """The OpenAI client the website's work views use (gpt-3.5-turbo); the
    Groq `llama3-8b-8192` model these two endpoints first shipped with has been
    retired, which made both return 500."""
    from . import work_prenair_views as _wv
    return _wv.client


def _loads_ai_json(text):
    import re as _re
    text = (text or '').strip()
    if text.startswith('```'):
        text = _re.sub(r'^```(?:json)?', '', text).rstrip('`').strip()
    return json.loads(text)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def suggest_gig_pricing_api(request, slug):
    """AI pricing tips for one of the caller's gigs (website suggest_gig_pricing).

    Returns the website's keys (`basic_suggestion`, `standard_suggestion`,
    `premium_suggestion`, `bundles`, `explanations`) and, for older clients,
    the same payload again under `suggestions`.
    """
    gig = get_object_or_404(Gig, slug=slug)
    if gig.user != request.user:
        return Response({'error': 'Unauthorized access'}, status=status.HTTP_403_FORBIDDEN)
    try:
        related = Gig.objects.filter(
            Q(category_level_1=gig.category_level_1) |
            Q(category_level_2=gig.category_level_2) |
            Q(category_level_3=gig.category_level_3)
        ).exclude(id=gig.id)

        def _market(field):
            vals = [getattr(g, field) for g in related if getattr(g, field)]
            return {
                'avg': float(sum(vals) / len(vals)) if vals else 0,
                'min': float(min(vals)) if vals else 0,
                'max': float(max(vals)) if vals else 0,
            }
        m = {k: _market(f'{k}_price') for k in ('basic', 'standard', 'premium')}
        prompt = f"""
        Act as a professional pricing strategist for freelancers. Analyze this gig's pricing and suggest optimizations:

        Current Pricing:
        - Basic: ${gig.basic_price} (Delivery: {gig.basic_delivery_time} days)
        - Standard: ${gig.standard_price} (Delivery: {gig.standard_delivery_time} days)
        - Premium: ${gig.premium_price} (Delivery: {gig.premium_delivery_time} days)

        Market Data from similar gigs:
        - Basic Package: Average ${m['basic']['avg']:.2f}, Range ${m['basic']['min']}-${m['basic']['max']}
        - Standard Package: Average ${m['standard']['avg']:.2f}, Range ${m['standard']['min']}-${m['standard']['max']}
        - Premium Package: Average ${m['premium']['avg']:.2f}, Range ${m['premium']['min']}-${m['premium']['max']}

        Provide:
        1. Specific price suggestions for each package (formatted as numbers only)
        2. 3 service bundle ideas with pricing
        3. Brief explanations for each suggestion

        Return JSON format with keys:
        'basic_suggestion', 'standard_suggestion', 'premium_suggestion',
        'bundles', 'explanations'
        """
        response = _work_ai_client().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000,
        )
        result = _loads_ai_json(response.choices[0].message.content)
        payload = dict(result)
        payload['suggestions'] = result
        return Response(payload)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_proposal_description_api(request):
    """AI proposal text for a custom offer (website generate_proposal_description).

    Body: { prompt, gig_slug }. Freelancers only, and only for their own gig,
    as on the website. `gig_title` (the first app build's key) is still
    accepted when no gig_slug is sent.
    """
    prompt = request.data.get('prompt', '')
    gig_slug = request.data.get('gig_slug', '')
    gig_title = request.data.get('gig_title', '')
    if not prompt or not (gig_slug or gig_title):
        return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
    if not request.user.is_work_freelancer:
        return Response({'error': 'You are not authorized to perform this action.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        if gig_slug:
            gig = get_object_or_404(Gig, slug=gig_slug)
            if gig.user != request.user:
                return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            service = f"""Service Being Offered: {gig.title}
        Service Description: {gig.description}
        Service Category: {gig.category_level_1}, {gig.category_level_2}, {gig.category_level_3}"""
        else:
            service = f"Service Being Offered: {gig_title}"
        ai_prompt = f"""
        Act as a professional freelance proposal writer. Generate a compelling project proposal description based on:

        Client's Requirements: {prompt}
        {service}

        Guidelines:
        - Keep it professional yet friendly
        - Highlight key benefits for the client
        - Mention relevant experience
        - 300-500 characters
        - Use bullet points if needed
        - Focus on client outcomes

        Return ONLY the proposal text without any formatting or markdown.
        """
        response = _work_ai_client().chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": ai_prompt}],
            temperature=0.7,
            max_tokens=500,
        )
        return Response({'description': response.choices[0].message.content.strip()})
    except Http404:
        raise
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
    """AI-generate a module with lessons.

    Web contract (module_lessons_eduprenair.html): ``{description,
    lesson_count}`` creates a Module (+ Lessons) on the course and answers
    ``{"success": true, ...}``. The older ``{module_title, count}`` form still
    returns just a lessons preview.
    """
    course = get_object_or_404(Course, slug=course_slug, instructor=request.user)
    description = request.data.get('description')
    if description:
        from django.db import transaction
        try:
            lesson_count = max(1, min(int(request.data.get('lesson_count', 1)), 4))
        except (TypeError, ValueError):
            lesson_count = 1
        try:
            from dashboard.views import client
            last = Module.objects.filter(course=course).order_by('-order').first()
            next_order = last.order + 1 if last else 1
            prompt = (
                "Create ONE course module with %d lessons from this course description:\n%s\n"
                "Return strictly JSON: {\"module_title\":str,\"module_description\":str,"
                "\"module_order\":%d,\"lessons\":[{\"title\":str,\"description\":str,\"order\":int}]}"
                % (lesson_count, description, next_order)
            )
            response = client.chat.completions.create(
                model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
            ai = json.loads(response.choices[0].message.content)
            with transaction.atomic():
                module = Module.objects.create(
                    course=course, title=ai['module_title'],
                    description=ai['module_description'], order=ai.get('module_order') or next_order)
                for ld in ai['lessons']:
                    Lesson.objects.create(
                        module=module, title=ld['title'],
                        description=ld.get('description', ''), order=ld['order'],
                        slug=f"{slugify(ld['title'])}-{module.id}-{ld['order']}_{str(uuid.uuid4().int)[:6]}",
                        video=None)
            return Response({'success': True, 'module_id': module.id})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
    """Add purchased items to a project (mirrors digi_prenair.views.add_to_project).

    Body: `item_ids` (OrderItem ids) and either `project_id` or `project_name`
    (+ optional `project_description`). `product_id` is also accepted and means
    "the caller's purchased line(s) of that product". The old version tried to
    create an OrderItem with no order, which violates NOT NULL and 500'd.
    """
    user = request.user
    item_ids = request.data.get('item_ids') or []
    product_id = request.data.get('product_id')
    project_id = request.data.get('project_id')
    project_name = (request.data.get('project_name') or '').strip()

    items = OrderItem.objects.filter(order__user=user, order__is_paid=True)
    if item_ids:
        items = items.filter(id__in=item_ids)
    elif product_id:
        items = items.filter(product_id=product_id)
    else:
        return Response({'success': False, 'message': 'Invalid request'},
                        status=status.HTTP_400_BAD_REQUEST)
    if not items.exists():
        return Response({'success': False,
                         'message': 'You have not purchased that item.'},
                        status=status.HTTP_400_BAD_REQUEST)

    if project_id:
        project = get_object_or_404(Project, id=project_id, user=user)
    elif project_name:
        project, _ = Project.objects.get_or_create(
            user=user, name=project_name,
            defaults={'description': request.data.get('project_description', '')},
        )
    else:
        return Response({'success': False, 'message': 'Invalid request'},
                        status=status.HTTP_400_BAD_REQUEST)

    project.order_items.add(*items)
    project.save()

    return Response({'success': True,
                     'message': f'Added to project "{project.name}".',
                     'project_id': project.id},
                    status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def digi_projects_api(request):
    """List user's projects"""
    projects = Project.objects.filter(user=request.user).order_by('-updated_at')
    data = [{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'created_at': p.created_at,
        'updated_at': p.updated_at,
        'items_count': p.order_items.count(),
        # Product thumbnails on the project card.
        'preview_images': [
            oi.product.image.url
            for oi in p.order_items.select_related('product')[:4]
            if oi.product.image
        ],
    } for p in projects]
    return Response({'projects': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def digi_project_detail_api(request, project_id):
    """Get project detail"""
    project = get_object_or_404(Project, id=project_id, user=request.user)
    items = OrderItemSerializer(project.order_items.all(), many=True).data
    # Add product details next to the serializer's ids (additive).
    by_id = {oi.id: oi for oi in project.order_items.select_related('product')}
    for row in items:
        oi = by_id.get(row['id'])
        if oi:
            row['product_title'] = oi.product.title
            row['product_slug'] = oi.product.slug
            row['product_image'] = oi.product.image.url if oi.product.image else None
            row['file_url'] = oi.product.downloadable_file.url if oi.product.downloadable_file else None
    return Response({
        'id': project.id,
        'name': project.name,
        'description': project.description,
        'created_at': project.created_at,
        'updated_at': project.updated_at,
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
        try:
            return FileResponse(product.downloadable_file.open(), as_attachment=True,
                                filename=product.downloadable_file.name.split('/')[-1])
        except (FileNotFoundError, OSError):
            # The row points at a file the storage no longer has.
            return Response({'error': 'The file for this product is missing. Please contact the seller.'},
                            status=status.HTTP_404_NOT_FOUND)
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

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def my_referrals_api(request):
    """My Referrals page (dashboard/my_referrals.html).

    GET -> referral code/link, stats (total / active / success rate) and the
    referred users. POST ``{referral_code}`` sets the code (the website's
    form: 3-20 letters/digits, unique). Old keys (``referral_code``,
    ``referral_count``, ``referrals``) are kept.
    """
    import re as _re
    from django.db import IntegrityError, transaction

    user = request.user
    if request.method == 'POST':
        code = str(request.data.get('referral_code') or '').strip()
        if not code:
            return Response({'error': 'Please enter a referral code.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not _re.match(r'^[A-Za-z0-9]+$', code):
            return Response({'error': 'Referral code can only contain letters and numbers.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if len(code) < 3 or len(code) > 20:
            return Response({'error': 'Referral code must be between 3 and 20 characters.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                user.referral_code = code
                user.save(update_fields=['referral_code'])
        except IntegrityError:
            user.refresh_from_db(fields=['referral_code'])
            return Response({'error': 'This referral code is already taken. Please choose another one.'},
                            status=status.HTTP_400_BAD_REQUEST)

    referrals = CustomUser.objects.filter(referred_by=user).order_by('-created_at')
    total = referrals.count()
    active = referrals.filter(has_listed_and_sold=True).count()
    rate = round((active / total) * 100, 1) if total else 0
    link = (f"https://fireprenair.com/?register=true&referral_code={user.referral_code}"
            if user.referral_code else None)
    data = []
    for u in referrals:
        pic = None
        try:
            pic = request.build_absolute_uri(u.profile_pic.url) if u.profile_pic else None
        except Exception:
            pic = None
        data.append({
            'id': u.id,
            'username': u.username,
            'name': u.name,
            'email': u.email,
            'profile_pic': pic,
            'created_at': u.created_at,
            'has_listed_and_sold': u.has_listed_and_sold,
        })
    body = {
        'referral_code': user.referral_code,
        'referral_link': link,
        'referral_count': total,
        'total_referrals': total,
        'active_referrals': active,
        'success_rate': rate,
        'referrals': data,
    }
    if request.method == 'POST':
        body['message'] = 'Your referral code has been set successfully!'
    return Response(body)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def personal_access_token_api(request):
    """Personal access token (dashboard/access_token.html).

    GET gets or creates the caller's token; POST ``{regenerate: true}`` (the
    website view's ``regenerate`` form field) deletes it and issues a new one.
    """
    from rest_framework.authtoken.models import Token
    if request.method == 'POST' and str(request.data.get('regenerate', '')).lower() in ('1', 'true', 'yes', 'on'):
        Token.objects.filter(user=request.user).delete()
        token = Token.objects.create(user=request.user)
        return Response({'token': token.key, 'created': True,
                         'message': 'Token regenerated successfully.'})
    token, created = Token.objects.get_or_create(user=request.user)
    return Response({'token': token.key, 'created': created})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_access_token_api(request):
    """Verify a personal access token.

    Only the caller's own token is confirmed (the previous version told any
    signed-in user who owned an arbitrary token key). Also accepts the
    website's ``Authorization: Token <key>`` form.
    """
    from rest_framework.authtoken.models import Token
    token_key = request.data.get('token', '')
    if not token_key:
        header = request.headers.get('Authorization', '')
        if header.startswith('Token '):
            token_key = header.split(' ', 1)[1]
    try:
        token = Token.objects.select_related('user').get(key=token_key)
    except Token.DoesNotExist:
        return Response({'valid': False, 'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
    if token.user_id != request.user.id:
        return Response({'valid': False, 'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
    return Response({'valid': True, 'status': 'valid', 'user_id': token.user_id,
                     'username': token.user.username, 'email': token.user.email})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_student_progress_api(request):
    """AI-analyze student progress.

    Web contract (dashboard_eduprenair.html "Analyze Progress"): body
    ``{course_slug, user_id}`` -> ``{"analysis": {risk_prediction,
    risk_percentage, strengths, improvements}}`` for the caller's own
    enrollment. When the caller instructs the course the old aggregate keys
    are returned as well.
    """
    course_slug = request.data.get('course_slug', '')
    course = get_object_or_404(Course, slug=course_slug)
    user_id = request.data.get('user_id')
    if user_id not in (None, '') and str(user_id) != str(request.user.id):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    data = {}
    if course.instructor_id == request.user.id:
        enrollments = StudentEnrollment.objects.filter(course=course)
        total_students = enrollments.count()
        avg_progress = sum(e.progress for e in enrollments) / total_students if total_students > 0 else 0
        completed = enrollments.filter(is_completed=True).count()
        data.update({
            'course': course.title,
            'total_students': total_students,
            'average_progress': round(avg_progress, 2),
            'completed_students': completed,
            'completion_rate': round((completed / total_students * 100) if total_students > 0 else 0, 2),
        })

    enrollment = StudentEnrollment.objects.filter(user=request.user, course=course).first()
    if enrollment is None and not data:
        return Response({'error': 'You are not enrolled in this course.'},
                        status=status.HTTP_404_NOT_FOUND)
    if enrollment is not None:
        progress = float(enrollment.progress or 0)
        days = max((timezone.now() - enrollment.enrolled_date).days, 0)
        risk = 0 if enrollment.is_completed else min(100, max(5, int(100 - progress + min(days, 30) / 2)))
        level = 'Low' if risk <= 33 else ('Medium' if risk <= 66 else 'High')
        strengths = []
        improvements = []
        if progress >= 50:
            strengths.append('Steady progress: %d%% of the course completed.' % progress)
        if enrollment.is_completed:
            strengths.append('Completed the course.')
        strengths.append('Enrolled %d day(s) ago and still engaged.' % days)
        if progress < 100:
            improvements.append('Finish the remaining lessons to reach 100%.')
        improvements.append('Set aside a fixed study slot each week.')
        improvements.append('Revisit completed lessons before the quiz.')
        data['analysis'] = {
            'risk_prediction': '%s dropout risk (%d%%)' % (level, risk),
            'risk_percentage': risk,
            'strengths': strengths[:3],
            'improvements': improvements[:3],
        }
    return Response(data)


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
