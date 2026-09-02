from django.urls import path
from . import views
from .views_payouts import (
    payout_request, payout_settings, payment_history, user_billings,
    paypal_manual_transfer, validate_payout_api, save_identity_api
)

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('notifications/', views.dashboard_notifications, name='dashboard_notifications'),
    path('notifications/delete/<int:notification_id>/', views.delete_notification, name='delete_notification'),
    path('my_refrerrals/', views.my_referrals, name='my_referrals'),
    path('my_access_token/', views.personal_access_token, name='access_token'),
    path('access-token/verify/', views.verify_access_token, name='verify_access_token'),

    # website builder
    path('my_websites/', views.my_websites, name='my_websites'),
    path('create_website/', views.create_website, name='create_website'),
    path('get_template_categories/', views.get_template_categories, name='get_template_categories'),
    path('select_template/', views.select_template, name='select_template'),
    path('create_from_template/<int:template_id>/', views.create_from_template, name='create_from_template'),
    path('get_user_website/<int:website_id>/', views.get_user_site_html, name='get_user_website'),
    path('edit_website/<int:website_id>/', views.edit_website, name='edit_website'),
    path('website/<int:website_id>/publish/', views.publish_website_ajax, name='publish_website_ajax'),
    path('', views.live_website_view),
    path('delete_website/<int:website_id>/', views.delete_website, name='delete_website'),
    path('save_website/', views.save_website, name='save_website'),

    path('', views.serve_funnel_entry, name='funnel_entry'),
    path('step/<int:step_order>/', views.serve_funnel_step, name='funnel_step'),
    path('funnels/funnel-lead/', views.funnel_lead_api, name='funnel_lead_api'),
    path('create-checkout/<int:funnel_id>/<int:product_id>/', views.create_checkout_session, name='create_checkout_session'),
    path('payment-success/<int:funnel_id>/', views.handle_payment_success, name='handle_payment_success'),
    path('funnels/<int:funnel_id>/success/', views.handle_payment_success, name='payment_success'),
    path('funnels/', views.funnel_list, name='funnel_list'),
    path('funnels/create/', views.create_funnel, name='create_funnel'),
    path('funnels/<int:funnel_id>/edit/', views.edit_funnel, name='edit_funnel'),
    path('funnels/delete/<int:funnel_id>/', views.delete_funnel, name='delete_funnel'),
    path('funnel/<int:id>/', views.run_funnel, name='run_funnel'),
    path('funnels/<int:funnel_id>/publish/', views.publish_funnel_ajax, name='publish_funnel_ajax'),
    path('funnels/emails-by-tag/', views.funnel_emails_by_tag_view, name='funnel_emails_by_tag'),
    path('funnels/send-tag-email/', views.send_tag_email_view, name='send_tag_email'),




    # path('commuprenair/', views.commu_dashboard, name='dashboard_commuprenair'),

    path('get-child-categories-digi/', views.get_child_categories_digi, name='get_child_categories_digi'),

    # Digiprenair
    path("profile/<int:user_id>/", views.user_profile, name="user_profile"),
    path('digiprenair/', views.dashboard_digiprenair, name='dashboard_digiprenair'),
    path('products/generate-upload-url/', views.generate_digiprenair_upload_url, name='generate_digiprenair_upload_url'),
    path('digiprenair/upload_item/', views.upload_item_digiprenair, name='upload_item_digiprenair'),
    path('digiprenair/manage_item/', views.manage_item_digiprenair, name='manage_item_digiprenair'),
    path("digiprenair/edit_item_digiprenair/<slug:slug>/", views.edit_item_digiprenair, name="edit_item_digiprenair"),
    path('digiprenair/projects/', views.digi_projects, name='digi_projects'),
    path('digiprenair/projects/<int:id>/', views.digi_project_detail, name='digi_project'),
    path('digiprenair/download-product/<int:product_id>/', views.download_product_file, name='download_product'),
    path('image_generation/', views.image_generation, name='image_generation'),
    path('logo_generation/', views.logo_gen, name='logo_generation'),
    path('video_generation/', views.video_generation, name='video_generation'),
    path('generate-video/', views.generate_video, name='generate_video'),
    path('ebook_generation/', views.generate_ebook, name='ebook_generation'),
    path('generate-ebook-images/', views.generate_ebook_images, name='generate_ebook_images'),
    path('preview-ebook/', views.ebook_preview, name='preview_ebook'),
    path('generate_pdf/', views.generate_pdf, name='generate_pdf'),

    # Eduprenair
    path('get-child-categories/', views.get_child_categories, name='get_child_categories'),
    path('eduprenair/', views.dashboard_eduprenair, name='dashboard_eduprenair'),
    path('eduprenair/manage_courses/', views.manage_courses_eduprenair, name='manage_courses_eduprenair'),
    path('eduprenair/analyze_student_progress/', views.analyze_student_progress, name='analyze_student_progress'),
    path('eduprenair/course_create/', views.course_create_eduprenair, name='course_create_eduprenair'),
    path("eduprenair/course_submit/<slug:course_slug>/", views.submit_for_approval, name="submit_for_approval"),
    path("eduprenair/course_edit/<slug:course_slug>/", views.course_edit_eduprenair, name="course_edit_eduprenair"),
    path("course/delete/<slug:slug>/", views.delete_course, name="delete_course"),
    path('eduprenair/course/<slug:course_slug>/add-module/', views.add_module_course_eduprenair, name='add_module_course_eduprenair'),
    path('eduprenair/course/module/<int:module_id>/add-lesson/', views.add_lesson_course_eduprenair, name='add_lesson_course_eduprenair'),
    path('eduprenair/edit-lesson/<int:lesson_id>/', views.edit_lesson_course_eduprenair, name='edit_lesson_course_eduprenair'),
    path('generate-module-lessons/<slug:course_slug>/', views.generate_module_lessons_eduprenair, name='generate_module_lessons'),
    path('delete-lesson/<int:lesson_id>/', views.delete_lesson, name='delete_lesson'),
    path('course/<str:course_slug>/stats/', views.course_stats, name='course_stats'),
    path('digi-reviews/', views.digi_reviews, name='digi_reviews'),

    path('edit_profile/', views.dashboard_edit_profile, name='dashboard_edit_profile'),
    path('change_password/', views.dashboard_change_password, name='dashboard_change_password'),

    
    # commuprenair
    path('commuprenair/', views.dashboard_commuprenair, name='dashboard_commuprenair'),
    
    # AI
    path("generate-description-eduprenair/", views.generate_description_eduprenair, name="generate_description_eduprenair"),
    path("generate-description-digiprenair/", views.generate_description_digiprenair, name="generate_description_digiprenair"),
    path("generate-description-workprenair/", views.generate_description_workprenair, name="generate_description_workprenair"),
    
    # path('dashboard_chatbot/', views.dashboard_chatbot_view, name='dashboard_chatbot'),
    

    # Payouts
    path('billing/', user_billings, name='billings'),
    path('request-payout/', payout_request, name="payout_request"),
    path('payout-settings/', payout_settings, name="payout_settings"),
    path('payment-history/', payment_history, name="payment_history"),
    # path('paypal-transfer/', paypal_transfer, name="paypal_transfer"),
    path('paypal-transfer/', paypal_manual_transfer, name="paypal_transfer"),
    
    # KYC/Identity Verification APIs
    path('api/validate-payout/', validate_payout_api, name="validate_payout_api"),
    path('api/save-identity/', save_identity_api, name="save_identity_api"),



    # Admin Urls
    path('admin/', views.admin_dash, name='admin_dashboard'),
    path('admin/online-users/', views.admin_online_users, name='admin_users'),
    path('admin/statistics/', views.admin_stats, name='admin_stats'),
    path('admin/sales/digiprenair/', views.digi_sales, name='admin_digi_sales'),
    path('admin/sales/workprenair/', views.work_sales, name='admin_work_sales'),
    path('admin/withdrawal_requests/', views.withdrawl_requests, name='admin_withdrawal_requests'),
    path('admin/withdrawal_requests/<int:withdraw_id>/', views.withdraw_admin_detail, name='withdraw_admin_detail'),
    path('admin/traffic-logs/', views.admin_traffic_logs, name='admin_traffic_logs'),
    path('admin/traffic-insights-json/', views.traffic_insights_json, name='traffic_insights_json'),
]