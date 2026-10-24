from django.urls import re_path
from . import consumers
from profiles.consumers import NotificationConsumer

websocket_urlpatterns = [
    # `api/` is optional: nginx rewrites /api/ws/ to /ws/, but accept both so a
    # direct hit works too.
    re_path(r'^(?:api/)?ws/chat/(?P<slug>[-\w]+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'^(?:api/)?ws/notifications/$', NotificationConsumer.as_asgi()),

]
