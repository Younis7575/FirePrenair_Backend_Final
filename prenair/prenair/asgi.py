import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prenair.settings')

django_asgi_app = get_asgi_application()

from commu_prenair import routing
from prenair.ws_auth import JWTAuthMiddleware

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    # AuthMiddlewareStack reads the session cookie, which the website
    # has; JWTAuthMiddleware then reads ?token= for the mobile app,
    # which does not. Without the second one every socket the app
    # opened arrived as AnonymousUser.
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            JWTAuthMiddleware(URLRouter(routing.websocket_urlpatterns))
        )
    ),
})
