from .views import *
from django.urls import path

urlpatterns = [
    path('', home, name='commu_home'),

    path('make-post/', make_post, name='make_post'),

    path('post/<str:slug>/', post_detail, name='post_detail'),
    path('delete_post/<str:slug>/', delete_post, name='delete_post'),
    path('post/<str:post_slug>/add_comment/', add_comment, name='add_comment'),
    path('add-reply/<int:comment_id>/', add_reply, name='add_reply'),
    path('add-reply1<int:comment_id>/', add_reply1, name='add_reply1'),
    path('like/<str:slug>/', toggle_like, name='toggle_like'),
    path('likes/<str:slug>/', get_likes, name='get_likes'),

    path('search/', search_people, name='search_people'),
    
    path('profile/<str:slug>/', profile, name='commu_profile'),
    path('profile-settings/', profile_settings, name='profile_settings'),

    path('about/<str:slug>/', profile_about, name='commu_about'),

    path('get-child-categories/', get_child_categories, name='get_child_categories'),

    path('groups/', group_list, name='commu_groups'),
    path('groups/create/', create_group, name='create_group'),
    path('groups/<str:slug>/', profile_groups, name='commu_profile_groups'),
    path('group/<str:slug>/', group_detail, name='group_detail'),
    path('group/<str:slug>/manage/', manage_group, name='manage_group'),
    path('group/<str:slug>/join/', join_group, name='join_group'),
    path('group/<str:slug>/leave/', leave_group, name='leave_group'),
    path('group/<slug:slug>/post/', make_group_post, name='make_group_post'),

    path('events/', event_list, name='commu_events'),
    path('events/create/', create_event, name='create_event'),
    path("events/create/ai/", generate_ai_event, name=""),
    path('events/<str:slug>/', event_detail, name='event_detail'),
    path('events/join/<slug:slug>/', join_event, name='join_event'),
    path('events/leave/<slug:slug>/', leave_event, name='leave_event'),
    path('events/edit/<slug:slug>/', edit_event, name='edit_event'),

    path('connection-requests/', connection_requests, name='connection_requests'),
    path('connections/<str:slug>/', profile_connections, name='commu_connections'),
    path('send-connection-request/<slug:slug>/', send_friend_request, name='send_friend_request'),
    path('withdraw-connection-request/<str:slug>/', withdraw_friend_request, name='withdraw_friend_request'),

    path('friend-request/<slug:slug>/<str:action>/', handle_friend_request, name='handle_friend_request'),
    path('remove-connection/<slug:slug>/', remove_connection, name='remove_connection'),

    path("chat/", user_messages, name="commu_messages"),
    path('chat/<str:slug>/', private_chat, name='private_chat'),

    path('sub-child-categories/<int:category_id>/', get_subcategories, name='get_subcategories'),

    path('commuprenair_chatbot/', commuprenair_chatbot_view, name='commuprenair_chatbot_view'),
    
    path("notifications/read/all/", mark_all_messages_notifications_as_read, name="mark_all_messages_notifications_as_read"),

]
