from django.utils import timezone
from django.db import transaction

from rest_framework import viewsets, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, NotFound
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings

from .serializers import (
    RegisterSerializer, UserSerializer,
    PortfolioSerializer, ProjectSerializer,
    UserSessionSerializer, SecurityEventSerializer,
)
from .models import Portfolio, Project, UserSession, SecurityEvent
from .permissions import IsOwner
from .tokens import SessionRefreshToken
from .session_utils import (
    create_session, is_new_device, record_event,
)


# ── Auth ──────────────────────────────────────────────────────

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Registration successful"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    POST /api/login/
    Creates a server-side UserSession and embeds the session key hash
    in both access and refresh tokens as the `sid` claim.
    Returns { access, refresh } — same contract as before.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from django.contrib.auth import authenticate
        username = request.data.get("username", "")
        password = request.data.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is None:
            record_event(
                user=_get_user_by_username(username),
                event_type="LOGIN_FAILED",
                request=request,
                detail=f"Failed login attempt for username: {username}",
            )
            return Response(
                {"detail": "No active account found with the given credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Detect new device BEFORE creating session (compare against prior sessions)
        from .session_utils import parse_user_agent, get_client_ip
        ua_data = parse_user_agent(request.META.get("HTTP_USER_AGENT", ""))
        ip = get_client_ip(request)
        new_device = is_new_device(user, ua_data, ip)

        # Create session and tokens atomically — no usable credentials if this fails
        with transaction.atomic():
            session, raw_key = create_session(
                user=user,
                request=request,
                refresh_token_lifetime=jwt_settings.REFRESH_TOKEN_LIFETIME,
            )
            refresh = SessionRefreshToken.for_session(user, session.session_key_hash)
            access = refresh.access_token

        # Update Django's last_login
        from django.contrib.auth.models import User as AuthUser
        AuthUser.objects.filter(pk=user.pk).update(last_login=timezone.now())

        if new_device:
            record_event(user, "NEW_DEVICE_OBSERVED", request, session,
                         detail=f"New device: {session.device_name}")

        record_event(user, "LOGIN_SUCCESS", request, session,
                     detail=session.device_name)

        return Response({
            "access": str(access),
            "refresh": str(refresh),
        })


class TokenRefreshView(APIView):
    """
    POST /api/token/refresh/
    Session-aware: validates session is still active before issuing new access token.
    Maintains { access } response shape.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = SessionRefreshToken(refresh_token)
        except TokenError as e:
            _record_refresh_failure(request, str(e))
            return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        sid = token.get("sid")
        if not sid:
            return Response({"detail": "Invalid token."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            session = UserSession.objects.select_related("user").get(session_key_hash=sid)
        except UserSession.DoesNotExist:
            _record_refresh_failure(request, "Session not found")
            return Response({"detail": "Session not found or revoked."}, status=status.HTTP_401_UNAUTHORIZED)

        if not session.is_active:
            record_event(session.user, "REFRESH_REJECTED", request, session,
                         detail=f"Session status: {session.status}")
            return Response({"detail": "Session has been revoked or expired."}, status=status.HTTP_401_UNAUTHORIZED)

        new_access = token.access_token
        new_access["sid"] = sid

        UserSession.objects.filter(pk=session.pk).update(last_refresh_at=timezone.now())
        record_event(session.user, "TOKEN_REFRESH", request, session)

        return Response({"access": str(new_access)})


class LogoutView(APIView):
    """
    POST /api/logout/
    Revokes the current server-side session.
    Frontend calls this before clearing local tokens.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session = getattr(request, "user_session", None)
        if session:
            session.revoked_at = timezone.now()
            session.revocation_reason = "USER_LOGOUT"
            session.save(update_fields=["revoked_at", "revocation_reason"])
            record_event(request.user, "LOGOUT", request, session)
        return Response({"message": "Logged out successfully."})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── Sessions ──────────────────────────────────────────────────

from rest_framework.pagination import PageNumberPagination

class UserSessionPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class UserSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET  /api/sessions/                    list active sessions
    GET  /api/sessions/<uuid>/             retrieve one session
    POST /api/sessions/<uuid>/revoke/      revoke a session
    POST /api/sessions/revoke-others/      revoke all except current
    """
    serializer_class = UserSessionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = UserSessionPagination

    def get_queryset(self):
        return UserSession.objects.filter(
            user=self.request.user,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).order_by("-last_seen_at")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    @action(detail=True, methods=["post"], url_path="revoke")
    def revoke(self, request, pk=None):
        try:
            session = UserSession.objects.get(pk=pk, user=request.user)
        except UserSession.DoesNotExist:
            raise NotFound("Session not found.")

        if not session.is_active:
            return Response({"detail": "Session is already inactive."}, status=status.HTTP_400_BAD_REQUEST)

        is_current = (
            hasattr(request, "user_session") and
            str(request.user_session.id) == str(session.id)
        )

        session.revoked_at = timezone.now()
        session.revocation_reason = "USER_REVOKED"
        session.save(update_fields=["revoked_at", "revocation_reason"])

        record_event(request.user, "SESSION_REVOKED", request, session,
                     detail=f"Revoked: {session.device_name}")

        return Response({
            "message": "Session revoked.",
            "was_current": is_current,
        })

    @action(detail=False, methods=["post"], url_path="revoke-others")
    def revoke_others(self, request):
        current_session = getattr(request, "user_session", None)

        with transaction.atomic():
            qs = UserSession.objects.filter(
                user=request.user,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            if current_session:
                qs = qs.exclude(pk=current_session.pk)

            count = qs.count()
            qs.update(
                revoked_at=timezone.now(),
                revocation_reason="REVOKE_OTHERS",
            )

        record_event(request.user, "SESSION_REVOKE_OTHERS", request, current_session,
                     detail=f"Revoked {count} other session(s)")

        return Response({"message": f"Revoked {count} other session(s)."})


# ── Security Events ───────────────────────────────────────────

class SecurityEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/security-events/         paginated list for current user
    GET /api/security-events/<uuid>/  single event
    """
    serializer_class = SecurityEventSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ["-created_at"]

    def get_queryset(self):
        # user__isnull=False excludes anonymous refresh-failure events
        return SecurityEvent.objects.filter(user=self.request.user)


# ── Portfolio ViewSet ─────────────────────────────────────────

class PortfolioViewSet(viewsets.ModelViewSet):
    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["full_name", "headline", "skills"]
    ordering_fields = ["full_name", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        if Portfolio.objects.filter(user=request.user).exists():
            return Response({"error": "Portfolio already exists"}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Portfolio deleted successfully"}, status=status.HTTP_200_OK)


# ── Project ViewSet ───────────────────────────────────────────

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["tech_stack"]
    search_fields = ["title", "description", "tech_stack"]
    ordering_fields = ["title", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Project.objects.filter(
            portfolio__user=self.request.user
        ).select_related("portfolio")

    def perform_create(self, serializer):
        portfolio = Portfolio.objects.filter(user=self.request.user).first()
        if portfolio is None:
            raise ValidationError({"error": "Create a portfolio first."})
        serializer.save(portfolio=portfolio)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Project deleted successfully"}, status=status.HTTP_200_OK)


# ── Helpers ───────────────────────────────────────────────────

def _get_user_by_username(username):
    from django.contrib.auth.models import User
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None


def _record_refresh_failure(request, detail):
    """Best-effort anonymous refresh failure event. user is nullable."""
    try:
        from .session_utils import get_client_ip
        SecurityEvent.objects.create(
            user=None,
            event_type="REFRESH_REJECTED",
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            detail=detail[:300],
        )
    except Exception:
        pass
