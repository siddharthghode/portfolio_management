# ============================================================
# PHASE 3: Serializers with validation improvements
# ============================================================
# BEFORE: Serializers had no field-level validation. A user could
# register with a 1-character password, submit an empty bio, or
# provide a duplicate username — the DB or Django's auth would
# raise cryptic errors instead of clean API responses.
#
# AFTER: Each serializer validates its own fields explicitly.
# DRF calls validate_<field>() automatically during is_valid().
# validate() (no field suffix) is called for cross-field validation.
#
# HOW DRF VALIDATION WORKS INTERNALLY:
#   serializer.is_valid() calls run_validators() → field.validate()
#   → validate_<fieldname>() → validate() in that order.
#   Any ValidationError raised becomes a key in serializer.errors.
#   The view's create()/update() never runs if validation fails.
# ============================================================

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Portfolio, Project


class RegisterSerializer(serializers.ModelSerializer):
    # write_only=True: password is accepted on input but never returned
    # in responses. Without this, the hashed password would be exposed.
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def validate_username(self, value):
        # Explicit duplicate check with a clean error message.
        # Without this, Django raises a DB IntegrityError which DRF
        # catches and returns as a generic "unique" constraint message.
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
        # Use set_password() to hash the password properly.
        # Never store raw passwords.
        user = User(
            username=validated_data["username"],
            email=validated_data["email"]
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


class PortfolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portfolio
        fields = [
            "id",
            "full_name",
            "headline",
            "bio",
            "skills",
            "github",
            "linkedin",
            "resume",
            "profile_image",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_full_name(self, value):
        # Strip whitespace and enforce minimum length.
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Full name must be at least 2 characters.")
        return value

    def validate_github(self, value):
        # URLField already validates URL format, but we add a domain check
        # so users don't submit arbitrary URLs in the github field.
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
            "id",
            "title",
            "description",
            "tech_stack",
            "github_link",
            "live_demo",
            "image",
            "created_at",
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
