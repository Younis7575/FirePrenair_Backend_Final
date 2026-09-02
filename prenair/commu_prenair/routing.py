from django.urls import re_path
from . import consumers
from profiles.consumers import NotificationConsumer

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<slug>[-\w]+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),

]
