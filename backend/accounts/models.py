import uuid
from django.db import models
from django.contrib.auth.models import User


class Portfolio(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="portfolio"
    )

    full_name = models.CharField(max_length=100)
    headline = models.CharField(max_length=150, default="")

    bio = models.TextField()
    skills = models.TextField()

    github = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)

    resume = models.FileField(
        upload_to="resumes/",
        blank=True,
        null=True
    )

    profile_image = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name


class Project(models.Model):
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="projects"
    )

    title = models.CharField(max_length=150)
    description = models.TextField()
    tech_stack = models.CharField(max_length=255)
    github_link = models.URLField(blank=True)
    live_demo = models.URLField(blank=True)

    image = models.ImageField(
        upload_to="projects/",
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class UserSession(models.Model):
    DEVICE_TYPES = [
        ("desktop", "Desktop"),
        ("mobile", "Mobile"),
        ("tablet", "Tablet"),
        ("unknown", "Unknown"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sessions"
    )

    # Secure random token stored as a hash — used to identify this session
    # in the JWT claim. Never stored raw.
    session_key_hash = models.CharField(max_length=64, unique=True, db_index=True)

    device_name = models.CharField(max_length=200, default="Unknown Device")
    device_type = models.CharField(max_length=10, choices=DEVICE_TYPES, default="unknown")
    browser = models.CharField(max_length=100, blank=True)
    operating_system = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revocation_reason = models.CharField(max_length=100, blank=True)
    last_refresh_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "revoked_at", "expires_at"]),
        ]

    @property
    def is_active(self):
        from django.utils import timezone
        return self.revoked_at is None and self.expires_at > timezone.now()

    @property
    def status(self):
        from django.utils import timezone
        if self.revoked_at:
            return "revoked"
        if self.expires_at <= timezone.now():
            return "expired"
        return "active"

    def __str__(self):
        return f"{self.user.username} — {self.device_name}"


class SecurityEvent(models.Model):
    EVENT_TYPES = [
        ("LOGIN_SUCCESS", "Login Success"),
        ("LOGIN_FAILED", "Login Failed"),
        ("LOGOUT", "Logout"),
        ("SESSION_REVOKED", "Session Revoked"),
        ("SESSION_REVOKE_OTHERS", "Revoke Other Sessions"),
        ("NEW_DEVICE_OBSERVED", "New Device Observed"),
        ("TOKEN_REFRESH", "Token Refreshed"),
        ("REFRESH_REJECTED", "Refresh Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="security_events",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES, db_index=True)
    session = models.ForeignKey(
        UserSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    detail = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} — {self.event_type}"