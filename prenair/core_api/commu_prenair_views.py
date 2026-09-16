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
from django.http import Http404, JsonResponse
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

@method_decorator(csrf_exempt, name='dispatch')  # Exempt CSRF for this view
class CommuprenairChatbotView(APIView):
    def post(request):
        user_message = request.data.get('message', '').lower()
        
        # Predefined responses for quick replies
        predefined_responses = {
            "name": "I am your customer support assistant, here to help you with any questions about Workprenair.",
            "who_created_you": "I was created by the development team of Fireprenair.",
            "what_can_you_do": "I can help you navigate our platform, answer questions about our services, and provide consultation details.",
        }

        # Check if the user message matches any predefined responses
        for key, response in predefined_responses.items():
            if key in user_message:
                return Response({"message": response})

        # Interact with Groq API for other responses
        client = Groq(api_key=settings.GROQ_API_KEY)
        groq_response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": json.dumps({
                    "knowledge_base": knowledge_base,
                    "instruction": "Please generate short, clear, and professional responses. "
                                   "Limit unnecessary details, ensure the tone is formal, and provide concise answers. "
                                   "Avoid elaboration and keep responses to the point. "
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

        return Response({"message": bot_reply_html})

    # Optional: handle other HTTP methods (e.g., GET, PUT, etc.)
    def get(self, request, *args, **kwargs):
        return Response({"message": "Only POST requests are allowed."}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def commu_prenair_home_api(request):
    """
    Home endpoint returning posts and user contacts.
    """
    try:
        # Fetch the posts and user contacts
        posts = Post.objects.filter(is_group_post=False).order_by('-created_at')
        user_contacts = request.user.get_all_chats()

        # Serialize the data
        post_serializer = PostSerializer(posts, many=True)
        # user_contacts_serializer = UserDataSerializer(user_contacts, many=True)
        user_contacts_serializer = PrivateChatSerializer(user_contacts, many=True)

        # Return the data in a response
        return Response({
            'posts': post_serializer.data,
            'user_contacts': user_contacts_serializer.data
        })
    except Exception as e:
        print(e)
        return Response({"error":"Something went Wrong"},status=500)


class MakePostView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self,request):
        title = request.data.get('title')
        content = request.data.get('content')
        group_slug = request.data.get('group_slug')
        file = request.FILES.get('media')
        image = None
        video = None
        print('the group is ',group_slug)
        if file:
            if file.content_type.startswith('video/'):
                video = file
            elif file.content_type.startswith('image/'):
                image = file

        if title:
            unique_slug = slugify(title) + "-by-" + request.user.username + "-" + str(uuid.uuid4())[:6]
        else:
            unique_slug = request.user.username + "-" + str(uuid.uuid4())[:6]

        is_group_post = False
        group = None
        if group_slug:
            group = get_object_or_404(Group, slug=group_slug)
            is_group_post = True

        post = Post.objects.create(
            author=request.user,
            title=title if title else f"Untitled by {request.user.username}",
            content=content,
            image=image,
            video=video,
            slug=unique_slug,
            is_group_post=is_group_post,
        )

        if group:
            group.group_posts.add(post)

        response_data = {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'slug': post.slug,
            'is_group_post': post.is_group_post,
        }

        if group:
            response_data['redirect_url'] = f"/commuprenair/group/{group.slug}/"  # Replace with actual URL pattern for group detail
        else:
            response_data['redirect_url'] = '/commu_home_api/'  # Replace with actual URL for home

        return Response(response_data, status=status.HTTP_201_CREATED)



@api_view(['POST'])
@authenticated_user_required_commu_api
def make_group_post_api(request, slug):
    group = get_object_or_404(Group, slug=slug)

    # Posting is for members. `group_detail_api` already refuses to show a
    # private group to a non-member, but this endpoint let anyone signed in
    # post into any group — including a private one they had never joined,
    # which made the whole membership-request flow pointless.
    is_member = (
        group.admin_id == request.user.id
        or group.members.filter(id=request.user.id).exists()
    )
    if not is_member:
        return Response(
            {'error': 'You must join this group to post in it.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    content = request.data.get('content')
    image = request.FILES.get('image')
    video = request.FILES.get('video')

    # Basic validation
    if not content:
        return Response({"error": "Content is required."}, status=status.HTTP_400_BAD_REQUEST)

    post_slug = slugify(group.name) + "-by-" + request.user.username + "-" + str(uuid.uuid4())[:6]

    # Create post object
    post = Post.objects.create(
        author=request.user,
        content=content,
        image=image if image else None,
        video=video if video else None,
        slug=post_slug,
        is_group_post=True
    )

    # Associate post with the group
    group.group_posts.add(post)
    group.save()

    return Response({"message": "Post created successfully!", "post_slug": post.slug}, status=status.HTTP_201_CREATED)



@api_view(['GET'])
@authenticated_user_required_commu_api
def post_detail_api(request, slug):
    try:
        post = get_object_or_404(Post, slug=slug)
        post_data = PostSerializer(post).data
        return Response(post_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@authenticated_user_required_commu_api
def delete_post_api(request, slug):
    try:
        post = get_object_or_404(Post, slug=slug)
        
        if request.user != post.author:
            return Response({
                "error": "Your account has been noticed to be violating our terms of service."
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Handle file deletion
        if post.image:
            post.image.delete(save=False)
        if post.video:
            post.video.delete(save=False)
        post.delete()
        return Response({"message": "Post deleted successfully."}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authenticated_user_required_commu_api
def add_comment_api(request, post_slug):
    try:
        content = request.data.get('content')

        if not content:
            return Response({"error": "Comment   cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
        post = get_object_or_404(Post, slug=post_slug)
        comment = Comment.objects.create(post=post, author=request.user, content=content)

        if post.author != request.user:
            Notification.objects.create(
                user=post.author,
                message=f'{request.user.username} commented on your post',
                app_name='commuprenair'
            )
        print(post_slug)
        comment=CommentSerializer(comment).data
        return Response({'message': 'comment added','comment':comment},status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



@api_view(['POST'])
@authenticated_user_required_commu_api
def add_reply_api(request, comment_id):
    content = request.data.get("content", "").strip()

    if not content:
        return Response({"success": False, "error": "Reply cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        comment = get_object_or_404(Comment, id=comment_id)
        reply = ReplyComment.objects.create(
            comment=comment,
            author=request.user,
            content=content
        )
        
        # `author.profile.profile_pic` never resolved — CustomUser has no
        # `profile` relation, profile_pic sits on the user — so the avatar came
        # back null every time, and `username` was sent where the templates
        # show `name`. Returning the serialised reply keeps this identical to
        # what the post detail hands back for a comment.
        return Response({
            "success": True,
            "reply": ReplyCommentSerializer(reply).data,
        }, status=status.HTTP_201_CREATED)
    
    except Comment.DoesNotExist:
        return Response({"success": False, "error": "Comment not found."}, status=status.HTTP_404_NOT_FOUND)
    
@api_view(['POST'])
@authenticated_user_required_commu_api
def add_reply1_api(request, comment_id):
    content = request.data.get("content", "").strip()

    if not content:
        return Response({"success": False, "error": "Reply content cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
    
    comment = get_object_or_404(Comment, id=comment_id)
    reply = ReplyComment.objects.create(comment=comment, author=request.user, content=content)

    return Response({
        "success": True,
        "message": "Reply added successfully!",
        "redirect_url": f"/post/{comment.post.slug}/"
    }, status=status.HTTP_201_CREATED)
    
    
@api_view(['POST'])
@authenticated_user_required_commu_api
def toggle_like_api(request, slug):
    user = request.user
    post = get_object_or_404(Post, slug=slug)

    like, created = Like.objects.get_or_create(post=post, user=user)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
        if user != post.author:
            Notification.objects.create(
                user=post.author,
                message=f'{user.username} liked your post',
                app_name='commuprenair'
            )
    
    liked_users = [
        {
            "name": like.user.username,
            "slug": getattr(like.user, "slug", ""),  # Handle if 'slug' isn't present
            "profile_pic": like.user.profile_pic.url if like.user.profile_pic else ""
        }
        for like in post.likes.all()
    ]

    return Response({
        'liked': liked,
        'liked_users': liked_users,
        'like_count': post.likes.count()
    }, status=status.HTTP_200_OK)
    
    
@api_view(['GET'])
@authenticated_user_required_commu_api
def get_likes_api(request, slug):
    post = get_object_or_404(Post, slug=slug)
    
    liked_users = [
        {
            'name': like.user.username,
            'slug': getattr(like.user, 'slug', ''),
            'profile_pic': like.user.profile_pic.url if like.user.profile_pic else ''
        }
        for like in post.likes.all()
    ]

    return Response({'liked_users': liked_users}, status=status.HTTP_200_OK)

def _get_user_by_slug(slug):
    """Resolve a user from a URL segment that may be a slug or a username.

    The commu endpoints all matched `slug=slug` exactly. A user whose username
    differs from their slug only in case -- `Test4` against `test4`, which is
    what slugify produces -- therefore 404'd on their own profile, because the
    clients hold the username and send that.
    """
    user = User.objects.filter(slug=slug).first()
    if user is None:
        user = User.objects.filter(slug__iexact=slug).first()
    if user is None:
        user = User.objects.filter(username__iexact=slug).first()
    if user is None:
        raise Http404(f'No user matching "{slug}".')
    return user

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_api(request, slug):
    user = _get_user_by_slug(slug)
    posts = Post.objects.filter(author=user, is_group_post=False).order_by('-created_at')
    
    user_data = UserSerializer(user).data
    posts_data = PostSerializer(posts, many=True).data

    # The website's profile header shows "<n> Followers" above a stack of the
    # first three connection avatars (see partials/profile_topbar.html). Only
    # the connections *list* endpoint carried this, so the app had to make a
    # second request just to draw the header.
    # A method, not a property — the template calls it implicitly, Python does not.
    connections = user.user_connections()
    return Response({
        'user': user_data,
        'posts': posts_data,
        'followers_count': connections.count(),
        'followers': [
            {
                'username': person.username,
                'slug': person.slug,
                'name': person.name,
                'profile_pic': person.profile_pic.url if person.profile_pic else None,
            }
            for person in connections[:3]
        ],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_about_api(request, slug):
    user = _get_user_by_slug(slug)
    user_data = UserSerializer(user).data
    
    return Response({'user': user_data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_groups_api(request, slug):
    user = _get_user_by_slug(slug)
    groups = Group.objects.filter(members=user)
    
    user_data = UserSerializer(user).data
    groups_data = GroupSerializer(groups, many=True).data
    
    return Response({
        'user': user_data,
        'groups': groups_data
    })
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def group_detail_api(request, slug):
    group = get_object_or_404(Group, slug=slug)
    
    if not group.is_member(request.user):
        return Response({'error': 'You Must Join this Group to view it'}, status=403)
    
    friends_in_group = group.friends_who_joined(request.user)
    friends_count = friends_in_group.count()
    posts = group.group_posts.all().order_by('-created_at')
    
    group_data = GroupSerializer(group).data
    posts_data = PostSerializer(posts, many=True).data
    friends_data = UserSerializer(friends_in_group, many=True).data
    
    # The app has to decide which header actions to draw — Leave vs Join vs
    # "Requested", and whether to offer Manage Group — and none of that was
    # derivable from the payload before.
    is_admin = group.admin_id == request.user.id

    return Response({
        'group': group_data,
        'posts': posts_data,
        'friends_count': friends_count,
        'friends_in_group': friends_data,
        'is_admin': is_admin,
        'is_member': group.is_member(request.user),
        'is_pending': group.is_pending(request.user),
        'member_count': group.members.count(),
        # Only the admin can act on these, so only the admin is told.
        'pending_requests_count':
            group.group_membership_requests.count() if is_admin else 0,
    })
    
    
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manage_group_api(request, slug):
    group = get_object_or_404(Group, slug=slug)

    # Membership requests are the group admin's to decide. Without this any
    # signed-in user could read another group's pending requests and approve
    # or decline them — `decline_all` from a non-admin was accepted.
    if group.admin_id != request.user.id:
        return Response(
            {'error': 'Only the group admin can manage this group.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    member_requests = GroupMemberShipRequests.objects.filter(group=group)
    
    query = request.GET.get('query')
    if query:
        member_requests = member_requests.filter(
            Q(user__username__icontains=query) | Q(user__email__icontains=query)
        )
    
    if request.method == 'POST':
        action = request.data.get('action')
        member_id = request.data.get('member_id')
        
        if action == 'approve_all':
            for member_request in member_requests:
                group.members.add(member_request.user)
                member_request.delete()
            return Response({'message': 'All member requests approved and users added to the group.'})
        
        if action == 'decline_all':
            member_requests.delete()
            return Response({'message': 'All member requests declined.'})
        
        if action == 'approve' and member_id:
            member_request = get_object_or_404(GroupMemberShipRequests, id=member_id, group=group)
            group.members.add(member_request.user)
            member_request.delete()
            return Response({'message': f'{member_request.user} approved and added to the group.'})
        
        if action == 'decline' and member_id:
            member_request = get_object_or_404(GroupMemberShipRequests, id=member_id, group=group)
            member_request.delete()
            return Response({'message': f'{member_request.user} declined.'})
    
    return Response({
        'group': GroupSerializer(group).data,
        'member_requests': GroupMemberShipRequestsSerializer(member_requests, many=True).data,
        'query': query
    })


@api_view(['GET'])
def get_child_categories_api(request):
    parent_id = request.GET.get("parent_id")
    categories = Groupcategory.objects.filter(parent_id=parent_id) if parent_id else Groupcategory.objects.none()
    category_data = [{"id": cat.id, "name": cat.name} for cat in categories]
    return Response({"categories": category_data})
@api_view(['GET'])
def get_group_categories_api(request):
    categories = Groupcategory.objects.all()
    category_data = [{"id": cat.id, "name": cat.name} for cat in categories]
    return Response({"categories": category_data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createe_group_api(request):
    name = request.data.get('name')
    desc = request.data.get('desc')
    is_private = request.data.get('is_private', 'False')
    # DRF puts uploaded files in request.FILES, not request.data
    profile_img = request.FILES.get('profile_img') or request.data.get('profile_img')
    cover_img = request.FILES.get('cover_img') or request.data.get('cover_img')
    category_l_1 = request.data.get('category_l_1')
    category_l_2 = request.data.get('category_l_2')
    category_l_3 = request.data.get('category_l_3')

    print(f'Create Group: name={name}, desc={desc}, private={is_private}, l1={category_l_1}, l2={category_l_2}, l3={category_l_3}')
    print(f'  profile_img={profile_img}, cover_img={cover_img}')

    if not name or not desc:
        return Response({'error': 'Name and description are required.'}, status=400)
    if not category_l_1:
        return Response({'error': 'Category L1 is required.'}, status=400)

    try:
        # Validate categories exist
        cat_l1 = Groupcategory.objects.get(id=category_l_1)
        cat_l2 = Groupcategory.objects.get(id=category_l_2) if category_l_2 else cat_l1
        cat_l3 = Groupcategory.objects.get(id=category_l_3) if category_l_3 else cat_l2
    except Groupcategory.DoesNotExist:
        return Response({'error': 'Invalid category ID.'}, status=400)

    try:
        # Handle is_private properly - DRF sends form data as strings
        if isinstance(is_private, str):
            is_private_bool = is_private.lower() in ('true', '1', 'yes')
        else:
            is_private_bool = bool(is_private)

        print(f'  Creating group: name={name}, private={is_private_bool}, img={profile_img}, cover={cover_img}')

        group = Group.objects.create(
            name=name,
            desc=desc,
            admin=request.user,
            is_private=is_private_bool,
            profile_img=profile_img,
            bg_img=cover_img,
            slug=slugify(name) + "-" + str(uuid.uuid4())[:6],
            category_l_1=cat_l1,
            category_l_2=cat_l2,
            category_l_3=cat_l3,
        )
        group.members.add(request.user)
        group.save()
        print(f'  Group created successfully: {group.slug}')
        return Response({'message': 'Group created successfully.', 'group': GroupSerializer(group).data})
    except Exception as e:
        print(f'  ERROR creating group: {e}')
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=400)


@api_view(['GET'])
def group_list_api(request):
    category_id = request.GET.get('category')
    query = request.GET.get('q')
    groups = Group.objects.all()

    if category_id:
        groups = groups.filter(
            Q(category_l_1_id=category_id) | Q(category_l_2_id=category_id) | Q(category_l_3_id=category_id)
        )

    if query:
        groups = groups.filter(
            Q(name__icontains=query) | Q(desc__icontains=query)
        )
        
    return Response({'groups': GroupSerializer(groups, many=True).data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_group_api(request, slug):
    group = get_object_or_404(Group, slug=slug)
    if not group.is_private:
        group.members.add(request.user)
        return Response({'message': 'You have joined the group successfully!'})
    
    GroupMemberShipRequests.objects.create(group=group, user=request.user)
    return Response({'message': 'Your request has been sent to the group admin.'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def leave_group_api(request, slug):
    group = get_object_or_404(Group, slug=slug)
    group.members.remove(request.user)
    if group.admin == request.user:
        group.admin = group.members.first()
        group.save()
    return Response({'message': 'You have left the group successfully.'})

# ----------------------------------       Connections         ---------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_connections_api(request, slug):
    user = _get_user_by_slug(slug)
    query = request.GET.get('q', '')
    
    connections_sent = User.objects.filter(connections_sent__to_user=user)
    connections_received = User.objects.filter(connections_received__from_user=user)
    
    if query:
        connections_sent = connections_sent.filter(Q(name__icontains=query) | Q(username__icontains=query))
        connections_received = connections_received.filter(Q(name__icontains=query) | Q(username__icontains=query))
    
    connections = connections_sent.union(connections_received)
    serializer = UserSerializer(connections, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def connection_requests_api(request):
    friend_requests = FriendRequest.objects.filter(to_user=request.user)
    serializer = FriendRequestSerializer(friend_requests, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_friend_request_api(request, slug):
    try:
        to_user = _get_user_by_slug(slug)
        
        if FriendRequest.objects.filter(from_user=request.user, to_user=to_user).exists():
            return Response({'message': 'Friend request already sent.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if request.user == to_user:
            return Response({'message': 'You cannot send a friend request to yourself.'}, status=status.HTTP_400_BAD_REQUEST)
        FriendRequest.objects.create(from_user=request.user, to_user=to_user)
        if to_user != request.user:
            Notification.objects.create(user=to_user, message=f'{request.user.username} sent you a friend request', app_name='commuprenair')
        
        return Response({'message': 'Friend request sent successfully.'}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def withdraw_friend_request_api(request, slug):
    to_user = _get_user_by_slug(slug)
    friend_request = FriendRequest.objects.filter(from_user=request.user, to_user=to_user).first()
    
    if not friend_request:
        return Response({'message': 'No friend request found.'}, status=status.HTTP_404_NOT_FOUND)
    
    friend_request.delete()
    return Response({'message': 'Friend request withdrawn successfully.'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def handle_friend_request_api(request, slug, action):
    tto_user = _get_user_by_slug(slug)
    friend_request = FriendRequest.objects.filter(from_user=tto_user, to_user=request.user).first()
    
    if not friend_request:
        return Response({'message': 'No friend request found.'}, status=status.HTTP_404_NOT_FOUND)
    
    if action == 'accept':
        Connection.objects.create(from_user=friend_request.from_user, to_user=friend_request.to_user)
        Connection.objects.create(from_user=friend_request.to_user, to_user=friend_request.from_user)
        Notification.objects.create(user=friend_request.from_user, message=f'{request.user.username} accepted your friend request', app_name='commuprenair')
        friend_request.delete()
        return Response({'message': 'Friend request accepted.'}, status=status.HTTP_200_OK)
    elif action == 'reject':
        friend_request.delete()
        return Response({'message': 'Friend request rejected.'}, status=status.HTTP_200_OK)
    return Response({'message': 'Invalid action.'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_connection_api(request, slug):
    other_user = _get_user_by_slug(slug)
    
    Connection.objects.filter(from_user=request.user, to_user=other_user).delete()
    Connection.objects.filter(from_user=other_user, to_user=request.user).delete()
    
    return Response({'message': f'You have unfollowed {other_user.name}.'}, status=status.HTTP_200_OK)


from django.contrib.auth import get_user_model

User = get_user_model()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_people_api(request):
    try:
            
        query = request.GET.get('q', '')
        users = User.objects.exclude(slug=request.user.slug)
        
        if query:
            users = users.filter(Q(name__icontains=query) | Q(username__icontains=query))
        
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        print(e)
        return Response(e,status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def profile_settings_api(request):
    user = request.user
    user.name = request.data.get('name', user.name)
    user.commu_bio = request.data.get('bio', user.commu_bio)
    
    if 'profile_pic' in request.FILES:
        user.profile_pic = request.FILES['profile_pic']
    
    user.save()
    return Response({'message': 'Profile updated successfully.'}, status=status.HTTP_200_OK)


############################################################################

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_messages_api(request):
    try:
        # When ?user_slug= is present, find/create a private chat with that user
        # instead of listing all chats. This handles the case where Flutter opens
        # a chat from a profile with no existing chat slug.
        user_slug = request.GET.get('user_slug')
        if user_slug:
            other_user = _get_user_by_slug(user_slug)
            chat = PrivateChat.objects.filter(
                (Q(user1=request.user, commu_prenair_chat=True) & Q(user2=other_user, commu_prenair_chat=True)) |
                (Q(user1=other_user, commu_prenair_chat=True) & Q(user2=request.user, commu_prenair_chat=True))
            ).first()
            if not chat:
                unique_uuid = uuid.uuid4()
                chat_slug = slugify(f"{request.user.username}-{other_user.username}-{unique_uuid}")
                chat = PrivateChat.objects.create(user1=request.user, user2=other_user, slug=chat_slug)
                Notification.objects.create(
                    user=other_user,
                    message=f'{request.user.username} has started a chat with you on Commuprenair',
                    app_name='commuprenair'
                )
            return Response({"chat_slug": chat.slug}, status=status.HTTP_201_CREATED)

        user_chats = request.user.get_all_chats()
        
        chats_with_last_message = []
        for user_chat in user_chats:
            last_message = user_chat.chat_messages.order_by('-timestamp').first()
            unread_count = user_chat.chat_messages.filter(is_read=False, receiver=request.user).count()
            
            chat_data = {
                "chat": PrivateChatSerializer(user_chat).data,
                "last_message": MessageSerializer(last_message).data if last_message else None,
                "unread_count": unread_count
            }
            chats_with_last_message.append(chat_data)

        return Response(chats_with_last_message, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def private_chat_api(request, slug):
    try:
        chat = PrivateChat.objects.filter(slug=slug).first()
        
        if not chat:
            other_user_slug = request.GET.get('user_slug')
            if not other_user_slug:
                return Response({"error": "User slug is required"}, status=status.HTTP_400_BAD_REQUEST)

            other_user = _get_user_by_slug(other_user_slug)
            
            chat = PrivateChat.objects.filter(
                (Q(user1=request.user, commu_prenair_chat=True) & Q(user2=other_user, commu_prenair_chat=True)) |
                (Q(user1=other_user, commu_prenair_chat=True) & Q(user2=request.user, commu_prenair_chat=True))
            ).first()
            
            if not chat:
                unique_uuid = uuid.uuid4()
                chat_slug = slugify(f"{request.user.username}-{other_user.username}-{unique_uuid}")
                chat = PrivateChat.objects.create(user1=request.user, user2=other_user, slug=chat_slug)

                Notification.objects.create(
                    user=other_user,
                    message=f'{request.user.username} has started a chat with you on Commuprenair',
                    app_name='commuprenair'
                )

            return Response({"chat_slug": chat.slug}, status=status.HTTP_201_CREATED)

        # Mark messages as read
        chat.chat_messages.filter(is_read=False, receiver=request.user).update(is_read=True)

        chat_messages = chat.chat_messages.all().order_by('timestamp')
        serialized_messages = MessageSerializer(chat_messages, many=True).data

        chat_with = chat.user1 if request.user != chat.user1 else chat.user2
        user=User.objects.get(id=chat_with.id)
        userserializer=UserSerializer(user)
        response_data = {
            # "chat_with": {"id": chat_with.id, "username": chat_with.username, "slug": chat_with.slug},
            "chat_with": userserializer.data,
            "chat_messages": serialized_messages,
            "chat_slug": chat.slug
        }
        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_subcategories_api(request, category_id):
    """
    Fetch subcategories for a given category.
    """
    level_2_categories = Groupcategory.objects.filter(parent_id=category_id)

    data = [
        {
            "id": category.id,
            "name": category.name,
            "children": [
                {"id": child.id, "name": child.name, "url": "#"} for child in category.group_categories.all()
            ],
        }
        for category in level_2_categories
    ]

    return Response({"level_2_categories": data})


@api_view(['POST']) 
@permission_classes([IsAuthenticated])
def mark_all_messages_notifications_as_read_api(request):
    """
    Marks all message notifications as read for the authenticated user.
    """
    notifications = request.user.notifications.filter(app_name='commuprenair', is_message=True, is_read=False)
    
    if notifications.exists():
        notifications.update(is_read=True)
        return Response({"message": "All message notifications marked as read."}, status=status.HTTP_200_OK)
    
    return Response({"message": "No unread message notifications found."}, status=status.HTTP_200_OK)
