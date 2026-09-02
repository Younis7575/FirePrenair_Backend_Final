from .views import *
from django.urls import path

urlpatterns = [
    path("", edu_home, name="edu_home"),
    path("profile/<slug:slug>/", edu_profile, name="edu_profile"),
    path("settings/", edu_settings, name="edu_settings"),
    path("instructor/dashboard/", instructor_dashboard, name="edu_instructor_dashboard"),

    path("instructors/", instructors, name="edu_instructors"),

    path("instructor/add-course/", add_course, name="edu_add_course"),
    path("instructor/courses/", my_courses, name="edu_my_courses"),
    path("instructor/course/<slug:slug>/submit/",submit_for_approval,name="submit_for_approval",),
    path("instructor/course/<slug:course_slug>/add-module/",add_module,name="add_module",),
    path("instructor/course/module/<int:module_id>/add-lesson/",add_lesson,name="add_lesson",),
    path("instructor/course/<slug:slug>/delete/", delete_course, name="delete_course"),
    
    path("lesson-complete/<slug:lesson_slug>/<str:course_slug>/",mark_lesson_completed,name="mark_lesson_completed",),
    path("student/dashboard/", edu_student_dashboard, name="edu_student_dashboard"),
    path("student/courses/", student_courses, name="student_courses"),
    path("reviews/", reviews, name="reviews"),

    path("courses/", all_courses, name="courses"),
    path('course/analyze-review/', analyze_review, name='analyze_review'),
    path("course/<slug:slug>/", course_detail, name="course_detail"),
    path("course/<slug:slug>/content/", course_content, name="course_content"),
    path('course/view_lesson/<slug:lesson_slug>/', view_lesson, name='view_lesson'),
    path('course/lesson/generate_audio/', generate_speech, name='generate_speech'),
    path('generate-quiz/<slug:course_slug>/', generate_quiz, name='generate_quiz'),
    path('take-quiz/<int:quiz_id>/', take_quiz, name='take_quiz'),
    path('quiz-results/<int:attempt_id>/', quiz_results, name='quiz_results'),
    path("course/<slug:course_slug>/get_certificate/", get_certificate, name="get_certificate"),
    path("course/<slug:slug>/post-review/", post_review, name="post_review"),
    path("course/<slug:slug>/add-to-wishlist/", add_to_wishlist, name="add_to_wishlist"),
    path("course/<slug:slug>/remove-from-wishlist/",remove_from_wishlist,name="remove_from_wishlist"),
    path("wishlist/", wishlists, name="wishlist"),
    path("order-history/", order_history, name="edu_order_history"),

    path("announcements/", announcements, name="edu_announcements"),
    path("announcements/add/", add_announcement, name="add_edu_announcement"),
    path("announcements/<int:id>/delete/",delete_announcement,name="delete_edu_announcement"),

    path("earnings/", earnings, name="edu_earnings"),

    path("course/<slug:course_slug>/checkout/",course_payment_view, name="course_checkout",),
    path("course-webhook/stripe/", stripe_webhook, name="course-stripe-webhook"),
    path("get-child-categories/<int:category_id>/",get_subcategories,name="get_child_categories"),

    path('paypal-checkout/<slug:course_slug>/', paypal_course_checkout, name='paypal_course_checkout'),
    path('paypal-success/<slug:course_slug>/', paypal_course_success, name='paypal_course_success'),


    path("eduprenair_chatbot/", eduprenair_chatbot_view, name="eduprenair_chatbot_view"),
    path("become-instructor/", become_intructor, name="become_instructor"),
]
