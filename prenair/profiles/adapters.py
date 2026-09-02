import logging
import re

import requests
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        If a local account already exists with the same email, connect this
        Google identity to that user instead of failing or creating a duplicate.
        """
        if sociallogin.is_existing:
            return

        email = self._get_email(sociallogin)
        if not email:
            logger.warning("pre_social_login: could not resolve email for social login")
            return

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return

        sociallogin.connect(request, user)

    def save_user(self, request, sociallogin, form=None):
        """
        Fill CustomUser fields before the default flow runs (password, username,
        sociallogin.save, EmailAddress setup).
        """
        user = sociallogin.user
        if not user.pk:
            extra = sociallogin.account.extra_data or {}
            email = extra.get("email") or self.get_email_from_token(sociallogin)
            name = (extra.get("name") or "").strip()
            if email:
                user.email = email
            if name:
                user.name = name
            base = email.split("@")[0] if email else (sociallogin.account.uid or "user")
            base = re.sub(r"[^a-zA-Z0-9_]", "_", base)[:50] or "user"
            user.username = self._unique_username(base)
        return super().save_user(request, sociallogin, form)

    def get_email_from_token(self, sociallogin):
        """
        Prefer provider extra_data; fall back to Google userinfo using the token.
        """
        extra = sociallogin.account.extra_data or {}
        if extra.get("email"):
            return extra["email"]

        try:
            token = sociallogin.token
            if not token:
                return None

            if sociallogin.account.provider != "google":
                logger.warning(
                    "get_email_from_token: unsupported provider %s",
                    sociallogin.account.provider,
                )
                return None

            userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            headers = {"Authorization": f"Bearer {token.token}"}
            response = requests.get(userinfo_url, headers=headers, timeout=15)
            if response.status_code == 200:
                return response.json().get("email")
            logger.warning(
                "get_email_from_token: userinfo failed with status %s",
                response.status_code,
            )
        except Exception as exc:
            logger.exception("get_email_from_token: %s", exc)
        return None

    def _get_email(self, sociallogin):
        extra = sociallogin.account.extra_data or {}
        email = extra.get("email")
        if email:
            return email
        return self.get_email_from_token(sociallogin)

    def _unique_username(self, base: str) -> str:
        candidate = base[:150]
        if not User.objects.filter(username=candidate).exists():
            return candidate
        n = 0
        while True:
            n += 1
            suffix = f"_{n}"
            candidate = f"{base[: 150 - len(suffix)]}{suffix}"
            if not User.objects.filter(username=candidate).exists():
                return candidate
