"""WebSocket authentication for clients that carry a JWT, not a session cookie.

`AuthMiddlewareStack` only knows how to read a session cookie. The Flutter app
authenticates with a JWT and has no cookie, so every socket it opened arrived as
AnonymousUser: NotificationConsumer dropped the connection without a word and
ChatConsumer accepted it and then failed trying to save AnonymousUser. The app's
own comment said the token was "passed as a query param for token-authenticated
Channels middleware" -- that middleware was never written.

Browsers cannot set headers on a WebSocket handshake, so the token travels as a
query parameter, which is the usual arrangement for Channels. Note that query
strings are easy to leak into access logs; nginx's `access_log off` is set for
static only, so consider a short-lived token if this ever carries more weight.

Falls back to the session, so the website keeps working unchanged.
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _user_from_token(raw_token):
    # Imported lazily: this module is imported from asgi.py before the app
    # registry is necessarily ready.
    from rest_framework_simplejwt.exceptions import TokenError
    from rest_framework_simplejwt.tokens import AccessToken
    from django.contrib.auth import get_user_model

    try:
        token = AccessToken(raw_token)
        return get_user_model().objects.get(id=token["user_id"])
    except (TokenError, KeyError, get_user_model().DoesNotExist):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """Set scope['user'] from ?token=<JWT> when the session did not supply one."""

    async def __call__(self, scope, receive, send):
        existing = scope.get("user")
        if existing is not None and existing.is_authenticated:
            return await super().__call__(scope, receive, send)

        params = parse_qs((scope.get("query_string") or b"").decode())
        raw_token = (params.get("token") or [None])[0]
        if raw_token:
            scope["user"] = await _user_from_token(raw_token)

        return await super().__call__(scope, receive, send)
