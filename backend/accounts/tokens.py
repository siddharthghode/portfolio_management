"""
accounts/tokens.py

Custom SimpleJWT token classes that carry a `sid` claim.
`sid` is the SHA-256 hash of the session key — it identifies the server-side
UserSession row without exposing any secret material in the token payload.
"""

from rest_framework_simplejwt.tokens import AccessToken, RefreshToken


class SessionAccessToken(AccessToken):
    """Access token that carries the session key hash as the `sid` claim."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def for_session(cls, user, session_key_hash):
        token = cls.for_user(user)
        token["sid"] = session_key_hash
        return token


class SessionRefreshToken(RefreshToken):
    """Refresh token that carries the session key hash as the `sid` claim."""

    access_token_class = SessionAccessToken

    @classmethod
    def for_session(cls, user, session_key_hash):
        token = cls.for_user(user)
        token["sid"] = session_key_hash
        return token
