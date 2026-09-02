from django.urls import path  # Import path function
from . import views  # Import views from current directory

urlpatterns = [
    # stripe payment
    path("checkout/", views.checkout, name="checkout"),
    path("webhook/", views.my_stripe_webhook, name="stripe_webhook"),
    
    # PayPal payment
    path("paypal/checkout/", views.paypal_checkout, name="paypal_checkout"),
    path("paypal/success/", views.paypal_payment_success, name="paypal_payment_success"),
    
    
    path("", views.digi_home, name="digi_home"),  # Home page
    path("logout/", views.logout_view, name="logout"),
    path("explore/", views.digi_explore, name="digi_explore"),  # Explore page
    path("product-search/", views.product_search_api, name="product_search_api"),  
    path("sellers/", views.digi_sellers, name="digi_sellers"),  # Sellers page
    path("product/<slug:slug>/", views.digi_product, name="digi_product"),  # Product details
    path("profile/<slug:slug>/", views.digi_profile, name="digi_profile"),  # User profile
    path("shoping_cart/", views.digi_shoping_cart, name="digi_shoping_cart"),  # Shopping cart
    path("add_to_cart/<slug:slug>/", views.add_to_cart, name="add_to_cart"),
    path("remove_from_cart/<slug:slug>/", views.remove_from_cart, name="remove_from_cart"),
    path("notifications/", views.digi_notifications, name="digi_notifications"),  # User notifications
    path("profile_info/", views.digi_profile_info, name="digi_profile_info"),  # Profile information
    path("profile_settings/", views.digi_profile_settings, name="digi_profile_settings"),  # Settings
    path( "remove_from_cart/<slug:slug>/", views.remove_from_cart, name="remove_from_cart"),
    path("notifications/", views.digi_notifications, name="digi_notifications"),
    path("notifications/read/<int:notification_id>/", views.mark_notification_as_read, name="mark_notification_as_read"),
    path("notifications/delete/<int:notification_id>/", views.delete_notification, name="delete_notification"),
    path("notifications/mark-all-read/", views.mark_all_notifications_as_read, name="mark_all_notifications_as_read"),
    path("profile_info/", views.digi_profile_info, name="digi_profile_info"),  # Profile information
    path("profile_settings/", views.digi_profile_settings, name="digi_profile_settings"),  # Settings
    path("dashboard/", views.digi_dashboard, name="digi_dashboard"),  # User dashboard
    path("upload_item/", views.digi_upload_item, name="digi_upload_item"),  # Upload item
    path("manage_items/", views.digi_manage_items, name="digi_manage_items"),  # Manage items
    path("edit-product/<slug:slug>/", views.edit_item, name="edit_item"),
    path("purchases/", views.digi_purchases, name="digi_purchases"),  # Purchases page
    path('add-to-project/', views.add_to_project, name='add_to_project'),
    path("become_seller/", views.digi_become_seller, name="digi_become_seller"),  # Become a seller
    path("get-child-categories/<int:category_id>/", views.get_subcategories, name="get_child_categories"),  # Get child categories
    path("digiprenair_chatbot/", views.digiprenair_chatbot_view, name="digiprenair_chatbot_view"),
]
