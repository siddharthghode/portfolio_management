from django.db import models
from django.contrib.auth.models import User


class Portfolio(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="portfolio"
    )

    full_name = models.CharField(max_length=100)
    headline = models.CharField(max_length=150,default="")

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