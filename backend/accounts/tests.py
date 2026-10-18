"""
accounts/tests.py

Tests for session management, authentication, revocation, and security events.
Run with: python3 manage.py test accounts
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework import status

from .models import UserSession, SecurityEvent
from .views import LoginView, TokenRefreshView
from .session_utils import hash_session_key, generate_session_key, parse_user_agent


UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"


def make_user(username="testuser", password="securepass123", email="test@example.com"):
    return User.objects.create_user(username=username, password=password, email=email)


def login(client, username="testuser", password="securepass123"):
    return client.post("/api/login/", {"username": username, "password": password}, format="json",
                       HTTP_USER_AGENT=UA)


# ── UA Parsing ────────────────────────────────────────────────

class UAParsingTests(TestCase):
    def test_desktop_chrome_linux(self):
        result = parse_user_agent(UA)
        self.assertEqual(result["device_type"], "desktop")
        self.assertIn("Chrome", result["browser"])
        self.assertIn("Linux", result["operating_system"])

    def test_empty_ua(self):
        result = parse_user_agent("")
        self.assertEqual(result["device_type"], "unknown")
        self.assertEqual(result["device_name"], "Unknown Device")

    def test_mobile_ua(self):
        mobile_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1"
        result = parse_user_agent(mobile_ua)
        self.assertEqual(result["device_type"], "mobile")


# ── Login ─────────────────────────────────────────────────────

class LoginTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()

    def test_successful_login_returns_tokens(self):
        resp = login(self.client)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_successful_login_creates_session(self):
        login(self.client)
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 1)

    def test_successful_login_records_security_event(self):
        login(self.client)
        self.assertTrue(SecurityEvent.objects.filter(
            user=self.user, event_type="LOGIN_SUCCESS"
        ).exists())

    def test_failed_login_does_not_create_session(self):
        self.client.post("/api/login/", {"username": "testuser", "password": "wrongpass"}, format="json")
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 0)

    def test_failed_login_returns_401(self):
        resp = self.client.post("/api/login/", {"username": "testuser", "password": "wrong"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_session_has_correct_user(self):
        login(self.client)
        session = UserSession.objects.get(user=self.user)
        self.assertEqual(session.user, self.user)

    def test_session_is_active_after_login(self):
        login(self.client)
        session = UserSession.objects.get(user=self.user)
        self.assertTrue(session.is_active)
        self.assertEqual(session.status, "active")

    def test_tokens_contain_sid_claim(self):
        import base64, json
        resp = login(self.client)
        access = resp.data["access"]
        payload = access.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        decoded = json.loads(base64.b64decode(payload))
        self.assertIn("sid", decoded)

    def test_new_device_event_recorded_on_first_login(self):
        login(self.client)
        self.assertTrue(SecurityEvent.objects.filter(
            user=self.user, event_type="NEW_DEVICE_OBSERVED"
        ).exists())

    def test_concurrent_logins_create_distinct_sessions(self):
        resp1 = login(self.client)
        resp2 = login(self.client)
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 2)
        self.assertNotEqual(resp1.data["access"], resp2.data["access"])


# ── Token Refresh ─────────────────────────────────────────────

class TokenRefreshTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()
        resp = login(self.client)
        self.access = resp.data["access"]
        self.refresh = resp.data["refresh"]

    def test_refresh_returns_new_access_token(self):
        resp = self.client.post("/api/token/refresh/", {"refresh": self.refresh}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)

    def test_refresh_rejected_after_session_revoked(self):
        session = UserSession.objects.get(user=self.user)
        session.revoked_at = timezone.now()
        session.revocation_reason = "TEST"
        session.save()

        resp = self.client.post("/api/token/refresh/", {"refresh": self.refresh}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rejected_after_session_expired(self):
        session = UserSession.objects.get(user=self.user)
        session.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        session.save()

        resp = self.client.post("/api/token/refresh/", {"refresh": self.refresh}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_with_invalid_token_returns_401(self):
        resp = self.client.post("/api/token/refresh/", {"refresh": "notavalidtoken"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_records_token_refresh_event(self):
        self.client.post("/api/token/refresh/", {"refresh": self.refresh}, format="json")
        self.assertTrue(SecurityEvent.objects.filter(
            user=self.user, event_type="TOKEN_REFRESH"
        ).exists())


# ── Session Authentication ────────────────────────────────────

class SessionAuthenticationTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()
        resp = login(self.client)
        self.access = resp.data["access"]
        self.session = UserSession.objects.get(user=self.user)

    def test_valid_token_accesses_protected_endpoint(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        resp = self.client.get("/api/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_revoked_session_rejects_valid_access_token(self):
        self.session.revoked_at = timezone.now()
        self.session.revocation_reason = "TEST"
        self.session.save()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        resp = self.client.get("/api/me/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_expired_session_rejects_valid_access_token(self):
        self.session.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        self.session.save()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        resp = self.client.get("/api/me/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_token_returns_401(self):
        resp = self.client.get("/api/me/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_missing_sid_rejected(self):
        from rest_framework_simplejwt.tokens import AccessToken
        legacy_token = AccessToken.for_user(self.user)  # No sid claim
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {legacy_token}")
        resp = self.client.get("/api/me/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_invalid_sid_rejected(self):
        from rest_framework_simplejwt.tokens import AccessToken
        bad_token = AccessToken.for_user(self.user)
        bad_token["sid"] = "nonexistent_session_hash_123"
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {bad_token}")
        resp = self.client.get("/api/me/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ── Session Listing ───────────────────────────────────────────

class SessionListTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.user2 = make_user("other", "otherpass123", "other@example.com")
        self.client = APIClient()
        resp = login(self.client)
        self.access = resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def test_list_returns_only_current_user_sessions(self):
        # Login as user2 to create their session
        client2 = APIClient()
        login(client2, "other", "otherpass123")

        resp = self.client.get("/api/sessions/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for s in resp.data["results"]:
            # All returned sessions must belong to self.user
            session = UserSession.objects.get(id=s["id"])
            self.assertEqual(session.user, self.user)

    def test_current_session_is_marked(self):
        resp = self.client.get("/api/sessions/")
        results = resp.data["results"]
        current_sessions = [s for s in results if s["is_current"]]
        self.assertEqual(len(current_sessions), 1)

    def test_revoked_sessions_not_in_list(self):
        session = UserSession.objects.get(user=self.user)
        session.revoked_at = timezone.now()
        session.save()

        # Use a fresh client without credentials since the session is revoked
        fresh_client = APIClient()
        # Login again to get a new valid session
        resp2 = login(fresh_client)
        fresh_client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp2.data['access']}")

        # Revoke the first session via the new session
        resp = fresh_client.get("/api/sessions/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Only the new session should appear (not the revoked one)
        session_ids = [str(s["id"]) for s in resp.data["results"]]
        self.assertNotIn(str(session.id), session_ids)

    def test_other_user_cannot_retrieve_session(self):
        session = UserSession.objects.get(user=self.user)
        client2 = APIClient()
        resp2 = login(client2, "other", "otherpass123")
        client2.credentials(HTTP_AUTHORIZATION=f"Bearer {resp2.data['access']}")

        resp = client2.get(f"/api/sessions/{session.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ── Session Revocation ────────────────────────────────────────

class SessionRevocationTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()
        resp = login(self.client)
        self.access = resp.data["access"]
        self.refresh = resp.data["refresh"]
        self.session = UserSession.objects.get(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def test_revoke_own_session(self):
        resp = self.client.post(f"/api/sessions/{self.session.id}/revoke/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.session.refresh_from_db()
        self.assertIsNotNone(self.session.revoked_at)

    def test_revoke_records_security_event(self):
        self.client.post(f"/api/sessions/{self.session.id}/revoke/")
        self.assertTrue(SecurityEvent.objects.filter(
            user=self.user, event_type="SESSION_REVOKED"
        ).exists())

    def test_cannot_revoke_other_users_session(self):
        user2 = make_user("other2", "otherpass123", "other2@example.com")
        client2 = APIClient()
        resp2 = login(client2, "other2", "otherpass123")
        client2.credentials(HTTP_AUTHORIZATION=f"Bearer {resp2.data['access']}")

        # user2 tries to revoke user1's session
        resp = client2.post(f"/api/sessions/{self.session.id}/revoke/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.session.refresh_from_db()
        self.assertIsNone(self.session.revoked_at)

    def test_revoke_others_preserves_current_session(self):
        # Create a second session for same user
        client2 = APIClient()
        login(client2, "testuser", "securepass123")
        self.assertEqual(UserSession.objects.filter(user=self.user, revoked_at__isnull=True).count(), 2)

        resp = self.client.post("/api/sessions/revoke-others/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        active = UserSession.objects.filter(user=self.user, revoked_at__isnull=True)
        self.assertEqual(active.count(), 1)
        self.assertEqual(str(active.first().id), str(self.session.id))

    def test_revoke_others_records_event(self):
        client2 = APIClient()
        login(client2, "testuser", "securepass123")
        self.client.post("/api/sessions/revoke-others/")
        self.assertTrue(SecurityEvent.objects.filter(
            user=self.user, event_type="SESSION_REVOKE_OTHERS"
        ).exists())


# ── Logout ────────────────────────────────────────────────────

class LogoutTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()
        resp = login(self.client)
        self.access = resp.data["access"]
        self.refresh = resp.data["refresh"]
        self.session = UserSession.objects.get(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def test_logout_revokes_session(self):
        self.client.post("/api/logout/")
        self.session.refresh_from_db()
        self.assertIsNotNone(self.session.revoked_at)
        self.assertEqual(self.session.revocation_reason, "USER_LOGOUT")

    def test_logout_records_event(self):
        self.client.post("/api/logout/")
        self.assertTrue(SecurityEvent.objects.filter(
            user=self.user, event_type="LOGOUT"
        ).exists())

    def test_access_token_rejected_after_logout(self):
        self.client.post("/api/logout/")
        resp = self.client.get("/api/me/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rejected_after_logout(self):
        self.client.post("/api/logout/")
        resp = self.client.post("/api/token/refresh/", {"refresh": self.refresh}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ── Security Events ───────────────────────────────────────────

class SecurityEventTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()
        resp = login(self.client)
        self.access = resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def test_list_returns_only_own_events(self):
        user2 = make_user("other3", "otherpass123", "other3@example.com")
        client2 = APIClient()
        login(client2, "other3", "otherpass123")

        resp = self.client.get("/api/security-events/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for e in resp.data["results"]:
            event = SecurityEvent.objects.get(id=e["id"])
            self.assertEqual(event.user, self.user)

    def test_events_do_not_expose_tokens(self):
        resp = self.client.get("/api/security-events/")
        for e in resp.data["results"]:
            self.assertNotIn("token", str(e).lower())
            self.assertNotIn("session_key", str(e).lower())


# ── Existing Functionality Preserved ─────────────────────────

class ExistingFunctionalityTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client = APIClient()
        resp = login(self.client)
        self.access = resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def test_register_still_works(self):
        resp = self.client.post("/api/register/", {
            "username": "newuser", "email": "new@example.com", "password": "newpass123"
        }, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_me_endpoint_still_works(self):
        resp = self.client.get("/api/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["username"], "testuser")

    def test_portfolio_endpoint_accessible(self):
        resp = self.client.get("/api/portfolio/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_projects_endpoint_accessible(self):
        resp = self.client.get("/api/projects/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
