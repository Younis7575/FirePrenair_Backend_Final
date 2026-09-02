from django.urls import path
from .views import *
from dashboard.views import live_website_view, serve_funnel_entry


def root_router(request):
    if getattr(request, 'is_funnel', False):
        return serve_funnel_entry(request)
    elif getattr(request, 'website', None):
        return live_website_view(request)
    return home(request)

urlpatterns = [
    path('', root_router, name='home'),
    path('leaderboard/', leaderboard_dashboard, name='leaderboard_dashboard'),
    path('home_chatbot/', fireprenair_chat_bot, name='home_chatbot'),
    path('delete_thread/', delete_chat_thread, name='delete_chat_thread'),
    path('work-parent-categories/', work_parent_categories, name='work_parent_categories'),
    path('edu-parent-categories/', edu_parent_categories, name='edu_parent_categories'),
    path('digi-parent-categories/', digi_parent_categories, name='digi_parent_categories'),
    path('commu-parent-categories/', commu_parent_categories, name='commu_parent_categories'),

    # legal pages
    path('terms-of-use/', terms_of_use, name='terms_of_use'),
    path('license-agreement/', license_agreement, name='license_agreement'),
    path('privacy-policy/', privacy_policy, name='privacy_policy'),
    path('copyright-information/', copyright_info, name='copyright_info'),
    path('cookie-policy/', cookies, name='cookie_policy'),
    path('dmca-policy/', dmca_policy, name='dmca_policy'),
    path('privacy-choice-policy/', privacy_choice_policy, name='privacy_choice_policy'),
    path('refund-policy/', refund_policy, name='refund_policy'),

    # company pages
    path('about-us/', about_us, name='about_us'),
    path('contact-support/', contact_support, name='contact_support'),
    path('help-support/', help_support, name='help_support'),
    path('how-it-works/', how_it_works, name='how_it_works'),
    path('pricing/', pricing, name='pricing'),
    path('fees-and-commissions/', fees_commisions, name='fees_and_commissions'),
    path('faq/', faq, name='faq'),

    # Resources pages
    path('training/', training, name='training'),
    path('digital-products/', digital_products, name='digital_products'),
    path('affiliate-program/', affiliates, name='affiliate_program'),
    path('partners/', partnerships, name='partners'),
    path('community/', community, name='community'),

    # features
    path('features/', features, name='features'),

    # corporate solutions
    path('corporate-solutions/', corporate_solutions, name='corporate_solutions'),
    path('corporate/check-email/', corporate_check_email, name='corporate_check_email'),
    path('corporate/login/', corporate_login_api, name='corporate_login_api'),
    path('corporate/verify-otp/', corporate_verify_otp, name='corporate_verify_otp'),
    path('corporate/submit-project/', submit_corporate_project, name='submit_corporate_project'),
    path('corporate-dashboard/', corporate_dashboard, name='corporate_dashboard'),
    path('feature/', feature_detail, name='feature_detail'),

    #blogs
    path('blogs/', blog_list, name='blog_list'),    
    path('blogs/<slug:slug>/', blog_detail, name='blog_detail'),

]
