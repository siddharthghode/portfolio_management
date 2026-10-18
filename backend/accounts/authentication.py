"""
accounts/authentication.py

SessionJWTAuthentication extends SimpleJWT's JWTAuthentication.

On every authenticated request it:
1. Validates the JWT signature and expiry (standard SimpleJWT behavior).
2. Reads the `sid` claim (session key hash) from the token payload.
3. Looks up the UserSession by that hash.
4. Rejects the request if the session is revoked or expired.
5. Throttles last_seen_at updates to avoid a DB write on every request.

Security/performance tradeoff:
- Access tokens are short-lived (2h). A revoked session's access token
  remains technically valid until expiry but is rejected here via DB lookup.
- last_seen_at is updated at most once per SESSION_ACTIVITY_THROTTLE_SECONDS
  (default 60s) to avoid hammering the DB on every request.
- If the session row is missing (deleted), the request is rejected.
"""

from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.exceptions import AuthenticationFailed

THROTTLE_SECONDS = getattr(settings, "SESSION_ACTIVITY_THROTTLE_SECONDS", 60)


class SessionJWTAuthentication(JWTAuthentication):

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, validated_token = result

        # Extract session key hash from JWT claim
        sid = validated_token.get("sid")
        if not sid:
            raise InvalidToken("Token missing session identifier.")

        # Validate session in DB
        from accounts.models import UserSession
        try:
            session = UserSession.objects.get(session_key_hash=sid)
        except UserSession.DoesNotExist:
            raise AuthenticationFailed("Session not found or has been revoked.")

        if not session.is_active:
            raise AuthenticationFailed("Session has been revoked or expired.")

        if session.user_id != user.id:
            raise AuthenticationFailed("Session does not belong to this user.")

        # If client verified as Brave but session was recorded with Chrome UA, update session
        client_browser = request.META.get("HTTP_X_CLIENT_BROWSER", "")
        if client_browser and client_browser.lower() == "brave" and "Chrome" in session.browser:
            session.browser = session.browser.replace("Chrome", "Brave")
            session.device_name = session.device_name.replace("Chrome", "Brave")
            UserSession.objects.filter(pk=session.pk).update(
                browser=session.browser,
                device_name=session.device_name,
            )

        # Throttled last_seen_at update
        now = timezone.now()
        if session.last_seen_at < now - timedelta(seconds=THROTTLE_SECONDS):
            UserSession.objects.filter(pk=session.pk).update(last_seen_at=now)

        # Attach session to request for use in views
        request.user_session = session
        return user, validated_token
