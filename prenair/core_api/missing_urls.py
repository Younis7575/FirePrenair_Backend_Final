"""
URL patterns for all missing REST API endpoints.
These are appended to core_api/urls.py
"""
from django.urls import path
from .missing_apis import *
from .missing_apis_v2 import *
from .missing_apis_v3 import *
from .home_views import home_subscribe_api
from .edu_prenair_views import get_notifications_api

urlpatterns = [
    # ==================== COMMUPRENAIR EVENTS ====================
    path('commuprenair/events/', events_list_api, name='commu_events_api'),
    path('commuprenair/events/create/', create_event_api, name='commu_create_event_api'),
    path('commuprenair/events/create/ai/', generate_ai_event_api, name='commu_generate_ai_event_api'),
    path('commuprenair/events/<str:slug>/', event_detail_api, name='commu_event_detail_api'),
    path('commuprenair/events/join/<str:slug>/', join_event_api, name='commu_join_event_api'),
    path('commuprenair/events/leave/<str:slug>/', leave_event_api, name='commu_leave_event_api'),
    path('commuprenair/events/edit/<str:slug>/', edit_event_api, name='commu_edit_event_api'),

    # ==================== WEBSITE BUILDER ====================
    path('dashboard/my_websites/', my_websites_api, name='my_websites_api'),
    path('dashboard/create_website/', create_website_api, name='create_website_api'),
    path('dashboard/get_template_categories/', get_template_categories_api, name='get_template_categories_api'),
    path('dashboard/select_template/', select_template_api, name='select_template_api'),
    path('dashboard/get_user_website/<int:website_id>/', get_user_website_html_api, name='get_user_website_api'),
    path('dashboard/save_website/', save_website_api, name='save_website_api'),
    path('dashboard/website/<int:website_id>/publish/', publish_website_api, name='publish_website_api'),
    path('dashboard/delete_website/<int:website_id>/', delete_website_api, name='delete_website_api'),

    # ==================== FUNNEL SYSTEM ====================
    path('dashboard/funnels/', funnel_list_api, name='funnel_list_api'),
    path('dashboard/funnels/create/', create_funnel_api, name='create_funnel_api'),
    path('dashboard/funnels/<int:funnel_id>/edit/', edit_funnel_api, name='edit_funnel_api'),
    path('dashboard/funnels/delete/<int:funnel_id>/', delete_funnel_api, name='delete_funnel_api'),
    path('dashboard/funnels/<int:funnel_id>/publish/', publish_funnel_api, name='publish_funnel_api'),
    path('dashboard/funnels/emails-by-tag/', funnel_emails_by_tag_api, name='funnel_emails_by_tag_api'),

    # ==================== AI GENERATION ====================
    path('dashboard/image_generation/', ImageGenerationAPIView.as_view(), name='image_generation_api'),
    path('dashboard/logo_generation/', LogoGenerationAPIView.as_view(), name='logo_generation_api'),
    path('dashboard/video_generation/', VideoGenerationAPIView.as_view(), name='video_generation_api'),
    path('dashboard/ebook_generation/', EbookGenerationAPIView.as_view(), name='ebook_generation_api'),
    path('dashboard/generate_pdf/', GeneratePdfAPIView.as_view(), name='generate_pdf_api'),

    # ==================== WORK PRENAIR MISSING ====================
    path('workprenair/gigs/<str:slug>/suggest_pricing/', suggest_gig_pricing_api, name='suggest_gig_pricing_api'),
    path('workprenair/offer/generate_proposal/', generate_proposal_description_api, name='generate_proposal_description_api'),

    # ==================== EDUPRENAIR MISSING ====================
    path('eduprenair/course/lesson/generate_audio/', GenerateSpeechAPIView.as_view(), name='generate_speech_api'),
    path('dashboard/generate-module-lessons/<str:course_slug>/', generate_module_lessons_api, name='generate_module_lessons_api'),
    path('dashboard/delete-lesson/<int:lesson_id>/', delete_lesson_api, name='delete_lesson_api'),
    path('dashboard/edit-lesson/<int:lesson_id>/', edit_lesson_api, name='edit_lesson_api'),
    path('dashboard/analyze_student_progress/', analyze_student_progress_api, name='analyze_student_progress_api'),
    path('dashboard/course/<str:course_slug>/stats/', course_stats_api, name='course_stats_api'),

    # ==================== DIGIPRENAIR MISSING ====================
    path('digiprenair/add-to-project/', add_to_project_api, name='digi_add_to_project_api'),
    path('digiprenair/projects/', digi_projects_api, name='digi_projects_api'),
    path('digiprenair/projects/<int:project_id>/', digi_project_detail_api, name='digi_project_detail_api'),
    path('digiprenair/download-product/<int:product_id>/', download_product_file_api, name='digi_download_product_api'),
    path('products/generate-upload-url/', generate_digiprenair_upload_url_api, name='generate_digiprenair_upload_url_api'),
    path('dashboard/digiprenair/manage_item/', manage_item_digiprenair_api, name='manage_item_digiprenair_api'),
    path('dashboard/get-child-categories-digi/', get_child_categories_digi_api, name='get_child_categories_digi_api'),

    # ==================== DASHBOARD MISSING ====================
    path('dashboard/my_referrals/', my_referrals_api, name='my_referrals_api'),
    path('dashboard/my_access_token/', personal_access_token_api, name='personal_access_token_api'),
    path('dashboard/access-token/verify/', verify_access_token_api, name='verify_access_token_api'),
    path('dashboard/digi-reviews/', digi_reviews_api, name='digi_reviews_api'),

    # ==================== AI DESCRIPTION GENERATORS ====================
    path('dashboard/generate-description-eduprenair/', generate_description_eduprenair_api, name='generate_description_eduprenair_api'),
    path('dashboard/generate-description-digiprenair/', generate_description_digiprenair_api, name='generate_description_digiprenair_api'),
    path('dashboard/generate-description-workprenair/', generate_description_workprenair_api, name='generate_description_workprenair_api'),

    # ==================== HOME CHATBOT ====================
    path('home/home_chatbot/', home_chatbot_api, name='home_chatbot_api'),

    # ==================== LEADERBOARD ====================
    path('home/leaderboard/', leaderboard_dashboard_api, name='leaderboard_dashboard_api'),

    # ==================== CORPORATE SOLUTIONS ====================
    path('home/corporate/check-email/', corporate_check_email_api, name='corporate_check_email_api'),
    path('home/corporate/login/', corporate_login_api_v2, name='corporate_login_api_v2'),
    path('home/corporate/verify-otp/', corporate_verify_otp_api, name='corporate_verify_otp_api'),
    path('home/corporate/submit-project/', submit_corporate_project_api, name='submit_corporate_project_api'),
    path('home/corporate-dashboard/', corporate_dashboard_api, name='corporate_dashboard_api'),

    # ==================== BLOGS ====================
    path('home/blogs/', blog_list_api, name='blog_list_api'),
    path('home/blogs/<str:slug>/', blog_detail_api, name='blog_detail_api'),

    # ==================== CHAT THREAD ====================
    path('home/delete_thread/', delete_chat_thread_api, name='delete_chat_thread_api'),

    # ==================== HOME SUBSCRIBE ====================
    path('home/subscribe/', home_subscribe_api, name='home_subscribe_api'),

    # ==================== EDU NOTIFICATIONS ====================
    path('eduprenair/notifications/', get_notifications_api, name='edu_notifications_api'),

    # ==================== FUNNEL SEND TAG EMAIL ====================
    path('dashboard/funnels/send-tag-email/', send_tag_email_api_v2, name='send_tag_email_api_v2'),

    # ==================== PROFILE RECOVERY & CHECK ====================
    path('my_accounts/forgot-password/', forgot_password_api_v2, name='forgot_password_api_v2'),
    path('my_accounts/forgot-username/', forgot_username_api_v2, name='forgot_username_api_v2'),
    path('my_accounts/password-reset-confirm/', password_reset_confirm_api_v2, name='password_reset_confirm_api_v2'),
    path('my_accounts/check-username/', check_username_availability_api, name='check_username_availability_api'),
    path('my_accounts/check-email/', check_email_availability_api, name='check_email_availability_api'),

    # ==================== ADMIN SALES ====================
    path('dashboard/admin/sales/digiprenair/', digi_sales_api, name='admin_digi_sales_api'),
    path('dashboard/admin/sales/workprenair/', work_sales_api, name='admin_work_sales_api'),
]
