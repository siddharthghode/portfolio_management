from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Portfolio, Project, UserSession, SecurityEvent


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email is required.")
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def create(self, validated_data):
        user = User(
            username=validated_data["username"],
            email=validated_data["email"]
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    has_portfolio = serializers.SerializerMethodField()
    projects_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "date_joined", "last_login", "has_portfolio", "projects_count",
        ]
        read_only_fields = [
            "id", "username", "date_joined", "last_login",
            "has_portfolio", "projects_count",
        ]

    def get_has_portfolio(self, obj):
        return hasattr(obj, "portfolio")

    def get_projects_count(self, obj):
        if hasattr(obj, "portfolio"):
            return obj.portfolio.projects.count()
        return 0

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email is required.")
        user = self.instance
        if user and User.objects.filter(email=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("This email is already in use by another account.")
        return value


class PortfolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portfolio
        fields = [
            "id", "full_name", "headline", "bio", "skills",
            "github", "linkedin", "resume", "profile_image",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_full_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Full name must be at least 2 characters.")
        return value

    def validate_github(self, value):
        if value and "github.com" not in value:
            raise serializers.ValidationError("Must be a valid GitHub URL.")
        return value

    def validate_linkedin(self, value):
        if value and "linkedin.com" not in value:
            raise serializers.ValidationError("Must be a valid LinkedIn URL.")
        return value


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            "id", "title", "description", "tech_stack",
            "github_link", "live_demo", "image", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_title(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters.")
        return value

    def validate_tech_stack(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Tech stack cannot be empty.")
        return value


class UserSessionSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields = [
            "id", "device_name", "device_type", "browser",
            "operating_system", "ip_address", "created_at",
            "last_seen_at", "expires_at", "is_current", "status",
        ]
        read_only_fields = fields

    def get_is_current(self, obj):
        request = self.context.get("request")
        if request and hasattr(request, "user_session"):
            return str(obj.id) == str(request.user_session.id)
        return False

    def get_status(self, obj):
        return obj.status


class SecurityEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityEvent
        fields = ["id", "event_type", "ip_address", "detail", "created_at"]
        read_only_fields = fields
