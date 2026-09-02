from .views import *
from django.urls import path

urlpatterns = [
    path('login/', login_user, name='login'),
    path('register/', register_user, name='register'),
    path('verify-email/', verify_email, name='verify_email'),
    path('logout/', logout_user, name='logout'),
    path('check-username/', check_username_availability, name='check_username'),
    path('check-email/', check_email_availability, name='check_email'),

    path('checkout/<int:plan_id>/', create_checkout_session, name='create_checkout_session'),
    path('webhook/', stripe_webhook, name='stripe_webhook_plan'),
    path('billing-portal/', stripe_billing_portal, name='billing_portal'),

    path('change-language/', update_language, name='change_language'),

    path('api/forgot-password/', forgot_password_api, name='forgot_password_api'),
    path('api/forgot-username/', forgot_username_api, name='forgot_username_api'),
    path('api/password-reset-confirm/', password_reset_confirm_api, name='password_reset_confirm_api'),

]