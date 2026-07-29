# ============================================================
# PHASE 3: Production-Ready ViewSets
# ============================================================
# Added on top of Phase 2 (ModelViewSet):
#
# 1. PAGINATION
#    WHY: Without pagination, GET /api/projects/ returns ALL projects
#    in one response. At scale this kills performance and memory.
#    HOW: PageNumberPagination is set globally in settings.py.
#    DRF calls paginator.paginate_queryset() inside list() automatically.
#    Response becomes: {"count": N, "next": "...", "results": [...]}
#
# 2. SEARCH FILTER (SearchFilter)
#    WHY: Clients need to find projects by title or tech stack without
#    fetching everything and filtering client-side.
#    HOW: DRF's SearchFilter reads ?search=django from the query string
#    and applies Q(title__icontains=...) | Q(tech_stack__icontains=...)
#    to the queryset before serialization.
#
# 3. ORDERING FILTER (OrderingFilter)
#    WHY: Clients need to sort results (newest first, alphabetical, etc.)
#    HOW: ?ordering=created_at or ?ordering=-title
#    DRF applies .order_by() to the queryset automatically.
#
# 4. DJANGO FILTER BACKEND (DjangoFilterBackend)
#    WHY: Exact field filtering. ?tech_stack=Django returns only Django
#    projects. More precise than SearchFilter's icontains.
#    HOW: filterset_fields defines which fields support exact filtering.
#    DRF applies .filter(tech_stack=...) to the queryset.
#
# 5. CUSTOM PERMISSIONS (IsOwner)
#    WHY: IsAuthenticated only checks token presence. IsOwner checks
#    that the object belongs to the authenticated user.
#    HOW: DRF calls check_object_permissions(request, obj) inside
#    get_object(). If IsOwner.has_object_permission() returns False → 403.
#
# 6. BETTER ERROR RESPONSES
#    WHY: Default DRF errors are inconsistent. Some return lists,
#    some return strings. We standardize via a custom exception handler
#    in settings.py (see config/settings.py).
# ============================================================

from rest_framework import viewsets, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend

from .serializers import RegisterSerializer, PortfolioSerializer, ProjectSerializer
from .models import Portfolio, Project
from .permissions import IsOwner


# ── Auth ────────────────────────────────────────────────────

class RegisterView(APIView):
    """
    POST /api/register/
    Public endpoint. No authentication required.
    Validation is handled entirely by RegisterSerializer.
    """
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Registration successful"},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
    """
    GET /api/me/
    Returns the authenticated user's basic info.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
        })


# ── Portfolio ViewSet ────────────────────────────────────────

class PortfolioViewSet(viewsets.ModelViewSet):
    """
    Handles all CRUD for Portfolio.

    GET    /api/portfolio/        → list (scoped to request.user)
    POST   /api/portfolio/        → create (user injected server-side)
    GET    /api/portfolio/<pk>/   → retrieve
    PUT    /api/portfolio/<pk>/   → update
    PATCH  /api/portfolio/<pk>/   → partial update
    DELETE /api/portfolio/<pk>/   → destroy

    Filters:
      ?search=python     → searches full_name, headline, skills
      ?ordering=full_name → orders results
    """
    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    # SearchFilter: DRF reads ?search= and applies icontains on these fields.
    # OrderingFilter: DRF reads ?ordering= and applies .order_by() on the queryset.
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["full_name", "headline", "skills"]
    ordering_fields = ["full_name", "created_at"]
    # Default ordering: newest portfolio first.
    ordering = ["-created_at"]

    def get_queryset(self):
        # Scope to the authenticated user only.
        # This is the single source of truth for ownership on this ViewSet.
        # All actions (list, retrieve, update, destroy) use this queryset.
        return Portfolio.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # user is injected here — never accepted from the client.
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        # Return 400 before hitting the DB if portfolio already exists.
        # Without this, the OneToOneField constraint raises an IntegrityError
        # which DRF catches as a 400 but with a less clear message.
        if Portfolio.objects.filter(user=request.user).exists():
            return Response(
                {"error": "Portfolio already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Override destroy() to return a message body instead of 204 No Content.
        # 204 is correct per HTTP spec, but some clients expect a JSON body.
        instance = self.get_object()
        instance.delete()
        return Response(
            {"message": "Portfolio deleted successfully"},
            status=status.HTTP_200_OK
        )


# ── Project ViewSet ──────────────────────────────────────────

class ProjectViewSet(viewsets.ModelViewSet):
    """
    Handles all CRUD for Project.

    GET    /api/projects/        → list (scoped to request.user's portfolio)
    POST   /api/projects/        → create (portfolio injected server-side)
    GET    /api/projects/<pk>/   → retrieve
    PUT    /api/projects/<pk>/   → update
    PATCH  /api/projects/<pk>/   → partial update
    DELETE /api/projects/<pk>/   → destroy

    Filters:
      ?search=django         → searches title, description, tech_stack
      ?tech_stack=Django     → exact filter on tech_stack
      ?ordering=-created_at  → newest first
    """
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    # DjangoFilterBackend: exact field filtering via ?field=value
    # SearchFilter: icontains search via ?search=value
    # OrderingFilter: column sorting via ?ordering=field
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["tech_stack"]          # ?tech_stack=Django
    search_fields = ["title", "description", "tech_stack"]  # ?search=portfolio
    ordering_fields = ["title", "created_at"]
    ordering = ["-created_at"]                 # Default: newest first

    def get_queryset(self):
        # JOIN through portfolio to user. This single filter enforces
        # that users only see their own projects across all 6 actions.
        # The ORM generates: SELECT * FROM project
        #   JOIN portfolio ON project.portfolio_id = portfolio.id
        #   WHERE portfolio.user_id = <request.user.id>
        return Project.objects.filter(
            portfolio__user=self.request.user
        ).select_related("portfolio")
        # select_related("portfolio") avoids an extra query when
        # IsOwner checks obj.portfolio.user in has_object_permission().

    def perform_create(self, serializer):
        # Auto-link to the user's portfolio. Client never sends portfolio_id.
        portfolio = Portfolio.objects.filter(user=self.request.user).first()
        if portfolio is None:
            raise ValidationError({"error": "Create a portfolio first."})
        serializer.save(portfolio=portfolio)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {"message": "Project deleted successfully"},
            status=status.HTTP_200_OK
        )
