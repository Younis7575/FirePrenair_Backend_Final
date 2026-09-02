from django.shortcuts import render, redirect
from .models import *
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.text import slugify
import uuid
from django.shortcuts import get_object_or_404
import json
from django.contrib import messages
from edu_prenair.decorators import authenticated_user_required_commu
from django.conf import settings
from django.contrib.auth.decorators import login_required
from profiles.models import Notification
from django.views.decorators.http import require_POST
from openai import OpenAI
# ai 
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.safestring import mark_safe
import markdown
from groq import Groq
client = OpenAI(api_key=settings.OPENAI_API_KEY)

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
def commuprenair_chatbot_view(request):
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



@authenticated_user_required_commu
def home(request): 
    posts = Post.objects.filter(is_group_post=False).order_by('-created_at')
    user_contacts = request.user.get_all_chats()
    
    context = {
        'posts': posts,
        'user_contacts': user_contacts
    }
    return render(request, 'commu_prenair/home.html', context)

@authenticated_user_required_commu
def make_post(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        file = request.FILES.get('media')
        group_slug = request.POST.get('group_slug', '').strip()
        
        image = None
        video = None
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

        if group:
            return redirect('group_detail', slug=group_slug)
        else:
            return redirect('commu_home')
    return render(request, 'commu_prenair/home.html')


@authenticated_user_required_commu
def make_group_post(request, slug):
    group = get_object_or_404(Group, slug=slug)
    
    if request.method == 'POST':
        content = request.POST.get('content')
        image = request.FILES.get('image')
        video = request.FILES.get('video')
        
        post_slug = slugify(group.name) + "-by-" + request.user.username + "-" + str(uuid.uuid4())[:6]

        post = Post.objects.create(
            author=request.user,
            content=content,
            image=image if image else None,
            video=video if video else None,
            slug=post_slug,
            is_group_post=True
        )

        # Add the post to the group
        group.group_posts.add(post)
        group.save()
        messages.success(request, "Post created successfully!")

        return redirect('group_detail', slug=group.slug)
    
    return render(request, 'commu_prenair/group_post_form.html', {'group': group})


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug)
    comments = post.comments.all()
    context = {
        'post': post,
        'comments': comments
    }
    return render(request, 'commu_prenair/post_detail.html', context)

import os

@login_required
def delete_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    if request.user == post.author:
    
        if post.image or post.video:
            if post.image:
                file_path = post.image.path
            elif post.video:
                file_path = post.video.path
            if settings.USE_S3_STORAGE:
                post.video.delete(save=False) if post.video else post.image.delete(save=False)
            elif os.path.exists(file_path):
                os.remove(file_path)
        post.delete()
        messages.success(request, "Post deleted successfully.")
    else:
        messages.error(request, "Your account has been noticed to be violating our terms of service.")
    return redirect('commu_home')


@login_required
def add_comment(request, post_slug):
    if request.method == "POST" and request.user.is_authenticated:
        content = request.POST.get('content', '').strip()

        if not content:
            messages.error(request, "Comment content cannot be empty.")
            return redirect('post_detail', slug=post_slug) 

        post = get_object_or_404(Post, slug=post_slug)
        Comment.objects.create(post=post, author=request.user, content=content)

        messages.success(request, "Comment added successfully.")
        Notification.objects.create(user=post.author,message=f'{request.user.username} commented on your post', app_name='commuprenair')
        return redirect('post_detail', slug=post_slug)

    messages.error(request, "Invalid request.")
    return redirect('commu_home')
        



@authenticated_user_required_commu
@csrf_exempt
def add_reply(request, comment_id):
    if request.method == "POST":
        data = json.loads(request.body)
        content = data.get("content")

        if content:
            try:
                comment = Comment.objects.get(id=comment_id)
                reply = ReplyComment.objects.create(
                    comment=comment,
                    author=request.user,
                    content=content
                )

                return JsonResponse({
                    "success": True,
                    "author_name": reply.author.name,
                    "author_profile_pic": reply.author.profile_pic.url,
                    "content": reply.content,
                })
            except Comment.DoesNotExist:
                return JsonResponse({"success": False, "error": "Comment not found."})
        else:
            return JsonResponse({"success": False, "error": "Reply cannot be empty."})

    return JsonResponse({"success": False, "error": "Invalid request method."})


@authenticated_user_required_commu
@csrf_exempt
def add_reply1(request, comment_id):
    if request.method == "POST":
        content = request.POST.get("content")

        if content:
                comment = Comment.objects.get(id=comment_id)
                reply = ReplyComment.objects.create(comment=comment,author=request.user,content=content)
        messages.success(request, 'Reply Added Successfully!')
        return redirect('post_detail', slug=comment.post.slug)


@authenticated_user_required_commu
def toggle_like(request, slug):
    user = request.user
    post = Post.objects.get(slug=slug)
    like, created = Like.objects.get_or_create(post=post, user=user)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
        if user != post.author:
            Notification.objects.create(user=post.author,message=f'{user.username} liked your post', app_name='commuprenair')
    
    liked_users = [
        {
        "name": like.user.username,
        "slug": like.user.slug,
        "profile_pic": like.user.profile_pic.url
        
        }
        for like in post.likes.all()
    ]

    return JsonResponse({
        'liked': liked,
        'liked_users': liked_users,
        'like_count': post.likes.count()
    })


@login_required
def get_likes(request, slug):
    try:
        post = Post.objects.get(slug=slug)
        liked_users = [
            {
                'name': like.user.username,
                'slug': like.user.slug,
                'profile_pic': like.user.profile_pic.url
            }
            for like in post.likes.all()
        ]
        return JsonResponse({'liked_users': liked_users})
    except Post.DoesNotExist:
        return JsonResponse({'error': 'Post not found'}, status=404)
    

#________________________________ Events_______________________________________
@login_required
def event_list(request):
    category_id = request.GET.get('category')
    query = request.GET.get('q')
    events = Event.objects.all().order_by('-start_time')

    if category_id:
        events = events.filter(category__id=category_id)

    if query:
        events = events.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query) |
            Q(location__icontains=query)
        )
        
    context = {
        'events': events,
        'categories': Groupcategory.objects.filter(parent=None)
    }
    return render(request, 'commu_prenair/event_list.html', context)

@login_required
def event_detail(request, slug):
    event = get_object_or_404(Event, slug=slug)
    context = {'event': event}
    return render(request, 'commu_prenair/event_detail.html', context)


@login_required
def create_event(request):
    categories = Groupcategory.objects.filter(parent=None)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        is_virtual = request.POST.get('is_virtual', False)
        virtual_link = request.POST.get('virtual_link')
        location = request.POST.get('location')
        event_image = request.FILES.get('event_image')
        category = request.POST.get('category')

        if not all([title, description, start_time, end_time, event_image]):
            messages.warning(request, "Required fields: title, description, start/end time, and image")
            return redirect('create_event')

        try:
            event = Event.objects.create(
                title=title,
                description=description,
                creator=request.user,
                start_time=start_time,
                end_time=end_time,
                is_virtual=is_virtual == 'True',
                virtual_link=virtual_link if is_virtual else None,
                location=location if location else None,
                event_image=event_image,
                category=Groupcategory.objects.get(id=category) if category else None,
                slug=slugify(title) + "-" + str(uuid.uuid4())[:6]
            )
            messages.success(request, "Event created successfully!")
            return redirect('commu_events')
        except Exception as e:
            messages.error(request, f"Error creating event: {str(e)}")

    context = {'categories': categories}
    return render(request, 'commu_prenair/create_event.html', context)

@require_POST
@login_required
def generate_ai_event(request):
    try:
        # Get form data
        idea = request.POST.get('idea')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        is_virtual = request.POST.get('is_virtual', 'false') == 'true'
        virtual_link = request.POST.get('virtual_link', '')
        location = request.POST.get('location', '')
        event_image = request.FILES.get('event_image')
        category_id = request.POST.get('category')

        # Generate title and description using AI
        prompt = f"""Create a compelling event title and professional description based on:
        Idea: {idea}
        Start: {start_time}
        End: {end_time}
        Type: {'Virtual' if is_virtual else 'Physical'}
        Format the title as the first line and description as markdown text following it. Do not include any **** in title"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )

        content = response.choices[0].message.content
        title = content.split('\n')[0].replace('# ', '').strip()
        description = '\n'.join(content.split('\n')[1:]).strip()

        # Create the event
        event = Event(
            title=title,
            description=description,
            creator=request.user,
            start_time=start_time,
            end_time=end_time,
            is_virtual=is_virtual,
            virtual_link=virtual_link if is_virtual else None,
            location=location if not is_virtual else None,
            event_image=event_image,
            category=Groupcategory.objects.get(id=category_id) if category_id else None
        )
        
        if not event.slug:
            event.slug = slugify(event.title) + "-" + str(uuid.uuid4())[:6]
        event.save()

        return JsonResponse({'success': True, 'slug': event.slug})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def join_event(request, slug):
    event = get_object_or_404(Event, slug=slug)
    
    if request.user not in event.attendees.all():
        event.attendees.add(request.user)
        messages.success(request, "Successfully registered for the event!")
    else:
        messages.info(request, "You're already registered for this event")
    
    return redirect('event_detail', slug=slug)


@login_required
def leave_event(request, slug):
    event = get_object_or_404(Event, slug=slug)
    if request.user in event.attendees.all():
        event.attendees.remove(request.user)
        messages.success(request, "Successfully unregistered from the event!")
    else:
        messages.info(request, "You're not registered for this event")

    return redirect('event_detail', slug=slug)


@login_required
def edit_event(request, slug):
    event = get_object_or_404(Event, slug=slug, creator=request.user)
    categories = Groupcategory.objects.filter(parent=None)

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        is_virtual = request.POST.get('is_virtual')
        virtual_link = request.POST.get('virtual_link')
        location = request.POST.get('location')
        event_image = request.FILES.get('event_image')
        category = request.POST.get('category')

        if not all([title, description, start_time, end_time]):
            messages.warning(request, "Required fields: title, description, start/end time")
            return redirect('edit_event', slug=slug)

        try:
            event.title = title
            event.description = description
            event.start_time = start_time
            event.end_time = end_time
            event.is_virtual = is_virtual == 'True'
            event.virtual_link = virtual_link if virtual_link else None
            event.location = location if location else None
            event.category = Groupcategory.objects.get(id=category) if category else None
            
            if event_image:
                event.event_image = event_image
            
            event.save()
            messages.success(request, "Event updated successfully!")
            return redirect('event_detail', slug=event.slug)
        except Exception as e:
            messages.error(request, f"Error updating event: {str(e)}")

    context = {
        'categories': categories,
        'event': event,
        'edit_mode': True
    }
    return render(request, 'commu_prenair/create_event.html', context)


@authenticated_user_required_commu
def profile(request, slug):
    user = User.objects.get(slug=slug)
    posts = Post.objects.filter(author=user, is_group_post=False).order_by('-created_at')
    
    context = {
        'user': user,
        'posts': posts
    }
    return render(request, 'commu_prenair/profile.html', context)


@authenticated_user_required_commu
def profile_about(request, slug):
    user = User.objects.get(slug=slug)
    
    context = {
        'user': user,
    }   
    return render(request, 'commu_prenair/about.html', context)

@authenticated_user_required_commu
def profile_groups(request, slug):
    user = User.objects.get(slug=slug)
    groups = Group.objects.filter(members=user)
    
    context = {
        'user': user,
        'groups': groups
    }
    return render(request, 'commu_prenair/profile_groups.html', context)


@authenticated_user_required_commu
def group_detail(request, slug):
    group = Group.objects.get(slug=slug)
    friends_in_group = group.friends_who_joined(request.user)
    friends_count = group.friends_who_joined(request.user).count()
    if not group.is_member(request.user):
        messages.warning(request, "You Must Join this Group to view it")
        return redirect('commu_groups')
    posts = group.group_posts.all().order_by('-created_at')
    context = {
        'group': group,
        'posts': posts,
        'friends_count': friends_count,
        'friends_in_group': friends_in_group
    }
    return render(request, 'commu_prenair/group_detail.html', context)

# from django.db.models import Q


@authenticated_user_required_commu
def manage_group(request, slug):
    group = get_object_or_404(Group, slug=slug)
    member_requests = GroupMemberShipRequests.objects.filter(group=group)

    query = request.GET.get('query')
    if query:
        member_requests = member_requests.filter(
            Q(user__username__icontains=query) | Q(user__email__icontains=query)
        )

    if request.method == 'POST':
        action = request.POST.get('action')

        if action in ['approve_all', 'decline_all'] and not member_requests.exists():
            messages.warning(request, "No member requests to approve or decline.")
            return redirect('manage_group', slug=slug)

        if action == 'approve_all':
            for member_request in member_requests:
                group.members.add(member_request.user)
                group.save()
                member_request.delete()
            messages.success(request, "All member requests approved and users added to the group.")
        elif action == 'decline_all':
            member_requests.delete()
            messages.success(request, "All member requests declined.")
        else:
            member_id = request.POST.get('member_id')
            if action == 'approve' and member_id:
                member_request = get_object_or_404(GroupMemberShipRequests, id=member_id, group=group)
                group.members.add(member_request.user)
                group.save()
                member_request.delete()
                messages.success(request, f"{member_request.user} approved and added to the group.")
            elif action == 'decline' and member_id:
                member_request = get_object_or_404(GroupMemberShipRequests, id=member_id, group=group)
                member_request.delete()
                messages.success(request, f"{member_request.user} declined.")

        return redirect('manage_group', slug=slug)

    context = {
        'group': group,
        'member_requests': member_requests,
        'query': query
    }
    return render(request, 'commu_prenair/manage_group.html', context)


def get_child_categories(request):
    parent_id = request.GET.get("parent_id")
    if parent_id:
        categories = Groupcategory.objects.filter(parent_id=parent_id)
    else:
        categories = Groupcategory.objects.none()
    
    category_data = [{"id": cat.id, "name": cat.name} for cat in categories]
    return JsonResponse({"categories": category_data})


@authenticated_user_required_commu
def create_group(request):
    categories = Groupcategory.objects.filter(parent=None)
    if request.method == 'POST':
        name = request.POST.get('name')
        desc = request.POST.get('desc')
        is_private = request.POST.get('is_private')
        profile_img = request.FILES.get('profile_img')
        cover_img = request.FILES.get('cover_img')
        category_l_1 = request.POST.get('category_l_1')
        category_l_2 = request.POST.get('category_l_2')
        category_l_3 = request.POST.get('category_l_3')


        if not name or not desc or not profile_img or not cover_img:
            messages.warning(request, "All fields are required.")
            return redirect('create_group')
        
        group = Group.objects.create(
            name=name,
            desc=desc,
            admin=request.user,
            is_private=is_private,
            profile_img=profile_img if profile_img else None,
            bg_img=cover_img if cover_img else None,
            slug=slugify(name) + "-" + str(uuid.uuid4())[:6],
            category_l_1=Groupcategory.objects.get(id=category_l_1),
            category_l_2=Groupcategory.objects.get(id=category_l_2),
            category_l_3=Groupcategory.objects.get(id=category_l_3)
        )
        
        group.members.add(request.user)
        group.save()
        
        return redirect('commu_profile_groups', slug=request.user.slug)
    
    context = {
        'categories': categories
    }
    
    return render(request, 'commu_prenair/create_group.html', context)


@authenticated_user_required_commu
def group_list(request):
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
        
    context = {
        'groups': groups
    }
    return render(request, 'commu_prenair/group_list.html', context)


@authenticated_user_required_commu
def join_group(request, slug):
    group = Group.objects.get(slug=slug)
    if not group.is_private:
        group.members.add(request.user)
        group.save()
        messages.success(request, "You have joined the group successfully!")
        return redirect('group_detail', slug=slug)
    else:
        # Create membership request
        GroupMemberShipRequests.objects.create(group=group, user=request.user)
        messages.success(request, "Your request has been sent to the group admin.")
        Notification.objects.create(user=group.admin,message=f'{request.user.username} has requested to join your group', app_name='commuprenair')
        return redirect('commu_groups')


@authenticated_user_required_commu
def leave_group(request, slug):
    group = Group.objects.get(slug=slug)
    group.members.remove(request.user)
    group.save()
    if group.admin == request.user:
        group.admin = group.members.first()
        group.save()
    messages.success(request, "You have left the group successfully.")
    return redirect('commu_groups')



# ----------------------------------       Connections         ---------------------------------
from django.db.models import Q

@authenticated_user_required_commu
def profile_connections(request, slug):
    user = get_object_or_404(User, slug=slug)

    # Get the search query from the request
    query = request.GET.get('q', '')
    
    # Filter connections_sent and connections_received separately before union
    connections_sent = User.objects.filter(connections_sent__to_user=user)
    connections_received = User.objects.filter(connections_received__from_user=user)
    
    if query:
        # Apply the search filter individually before union
        connections_sent = connections_sent.filter(
            Q(name__icontains=query) | Q(username__icontains=query)
        )
        connections_received = connections_received.filter(
            Q(name__icontains=query) | Q(username__icontains=query)
        )
    
    # Union the filtered results
    connections = connections_sent.union(connections_received)

    context = {
        'user': user,
        'connections': connections,
        'query': query,  # Include query to repopulate the search input if needed
    }
    return render(request, 'commu_prenair/profile_connections.html', context)



@authenticated_user_required_commu
def connection_requests(request):
    friend_requests = FriendRequest.objects.filter(to_user=request.user)
    
    context = {
        'friend_requests': friend_requests
    }
    return render(request, 'commu_prenair/connection_requests.html', context)


@authenticated_user_required_commu
def send_friend_request(request, slug):
    to_user = get_object_or_404(User, slug=slug)
    
    if FriendRequest.objects.filter(from_user=request.user, to_user=to_user).exists() or \
       FriendRequest.objects.filter(from_user=to_user, to_user=request.user).exists() or \
       Connection.objects.filter(from_user=request.user, to_user=to_user).exists() or \
       Connection.objects.filter(from_user=to_user, to_user=request.user).exists():
        messages.warning(request, f"You have already sent a friend request to {to_user.name} or are already connected.")
        return redirect('commu_profile', slug=to_user.slug)

    FriendRequest.objects.create(from_user=request.user, to_user=to_user)
    messages.success(request, f"Friend request sent to {to_user.name}.")
    Notification.objects.create(user=to_user,message=f'{request.user.username} has sent you a friend request', app_name='commuprenair')

    return redirect('commu_profile', slug=to_user.slug)


@authenticated_user_required_commu
def withdraw_friend_request(request, slug):
    to_user = get_object_or_404(User, slug=slug)
    
    try:
        friend_request = FriendRequest.objects.get(from_user=request.user, to_user=to_user)
    except FriendRequest.DoesNotExist:
        messages.warning(request, "No Connection request exists between you and this user.")
        return redirect('commu_home')

    friend_request.delete()
    messages.success(request, f"Connection request to {to_user.name} withdrawn.")
    return redirect('commu_profile', slug=to_user.slug)


@authenticated_user_required_commu
def handle_friend_request(request, slug, action):
    # Get the user based on the slug
    to_user = get_object_or_404(User, slug=slug)
    
    # Get the pending friend request between the logged-in user and the target user
    try:
        # Check if the current user is the one receiving the request
        friend_request = FriendRequest.objects.get(from_user=to_user, to_user=request.user)
    except FriendRequest.DoesNotExist:
        try:
            # Check if the current user has sent a friend request to the target user
            friend_request = FriendRequest.objects.get(from_user=request.user, to_user=to_user)
        except FriendRequest.DoesNotExist:
            messages.warning(request, "No friend request exists between you and this user.")
            return redirect('commu_home')

    # Make sure that the current user is the one receiving the request
    if friend_request.to_user != request.user:
        messages.warning(request, "You cannot respond to this friend request.")
        return redirect('commu_home') 

    if action == 'accept':
        # Create a mutual connection between the users
        Connection.objects.create(from_user=friend_request.from_user, to_user=friend_request.to_user)
        Connection.objects.create(from_user=friend_request.to_user, to_user=friend_request.from_user)
        messages.success(request, "Friend request accepted!")
        Notification.objects.create(user=friend_request.from_user,message=f'{request.user.username} has accepted your friend request', app_name='commuprenair')

    elif action == 'reject':
        messages.info(request, "Friend request rejected.")
    
    # Delete the friend request after responding to it
    friend_request.delete()
    return redirect('connection_requests')


@authenticated_user_required_commu
def remove_connection(request, slug):
    other_user = get_object_or_404(User, slug=slug)

    Connection.objects.filter(from_user=request.user, to_user=other_user).delete()
    Connection.objects.filter(from_user=other_user, to_user=request.user).delete()

    messages.success(request, f"You have unfollowed {other_user.name}.")
    return redirect('commu_connections', slug=request.user.slug)  


@authenticated_user_required_commu
def search_people(request):
    query = request.GET.get('q', '')
    if query:
        users = User.objects.filter(
            Q(name__icontains=query) | Q(username__icontains=query)
        ).exclude(slug=request.user.slug)
    else:
        users = User.objects.all().exclude(slug=request.user.slug)
    
    context = {
        'people': users,
        'query': query
    }
    return render(request, 'commu_prenair/search_people.html', context)


@authenticated_user_required_commu
def profile_settings(request):
    if request.method == 'POST':
        profile_pic = request.FILES.get('profile_pic')
        name = request.POST.get('name')
        bio = request.POST.get('bio')

        user = request.user
        if name:
            user.name = name
        if bio:
            user.commu_bio = bio
        if profile_pic:
            user.profile_pic = profile_pic

        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile_settings')
    return render(request, 'commu_prenair/profile_settings.html')






# ----------------------------------       Chat         ---------------------------------
@authenticated_user_required_commu
def user_messages(request):
    user_chats = request.user.get_all_chats()
    
    chats_with_last_message = []
    for user_chat in user_chats:
        last_message = user_chat.chat_messages.order_by('-timestamp').first()
        unread_count = user_chat.chat_messages.filter(is_read=False, receiver=request.user).count()
        chats_with_last_message.append((user_chat, last_message, unread_count))

    context = {
        'user_chats': chats_with_last_message
    }
    return render(request, 'commu_prenair/commu_messages.html', context)


@authenticated_user_required_commu
def private_chat(request, slug):
    chat = PrivateChat.objects.filter(slug=slug).first()
    
    if not chat:
        other_user_slug = request.GET.get('user_slug')
        other_user = get_object_or_404(User, slug=other_user_slug)
        
        chat = PrivateChat.objects.filter(
            (Q(user1=request.user, commu_prenair_chat=True) & Q(user2=other_user, commu_prenair_chat=True)) | (Q(user1=other_user, commu_prenair_chat=True) & Q(user2=request.user, commu_prenair_chat=True))
        ).first()
        
        if not chat:
            unique_uuid = uuid.uuid4()
            slug = slugify(f"{request.user.username}-{other_user.username}-{unique_uuid}")
            chat = PrivateChat.objects.create(user1=request.user, user2=other_user, slug=slug)
            Notification.objects.create(user=other_user,message=f'{request.user.username} has started a chat with you on Commuprenair', app_name='commuprenair')
        return redirect('private_chat', slug=chat.slug)

    chat_messages = chat.chat_messages.all().order_by('timestamp')
    user_chats = request.user.get_all_chats()
    chat.chat_messages.filter(is_read=False, receiver=request.user).update(is_read=True)
    chats_with_last_message = []
    for user_chat in user_chats:
        last_message = user_chat.chat_messages.order_by('-timestamp').first()
        unread_count = user_chat.chat_messages.filter(is_read=False, receiver=request.user).count()
        chats_with_last_message.append((user_chat, last_message, unread_count))

    chat_with = chat.user1 if request.user != chat.user1 else chat.user2
    
    return render(request, 'commu_prenair/private_chat.html', {
        'chat_with': chat_with,
        'chat_messages': chat_messages,
        'chatSlug': chat.slug,
        'user_chats': chats_with_last_message
    })







def get_subcategories(request, category_id):
    level_2_categories = Groupcategory.objects.filter(parent_id=category_id)

    data = []
    for category in level_2_categories:
        children = category.group_categories.all()
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



from django.contrib.auth.decorators import login_required
@login_required
def mark_all_messages_notifications_as_read(request):
    # Mark all notifications as read
    notifications = request.user.notifications.filter(app_name='commuprenair',  is_message=True)
    notifications.update(is_read=True)
    
    return redirect('commu_messages')
    