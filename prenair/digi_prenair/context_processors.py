from profiles.models import Notification

def unread_notification_count(request):
    unread_count = 0
    recent_unread_notifications = []
    unread_message_count = 0
    recent_unread_messages = []
    latest_notifications_by_app = {}
    
    # Initialize the current app name
    current_app_name = None  

    if request.user.is_authenticated:
        app_names = ['eduprenair', 'digiprenair', 'commuprenair', 'workprenair']
        
        # Check if the user is on a specific app page
        for app in app_names:
            if app in request.path:
                current_app_name = app
                break

        if current_app_name:
            # Filter notifications for the current app
            notifications = request.user.notifications.filter(app_name=current_app_name, is_message=False)
            unread_count = notifications.filter(is_read=False).count()
            recent_unread_notifications = notifications.filter(is_read=False).order_by('-created_at')[:5]

            unread_messages = request.user.notifications.filter(app_name=current_app_name, is_message=True)
            unread_message_count = unread_messages.filter(is_read=False).count()
            recent_unread_messages = unread_messages.filter(is_read=False).order_by('-created_at')[:5]
        else:
            # If on the home page, fetch 2 latest notifications from each app
            for app in app_names:
                latest_notifications_by_app[app] = request.user.notifications.filter(app_name=app).order_by('-created_at')[:2]

    return {
        "unread_count": unread_count,
        "recent_unread_notifications": recent_unread_notifications,
        "unread_message_count": unread_message_count,
        "recent_unread_messages": recent_unread_messages,
        "latest_notifications_by_app": latest_notifications_by_app if not current_app_name else None,
    }
