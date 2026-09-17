from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .profiles_views import (LoginUserAPIView,RegisterUserAPIView,VerifyEmailAPIView,LogoutUserAPIView,
    CreateCheckoutSessionAPIView,StripeWebhookAPIView,StripeBillingPortalAPIView,UpdateLanguageAPIView
    )
from .commu_prenair_views import *
from .home_views import *
from .digiprenair_views import *
from .edu_prenair_views import *
from .work_prenair_views import *
from .dashboard_views import *
from .missing_urls import urlpatterns as missing_urlpatterns
from .fcm_views import register_fcm_token, unregister_fcm_token, test_push_notification

urlpatterns = [
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    ##############################################################  commu_prenair APP VIEWS URLS ############################################################
    
    path('commuprenair/home/', commu_prenair_home_api, name='commu_home_api'),

    path('commuprenair/make-post/', MakePostView.as_view(), name='make_post_api'),

    path('commuprenair/post/<str:slug>/', post_detail_api, name='post_detail_api'),
    path('commuprenair/delete_post/<str:slug>/', delete_post_api, name='delete_post_api'),
    path('commuprenair/post/<str:post_slug>/add_comment/', add_comment_api, name='add_comment_api'),
    path('commuprenair/add-reply/<int:comment_id>/', add_reply_api, name='add_reply_api'),
    path('commuprenair/add-reply1<int:comment_id>/', add_reply1_api, name='add_reply1_api'),
    path('commuprenair/like/<str:slug>/', toggle_like_api, name='toggle_like_api'),
    path('commuprenair/likes/<str:slug>/', get_likes_api, name='get_likes_api'),

    path('commuprenair/search/', search_people_api, name='search_people_api'),
    
    path('commuprenair/profile/<str:slug>/', profile_api, name='commu_profile_api'),
    path('commuprenair/profile-settings/', profile_settings_api, name='profile_settings_api'),

    path('commuprenair/about/<str:slug>/', profile_about_api, name='commu_about_api'),

    path('commuprenair/get-child-categories/', get_child_categories_api, name='get_child_categories_api'),
    path('commuprenair/get_group_categories_api/', get_group_categories_api, name='get_group_categories_api'),

    path('commuprenair/groups/', group_list_api, name='commu_groups_api'),
    path('commuprenair/groups/create/', createe_group_api, name='createe_group_api'),
    path('commuprenair/groups/<str:slug>/', profile_groups_api, name='commu_profile_groups_api'),
    path('commuprenair/group/<str:slug>/', group_detail_api, name='group_detail_api'),
    path('commuprenair/group/<str:slug>/manage/', manage_group_api, name='manage_group_api'),
    path('commuprenair/group/<str:slug>/join/', join_group_api, name='join_group_api'),
    path('commuprenair/group/<str:slug>/leave/', leave_group_api, name='leave_group_api'),
    path('commuprenair/group/<slug:slug>/post/', make_group_post_api, name='make_group_post_api'),

    path('commuprenair/connection-requests/', connection_requests_api, name='connection_requests_api'),
    path('commuprenair/connections/<str:slug>/', profile_connections_api, name='commu_connections_api'),
    path('commuprenair/send-connection-request/<slug:slug>/', send_friend_request_api, name='send_friend_request_api'),
    path('commuprenair/withdraw-connection-request/<str:slug>/', withdraw_friend_request_api, name='withdraw_friend_request_api'),

    path('commuprenair/friend-request/<slug:slug>/<str:action>/', handle_friend_request_api, name='handle_friend_request_api'),
    path('commuprenair/remove-connection/<slug:slug>/', remove_connection_api, name='remove_connection_api'),

    path("commuprenair/chat/", user_messages_api, name="commu_messages_api"),
    path('commuprenair/chat/<str:slug>/', private_chat_api, name='private_chat_api'),

    path('commuprenair/sub-child-categories/<int:category_id>/', get_subcategories_api, name='get_subcategories_api'),

    path('commuprenair/commuprenair_chatbot/', CommuprenairChatbotView.as_view(), name='commuprenair_chatbot_view_api'),
    
    path("commuprenair/notifications/read/all/", mark_all_messages_notifications_as_read_api, name="mark_all_messages_notifications_as_read_api"),

    ###################################################################  HOME VIEWS #######################################################

    path('home/home/', home_api, name='home_api'),
    path('home/home_chatbot/', home_chatbot_view_api, name='home_chatbot_api'),
    path('home/work-parent-categories/', work_parent_categories_api, name='work_parent_categories_api'),
    path('home/edu-parent-categories/', edu_parent_categories_api, name='edu_parent_categories_api'),
    path('home/digi-parent-categories/', DigiParentCategoriesView.as_view(), name='digi_parent_categories_api'),
    path('home/commu-parent-categories/', commu_parent_categories_api, name='commu_parent_categories_api'),
    # legal pages
    path('home/terms-of-use/', terms_of_use_api, name='terms_of_use_api'),
    path('home/license-agreement/', license_agreement_api, name='license_agreement_api'),
    path('home/privacy-policy/', privacy_policy_api, name='privacy_policy_api'),
    path('home/copyright-information/', copyright_info_api, name='copyright_info_api'),
    path('home/cookie-policy/', cookies_api, name='cookie_policy_api'),
    path('home/dmca-policy/', dmca_policy_api, name='dmca_policy_api'),
    path('home/privacy-choice-policy/', privacy_choice_policy_api, name='privacy_choice_policy_api'),
    path('home/refund-policy/', refund_policy_api, name='refund_policy_api'),
    # company pages
    path('home/about-us/', about_us_api, name='about_us_api'),
    path('home/contact-support/', contact_support_api, name='contact_support_api'),
    path('home/help-support/', help_support_api, name='help_support_api'),
    path('home/how-it-works/', how_it_works_api, name='how_it_works_api'),
    path('home/pricing/', pricing_api, name='pricing_api'),
    path('home/fees-and-commissions/', fees_commisions_api, name='fees_and_commissions_api'),
    path('home/faq/', faq_api, name='faq_api'),

    # Resources pages
    path('home/training/', training_api, name='training_api'),
    path('home/digital-products/', digital_products_api, name='digital_products_api'),
    path('home/affiliate-program/', affiliates_api, name='affiliate_program_api'),
    path('home/partners/', partnerships_api, name='partners_api'),
    path('home/community/', community_api, name='community_api'),

    # features
    path('home/features/', features_api, name='features_api'),
    path('home/feature/', feature_detail_api, name='feature_detail_api'),   
    
    ######################################################  profiles APP VIEWS URLS ######################################################
    path('my_accounts/login/', LoginUserAPIView.as_view(), name='login_api'),
    path('my_accounts/register/', RegisterUserAPIView.as_view(), name='register_api'),
    path('my_accounts/verify-email/', VerifyEmailAPIView.as_view(), name='verify_email_api'),
    path('my_accounts/logout/', LogoutUserAPIView.as_view(), name='logout_api'),

    path('my_accounts/checkout/<int:plan_id>/', CreateCheckoutSessionAPIView.as_view(), name='create_checkout_session_api'),
    path('my_accounts/webhook/', StripeWebhookAPIView.as_view(), name='stripe_webhook_plan_api'),
    path('my_accounts/billing-portal/', StripeBillingPortalAPIView.as_view(), name='billing_portal_api'),

    path('my_accounts/change-language/', UpdateLanguageAPIView.as_view(), name='change_language_api'),

    # ── FCM Push Notifications ────────────────────────────────────────
    path('my_accounts/fcm-register/', register_fcm_token, name='fcm_register_api'),
    path('my_accounts/fcm-unregister/', unregister_fcm_token, name='fcm_unregister_api'),
    path('my_accounts/test-push/', test_push_notification, name='test_push_api'),



    ###################################################  DIGI-PRENAIR ######################################################################
    # # Stripe payment
    path("digiprenair/checkout_api/", checkout_api, name="checkout_api"),
    path("digiprenair/webhook_api/", my_stripe_webhook_api, name="stripe_webhook_api"),

    # PayPal payment
    path("digiprenair/paypal/checkout_api/", paypal_checkout_api, name="paypal_checkout_api"),
    path("digiprenair/paypal/success_api/", paypal_payment_success_api, name="paypal_payment_success_api"),

    # General pages
    path("digiprenair/home/", DigiHomeAPIView.as_view(), name="digi_home_api"),
    path("digiprenair/logout_api/", logout_view_api, name="logout_api"),
    path("digiprenair/explore_api/", DigiExploreAPIView.as_view(), name="digi_explore_api"),
    path("digiprenair/sellers_api/", digi_sellers_api, name="digi_sellers_api"),
    path("digiprenair/product_api/<slug:slug>/", digi_product_api, name="digi_product_api"),
    path("digiprenair/profile_api/<slug:slug>/", digi_profile_api, name="digi_profile_api"),

    # Cart
    path("digiprenair/shoping_cart_api/", digi_shoping_cart_api, name="digi_shoping_cart_api"),
    path("digiprenair/add_to_cart_api/<slug:slug>/", add_to_cart_api, name="add_to_cart_api"),
    path("digiprenair/update_cart_item/<int:item_id>/", update_cart_item_api, name="update_cart_item_api"),
    path("digiprenair/remove_from_cart_api/<slug:slug>/", remove_from_cart_api, name="remove_from_cart_api"),

    # Notifications
    path("digiprenair/notifications_api/", digi_notifications_api, name="digi_notifications_api"),
    path("digiprenair/notifications_api/read/<int:notification_id>/", mark_notification_as_read_api, name="mark_notification_as_read_api"),
    path("digiprenair/notifications_api/delete/<int:notification_id>/", delete_notification_api, name="delete_notification_api"),
    path("digiprenair/notifications_api/mark-all-read/", mark_all_notifications_as_read_api, name="mark_all_notifications_as_read_api"),

    # Profile
    path("digiprenair/profile_info_api/", digi_profile_info_api, name="digi_profile_info_api"),
    path("digiprenair/profile_settings_api/", digi_profile_settings_api, name="digi_profile_settings_api"),

    # Dashboard & Items
    path("digiprenair/dashboard_api/", digi_dashboard_api, name="digi_dashboard_api"),
    path("digiprenair/upload_item_api/", digi_upload_item_api, name="digi_upload_item_api"),
    path("digiprenair/manage_items_api/", digi_manage_items_api, name="digi_manage_items_api"),
    path("digiprenair/edit-product_api/<slug:slug>/", edit_item_api, name="edit_item_api"),
    path("digiprenair/purchases_api/", digi_purchases_api, name="digi_purchases_api"),
    path("digiprenair/become_seller_api/", digi_become_seller_api, name="digi_become_seller_api"),

    # Categories & Chatbot
    path("digiprenair/get-child-categories_api/<int:category_id>/", digi_get_subcategories_api, name="get_child_categories_api"),
    path("digiprenair/digiprenair_chatbot_api/", digiprenair_chatbot_view_api, name="digiprenair_chatbot_view_api"),

    path('getch_product_upload/', create_product_from_getch, name='create_product_from_getch'),
    

    # #########################################----> word prenair <----######################################################3
    # path("eduprenair/home/", edu_home_api, name="edu_home_api"),
    # path("eduprenair/profile/<slug:slug>/", edu_profile_api, name="edu_profile_api"),
    # path("eduprenair/settings/", edu_settings_api, name="edu_settings_api"),
    # path("eduprenair/instructor/dashboard/", instructor_dashboard_api, name="edu_instructor_dashboard_api"),

    # path("eduprenair/instructors/", InstructorsAPIView.as_view(), name="edu_instructors_api"),

    # path("eduprenair/instructor/add-course/", add_course_api, name="edu_add_course_api"),
    # path("eduprenair/instructor/courses/", my_courses_api, name="edu_my_courses_api"),
    # path("eduprenair/instructor/course/<slug:slug>/submit/", submit_for_approval_api, name="submit_for_approval_api"),
    # path("eduprenair/instructor/course/<slug:course_slug>/add-module/", add_module_api, name="add_module_api"),
    # path("eduprenair/instructor/course/module/<int:module_id>/add-lesson/", add_lesson_api, name="add_lesson_api"),
    # path("eduprenair/instructor/course/<slug:slug>/delete/", delete_course_api, name="delete_course_api"),

    # path("eduprenair/lesson-complete/<slug:lesson_slug>/<str:course_slug>/", mark_lesson_completed_api, name="mark_lesson_completed_api"),
    # path("eduprenair/student/dashboard/", edu_student_dashboard_api, name="edu_student_dashboard_api"),
    # path("eduprenair/student/courses/", student_courses_api, name="student_courses_api"),
    # path("eduprenair/reviews/", reviews_api, name="reviews_api"),

    # path("eduprenair/courses/", AllCoursesAPIView.as_view(), name="courses_api"),
    # path("eduprenair/course/analyze-review/", analyze_review_api, name="analyze_review_api"),
    # path("eduprenair/course/<slug:slug>/", course_detail_api, name="course_detail_api"),
    # path("eduprenair/course/<slug:slug>/content/", course_content_api, name="course_content_api"),
    # path("eduprenair/course/view_lesson/<slug:lesson_slug>/", view_lesson_api, name="view_lesson_api"),
    # path("eduprenair/generate-quiz/<slug:course_slug>/", generate_quiz_api, name="generate_quiz_api"),
    # path("eduprenair/take-quiz/<int:quiz_id>/", take_quiz_api, name="take_quiz_api"),
    # path("eduprenair/quiz-results/<int:attempt_id>/", quiz_results_api, name="quiz_results_api"),
    # path("eduprenair/course/<slug:course_slug>/get_certificate/", get_certificate_api, name="get_certificate_api"),
    # path("eduprenair/course/<slug:slug>/post-review/", post_review_api, name="post_review_api"),
    # path("eduprenair/course/<slug:slug>/add-to-wishlist/", add_to_wishlist_api, name="add_to_wishlist_api"),
    # path("eduprenair/course/<slug:slug>/remove-from-wishlist/", remove_from_wishlist_api, name="remove_from_wishlist_api"),
    # path("eduprenair/wishlist/", wishlists_api, name="wishlist_api"),
    # path("eduprenair/order-history/", order_history_api, name="edu_order_history_api"),

    # path("eduprenair/announcements/", announcements_api, name="edu_announcements_api"),
    # path("eduprenair/announcements/add/", add_announcement_api, name="add_edu_announcement_api"),
    # path("eduprenair/announcements/<int:id>/delete/", delete_announcement_api, name="delete_edu_announcement_api"),

    # path("eduprenair/earnings/", earnings_api, name="edu_earnings_api"),

    # path("eduprenair/course/<slug:course_slug>/checkout/", course_payment_view_api, name="course_checkout_api"),
    # path("eduprenair/course-webhook/stripe/", stripe_webhook_api, name="course-stripe-webhook_api"),
    # path("eduprenair/get-child-categories/<int:category_id>/", get_subcategories_api, name="get_child_categories_api"),

    # path("eduprenair/paypal-checkout/<slug:course_slug>/", paypal_course_checkout_api, name="paypal_course_checkout_api"),
    # path("eduprenair/paypal-success/<slug:course_slug>/", paypal_course_success_api, name="paypal_course_success_api"),

    # path("eduprenair/eduprenair_chatbot/", eduprenair_chatbot_api, name="eduprenair_chatbot_view_api"),
    # path("eduprenair/become-instructor/", become_instructor_api, name="become_instructor_api"),

    #########################################----> word prenair <----######################################################3

    path("eduprenair/home/", edu_home_api, name="edu_home_api"),
    path("eduprenair/profile/<slug:slug>/", edu_profile_api, name="edu_profile_api"),
    path("eduprenair/settings/", edu_settings_api, name="edu_settings_api"),
    path("eduprenair/instructor/dashboard/", instructor_dashboard_api, name="edu_instructor_dashboard_api"),
    path("eduprenair/instructors/", InstructorsAPIView.as_view(), name="edu_instructors_api"),
    path("eduprenair/instructor/add-course/", add_course_api, name="edu_add_course_api"),
    path("eduprenair/instructor/courses/", my_courses_api, name="edu_my_courses_api"),
    path("eduprenair/instructor/course/<slug:slug>/submit/", submit_for_approval_api, name="submit_for_approval_api"),
    path("eduprenair/instructor/course/<slug:course_slug>/add-module/", add_module_api, name="add_module_api"),
    path("eduprenair/instructor/course/module/<int:module_id>/add-lesson/", add_lesson_api, name="add_lesson_api"),
    path("eduprenair/instructor/course/<slug:slug>/delete/", delete_course_api, name="delete_course_api"),
    path("eduprenair/lesson-complete/<slug:lesson_slug>/<str:course_slug>/", mark_lesson_completed_api, name="mark_lesson_completed_api"),
    path("eduprenair/student/dashboard/", edu_student_dashboard_api, name="edu_student_dashboard_api"),
    path("eduprenair/student/courses/", student_courses_api, name="student_courses_api"),
    path("eduprenair/reviews/", reviews_api, name="reviews_api"),
    path("eduprenair/courses/", AllCoursesAPIView.as_view(), name="courses_api"),
    path("eduprenair/course/analyze-review/", analyze_review_api, name="analyze_review_api"),
    path("eduprenair/course/<slug:slug>/", course_detail_api, name="course_detail_api"),
    path("eduprenair/course/<slug:slug>/content/", course_content_api, name="course_content_api"),
    path("eduprenair/course/view_lesson/<slug:lesson_slug>/", view_lesson_api, name="view_lesson_api"),
    path("eduprenair/generate-quiz/<slug:course_slug>/", generate_quiz_api, name="generate_quiz_api"),
    path("eduprenair/take-quiz/<int:quiz_id>/", take_quiz_api, name="take_quiz_api"),
    path("eduprenair/quiz-results/<int:attempt_id>/", quiz_results_api, name="quiz_results_api"),
    path("eduprenair/course/<slug:course_slug>/get_certificate/", get_certificate_api, name="get_certificate_api"),
    path("eduprenair/course/<slug:slug>/post-review/", post_review_api, name="post_review_api"),
    path("eduprenair/course/<slug:slug>/add-to-wishlist/", add_to_wishlist_api, name="add_to_wishlist_api"),
    path("eduprenair/course/<slug:slug>/remove-from-wishlist/", remove_from_wishlist_api, name="remove_from_wishlist_api"),
    path("eduprenair/wishlist/", wishlists_api, name="wishlist_api"),
    path("eduprenair/order-history/", order_history_api, name="edu_order_history_api"),
    path("eduprenair/announcements/", announcements_api, name="edu_announcements_api"),
    path("eduprenair/announcements/add/", add_announcement_api, name="add_edu_announcement_api"),
    path("eduprenair/announcements/<int:id>/delete/", delete_announcement_api, name="delete_edu_announcement_api"),
    path("eduprenair/earnings/", earnings_api, name="edu_earnings_api"),
    path("eduprenair/course/<slug:course_slug>/checkout/", course_payment_view_api, name="course_checkout_api"),
    path("eduprenair/course-webhook/stripe/", stripe_webhook_api, name="course-stripe-webhook_api"),
    path("eduprenair/get-child-categories/<int:category_id>/", get_subcategories_api, name="get_child_categories_api"),
    path("eduprenair/paypal-checkout/<slug:course_slug>/", paypal_course_checkout_api, name="paypal_course_checkout_api"),
    path("eduprenair/paypal-success/<slug:course_slug>/", paypal_course_success_api, name="paypal_course_success_api"),
    path("eduprenair/eduprenair_chatbot/", eduprenair_chatbot_api, name="eduprenair_chatbot_view_api"),
    path("eduprenair/become-instructor/", become_instructor_api, name="become_instructor_api"),
    ###################################################----->workprenair<---------------------##############################################################
    path('workprenair/home/', work_home_api, name='work_home_api'),
    path('workprenair/buyer-dashboard/', buyer_dashboard_api, name='buyer_dashboard_api'),
    path('workprenair/seller-dashboard/', sellor_dashboard_api, name='sellor_dashboard_api'),
    path('workprenair/my_orders/', user_orders_api, name='user_orders_api'),

    # The literal route has to come first: `<str:username>` matches "edit",
    # so declared the other way round every request to profile/edit/ was
    # answered by user_profile_api with username="edit" and edit_profile_api
    # was unreachable.
    path('workprenair/profile/edit/', edit_profile_api, name='edit_work_profile_api'),
    path('workprenair/profile/<str:username>/', user_profile_api, name='work_user_profile_api'),

    path('workprenair/messages/', user_chats_api, name='user_chats_api'),
    path('workprenair/message/<str:chatSlug>/', user_chat_api, name='user_chat_api'),
    path('workprenair/message/ai-suggestions/<str:chatSlug>/', ai_chat_assist_api, name='ai_chat_assist_api'),

    path('workprenair/api/categories/<int:parent_id>/', get_child_categories_api, name='get_child_categories_api'),
    path('workprenair/api/search_tags/', search_tags_api, name='search_tags_api'),
    path("workprenair/api/gig-tags/<str:gig_slug>/", gig_tags_api, name="gig_tags_api"),
    path('workprenair/api/create_tag/', create_tag_api, name='create_tag_api'),

    path('workprenair/todos/', todos_api, name='todos_api'),
    path('workprenair/todos/create/', create_todo_api, name='create_todo_api'),
    path('workprenair/todos/update/<int:pk>/', update_todo_api, name='update_todo_api'),
    path('workprenair/todos/delete/<int:pk>/', delete_todo_api, name='delete_todo_api'),

    path('workprenair/services/', gigs_api, name='gigs_api'),
    path('workprenair/gigs/', user_gigs_api, name='user_gigs_api'),
    path('workprenair/gig/create/', create_gig_api, name='create_gig_api'),
    # The only route in the project that was missing its trailing slash, so
    # `workprenair/gig/<slug>/` — the form ApiEndpoints.workGigDetail builds,
    # and the one every sibling route uses — 404'd. Callers that still omit the
    # slash are redirected onto this by APPEND_SLASH.
    path('workprenair/gig/<str:slug>/', gig_detail_api, name='gig_detail_api'),
    path('workprenair/gig/<str:slug>/edit/', edit_gig_api, name='edit_gig_api'),
    path('workprenair/gig/<str:slug>/delete/', delete_gig_api, name='delete_gig_api'),
    path('workprenair/gig/optimize/<str:slug>/', optimize_gig_api, name='optimize_gig_api'),
    path('workprenair/gig/apply-suggestion/', apply_gig_ai_suggestion_api, name='apply_gig_ai_suggestion_api'),

    path('workprenair/order/<str:order_slug>/', order_detail_api, name='order_detail_api'),
    path('workprenair/order/submit_requirements/<int:order_id>/', submit_requirements_api, name='submit_order_requirements_api'),
    path('workprenair/order/<str:order_slug>/delivery/', order_delivery_api, name='order_delivery_api'),
    path('workprenair/order/<str:delivery_slug>/revision/', request_revision_api, name="request_revision_api"),
    path('workprenair/order/<str:order_slug>/complete/', complete_order_api, name='order_complete_api'),
    path('workprenair/order/<str:order_slug>/review/', review_order_api, name='order_review_api'),

    path('workprenair/offers/', CustomOffersListAPIView.as_view(), name='custom_offers_list_api'),
    path('workprenair/offer/create/', create_offer_api, name='create_offer_api'),
    path('workprenair/offer/decline/<str:offer_id>/', decline_offer_api, name='decline_offer_api'),
    path('workprenair/offer/delete/<str:offer_id>/', delete_offer_api, name='delete_offer_api'),

    path("workprenair/gig/<slug:gig_slug>/checkout/<str:package_type>/", gig_checkout_api, name="gig_checkout_api"),
    path("workprenair/custom-offer/checkout/<int:offer_id>/", custom_offer_checkout_api, name="custom_offer_checkout_api"),
    path("workprenair/webhook/", StripeWebhookView.as_view(), name="stripe_work_order_webhook_api"),

    # PayPal
    path("workprenair/paypal/checkout/<str:gig_slug>/<str:package_type>/", paypal_checkout_api, name="paypal_checkout_api"),
    path("workprenair/paypal/success/", PayPalSuccessAPIView.as_view(), name="paypal_success_api"),
    path("workprenair/paypal/cancel/", paypal_cancel_api, name="paypal_cancel_api"),

    # PayPal custom offer
    path("workprenair/custom-offer/paypal-checkout/<int:offer_id>/", CustomOfferPayPalCheckoutAPIView.as_view(), name="custom_offer_paypal_checkout_api"),
    path("workprenair/custom-offer/paypal-success/", custom_offer_paypal_success_api, name="custom_offer_paypal_success_api"),

    path('workprenair/categories/top/', get_top_categories_api, name='top_categories_api'),
    path('workprenair/categories/hierarchy/<int:category_id>/', get_work_subcategories_api, name='subcategories_api'),

    path('workprenair/workprenair_chatbot/', workprenair_chatbot_view_api, name='workprenair_chatbot_view_api'),

    path('workprenair/become-seller/', become_seller_api, name='become_seller_api'),
    path('workprenair/switch-profile/', toggle_profile_api, name='toggle_work_profile_api'),

    path('workprenair/workprenair_notifications/', workprenair_notifications_api, name='workprenair_notifications_api'),

    ###################################################################----> dashboard <----################################################################33


    path('dashboard/home/', dashboard_home_api, name='dashboard_home_api'),
    path('dashboard/notifications/', dashboard_notifications_api, name='dashboard_notifications_api'),
    path('dashboard/notifications/delete/<int:notification_id>/', delete_notification_api, name='delete_notification_api'),

    path('dashboard/get-child-categories-digi/', get_child_categories_digi_api, name='get_child_categories_digi_api'),

    # Digiprenair
    path('dashboard/digiprenair/', dashboard_digiprenair_api, name='dashboard_digiprenair_api'),
    path('dashboard/digiprenair/upload_item/', upload_item_digiprenair_api, name='upload_item_digiprenair_api'),
    path('dashboard/digiprenair/manage_item/', manage_item_digiprenair_api, name='manage_item_digiprenair_api'),
    path("dashboard/digiprenair/edit_item_digiprenair/<slug:slug>/", edit_item_digiprenair_api, name="edit_item_digiprenair_api"),
    path('dashboard/image_generation/', image_generation_api, name='image_generation_api'),
    path('dashboard/logo_generation/', logo_generation_api, name='logo_generation_api'),

    # Eduprenair
    path('dashboard/get-child-categories/', get_child_categories_api, name='get_child_categories_api'),
    path('dashboard/eduprenair/', dashboard_eduprenair_api, name='dashboard_eduprenair_api'),
    path('dashboard/eduprenair/manage_courses/', manage_courses_eduprenair_api, name='manage_courses_eduprenair_api'),
    path('dashboard/eduprenair/course_create/', course_create_eduprenair_api, name='course_create_eduprenair_api'),
    path("dashboard/eduprenair/course_submit/<slug:course_slug>/", submit_for_approval_api, name="submit_for_approval_api"),
    path("dashboard/eduprenair/course_edit/<slug:course_slug>/", course_edit_eduprenair_api, name="course_edit_eduprenair_api"),
    path("dashboard/course/delete/<slug:slug>/", delete_course_api, name="delete_course_api"),
    path('dashboard/eduprenair/course/<slug:course_slug>/add-module/', add_module_course_eduprenair_api, name='add_module_course_eduprenair_api'),
    path('dashboard/eduprenair/course/module/<int:module_id>/add-lesson/', add_lesson_course_eduprenair_api, name='add_lesson_course_eduprenair_api'),
    path('dashboard/delete-lesson/<int:lesson_id>/', delete_lesson_api, name='delete_lesson_api'),
    path('dashboard/course/<str:course_slug>/stats/', course_stats_api, name='course_stats_api'),
    path('dashboard/digi-reviews/', digi_reviews_api, name='digi_reviews_api'),

    path('dashboard/edit_profile/', dashboard_edit_profile_api, name='dashboard_edit_profile_api'),
    path('dashboard/change_password/', dashboard_change_password_api, name='dashboard_change_password_api'),

    # commuprenair
    path('dashboard/commuprenair/', dashboard_commuprenair_api, name='dashboard_commuprenair_api'),

    # AI
    path("dashboard/generate-description-eduprenair/", generate_description_eduprenair_api, name="generate_description_eduprenair_api"),
    path("dashboard/generate-description-digiprenair/", generate_description_digiprenair_api, name="generate_description_digiprenair_api"),
    path("dashboard/generate-description-workprenair/", generate_description_workprenair_api, name="generate_description_workprenair_api"),

    # Payouts
    path('dashboard/billing/', user_billings_api, name='billings_api'),
    path('dashboard/request-payout/', payout_request_api, name="payout_request_api"),
    path('dashboard/payout-settings/', payout_settings_api, name="payout_settings_api"),
    path('dashboard/payment-history/', payment_history_api, name="payment_history_api"),
    path('dashboard/paypal-transfer/', paypal_manual_transfer_api, name="paypal_transfer_api"),

    # Admin Urls
    path('dashboard/admin/', admin_dash_api, name='admin_dashboard_api'),
    path('dashboard/admin/online-users/', admin_online_users_api, name='admin_users_api'),
    path('dashboard/admin/statistics/', admin_stats_api, name='admin_stats_api'),
    path('dashboard/admin/withdrawal_requests/', withdrawal_requests_api, name='admin_withdrawal_requests_api'),
    path('dashboard/admin/withdrawal_requests/<int:withdraw_id>/', withdraw_admin_detail_api, name='withdraw_admin_detail_api'),
    path('dashboard/admin/traffic-logs/', admin_traffic_logs_api, name='admin_traffic_logs_api'),    path('dashboard/admin/traffic-insights-json/', traffic_insights_json_api, name='traffic_insights_json_api'),
] + missing_urlpatterns