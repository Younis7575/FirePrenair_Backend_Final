from .views import *
from django.urls import path

urlpatterns = [
    path('', work_home, name='work_home'),
    path('buyer-dashboard/', buyer_dashboard, name='buyer_dashboard'),
    path('seller-dashboard/', sellor_dashboard, name='sellor_dashboard'),
    path('my_orders/', user_orders, name='user_orders'),

    path('profile/<str:username>/', user_profile, name='work_user_profile'),
    path('profile/edit', edit_profile, name='edit_work_profile'),

    path('messages/', user_chats, name='user_chats'),
    path('message/<str:chatSlug>/', user_chat, name='user_chat'),
    path('message/ai-suggestions/<str:chatSlug>/', ai_chat_assist, name='ai_chat_assist'),

    path('api/categories/<int:parent_id>/', get_child_categories, name='get_child_categories'),
    path('api/search_tags/', search_tags, name='search_tags'),
    path("api/gig-tags/<str:gig_slug>/", gig_tags, name="gig_tags"),
    path('api/create_tag/', create_tag, name='create_tag'),

    path('todos/', todos, name='todos'),
    path('todos/create/', create_todo, name='create_todo'),
    path('todos/update/<int:pk>/', update_todo, name='update_todo'),
    path('todos/delete/<int:pk>/', delete_todo, name='delete_todo'),

    
    path('services/', gigs, name='gigs'),
    path('gigs/', user_gigs, name='user_gigs'),
    path('gig/create/', create_gig, name='create_gig'),
    path('gig/<str:slug>', gig_detail, name='gig_detail'),
    path('gig/<str:slug>/edit/', edit_gig, name='edit_gig'),
    path('gig/<str:slug>/delete/', delete_gig, name='delete_gig'),
    path('gig/optimize/<str:slug>/', optimize_gig, name='optimize_gig'),
    path('gig/apply-suggestion/', apply_gig_ai_suggestion, name='apply_gig_ai_suggestion'),
    path('gigs/<slug:slug>/suggest_pricing/', suggest_gig_pricing, name='suggest_gig_pricing'),

    path('order/<str:order_slug>/', order_detail, name='order_detail'),
    path('order/submit_requirements/<int:order_id>/', submit_requirements, name='submit_order_requirements'),
    path('order/<str:order_slug>/delivery/', order_delivery, name='order_delivery'),
    path('order/<str:delivery_slug>/revision/', request_revision, name="request_revision"),
    path('order/<str:order_slug>/complete/', complete_order, name='order_complete'),
    path('order/<str:order_slug>/review/', review_order, name='order_review'),

    path('offers/', custom_offers_list, name='custom_offers_list'),
    path('offer/create/', create_offer, name='create_offer'),
    path('offer/generate_proposal/', generate_proposal_description, name='generate_proposal_description'),
    path('offer/decline/<str:offer_id>/', decline_offer, name='decline_offer'),
    path('offer/delete/<str:offer_id>/', delete_offer, name='delete_offer'),


    path("gig/<slug:gig_slug>/checkout/<str:package_type>/", gig_checkout, name="gig_checkout"),
    path("custom-offer/checkout/<int:offer_id>/", custom_offer_checkout, name="custom_offer_checkout"),
    path("webhook/", stripe_webhook, name="stripe_work_order_webhook"),

    # paypal
    path("paypal/checkout/<str:gig_slug>/<str:package_type>/", paypal_checkout, name="paypal_checkout"),
    path("paypal/success/", paypal_success, name="paypal_success"),
    path("paypal/cancel/", paypal_cancel, name="paypal_cancel"),

    # paypal custom offer
    path("custom-offer/paypal-checkout/<int:offer_id>/", custom_offer_paypal_checkout, name="custom_offer_paypal_checkout"),
    path("custom-offer/paypal-success/", custom_offer_paypal_success, name="custom_offer_paypal_success"),

    path('categories/top/', get_top_categories, name='top_categories'),
    path('categories/hierarchy/<int:category_id>/', get_subcategories, name='subcategories'),
    # path('categories/nested/<int:category_id>/', get_nested_subcategories, name='nested_subcategories'),
    
    path('workprenair_chatbot/', workprenair_chatbot_view, name='workprenair_chatbot_view'),

    path('become-seller/', become_seller, name='become_seller'),
    path('switch-profile/', toggle_profile, name='toggle_work_profile'),
    
    path('workprenair_notifications/', workprenair_notifications, name='workprenair_notifications'),


]
