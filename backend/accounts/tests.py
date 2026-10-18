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


# ── Phase 5 Regression Tests: Multi-Browser Sessions ──────────

class MultiBrowserSessionRegressionTests(TestCase):
    """
    Dedicated regression test suite covering all 12 scenarios from Phase 5:
    1. Logging in once creates one session.
    2. Logging in twice with the same account creates two distinct session IDs.
    3. Both sessions are stored in the database.
    4. The session-list endpoint returns both active sessions.
    5. A second user cannot see the first user's sessions.
    6. Two sessions with identical browser and operating-system metadata remain separate.
    7. Refreshing one session's tokens does not create an unintended duplicate or replace another session.
    8. Revoking one session does not revoke another session.
    9. A revoked session cannot use an existing access token.
    10. Expired and revoked sessions are excluded from the active list.
    11. The existing /api/me/ and protected portfolio/project endpoints continue to work.
    12. The React UI can render multiple sessions from the actual API response format.
    """

    CHROME_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
    FIREFOX_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"

    def setUp(self):
        self.user = make_user("multiuser", "securepass123", "multi@example.com")
        self.other_user = make_user("otheruser", "otherpass123", "otheruser@example.com")
        self.client = APIClient()

    def _login_with_ua(self, user, ua, ip="127.0.0.1"):
        client = APIClient()
        resp = client.post(
            "/api/login/",
            {"username": user.username, "password": "securepass123" if user == self.user else "otherpass123"},
            format="json",
            HTTP_USER_AGENT=ua,
            REMOTE_ADDR=ip,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
        return client, resp.data

    def test_01_logging_in_once_creates_one_session(self):
        client, data = self._login_with_ua(self.user, self.CHROME_UA)
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 1)
        session = UserSession.objects.get(user=self.user)
        self.assertTrue(session.is_active)

    def test_02_logging_in_twice_creates_two_distinct_session_ids(self):
        client1, data1 = self._login_with_ua(self.user, self.CHROME_UA)
        client2, data2 = self._login_with_ua(self.user, self.FIREFOX_UA)

        sessions = UserSession.objects.filter(user=self.user)
        self.assertEqual(sessions.count(), 2)
        session_ids = [str(s.id) for s in sessions]
        self.assertNotEqual(session_ids[0], session_ids[1])
        self.assertNotEqual(data1["access"], data2["access"])

    def test_03_both_sessions_are_stored_in_the_database(self):
        self._login_with_ua(self.user, self.CHROME_UA)
        self._login_with_ua(self.user, self.FIREFOX_UA)

        chrome_sess = UserSession.objects.filter(user=self.user, browser__icontains="Chrome")
        firefox_sess = UserSession.objects.filter(user=self.user, browser__icontains="Firefox")
        self.assertTrue(chrome_sess.exists())
        self.assertTrue(firefox_sess.exists())
        self.assertEqual(UserSession.objects.filter(user=self.user, revoked_at__isnull=True).count(), 2)

    def test_04_session_list_endpoint_returns_both_active_sessions(self):
        client_chrome, data_chrome = self._login_with_ua(self.user, self.CHROME_UA)
        client_firefox, data_firefox = self._login_with_ua(self.user, self.FIREFOX_UA)

        # Chrome calls /api/sessions/
        resp_chrome = client_chrome.get("/api/sessions/")
        self.assertEqual(resp_chrome.status_code, status.HTTP_200_OK)
        results_chrome = resp_chrome.data.get("results", resp_chrome.data)
        self.assertEqual(len(results_chrome), 2)
        current_in_chrome = [s for s in results_chrome if s["is_current"]]
        self.assertEqual(len(current_in_chrome), 1)
        self.assertIn("Chrome", current_in_chrome[0]["device_name"])

        # Firefox calls /api/sessions/
        resp_firefox = client_firefox.get("/api/sessions/")
        self.assertEqual(resp_firefox.status_code, status.HTTP_200_OK)
        results_firefox = resp_firefox.data.get("results", resp_firefox.data)
        self.assertEqual(len(results_firefox), 2)
        current_in_firefox = [s for s in results_firefox if s["is_current"]]
        self.assertEqual(len(current_in_firefox), 1)
        self.assertIn("Firefox", current_in_firefox[0]["device_name"])

    def test_05_second_user_cannot_see_first_users_sessions(self):
        client1, _ = self._login_with_ua(self.user, self.CHROME_UA)
        client2, _ = self._login_with_ua(self.other_user, self.FIREFOX_UA)

        resp2 = client2.get("/api/sessions/")
        results2 = resp2.data.get("results", resp2.data)
        self.assertEqual(len(results2), 1)
        # Verify the returned session belongs strictly to other_user
        session_id = results2[0]["id"]
        self.assertEqual(str(UserSession.objects.get(id=session_id).user.id), str(self.other_user.id))

        # Direct access to user1's session by user2 returns 404
        user1_session = UserSession.objects.filter(user=self.user).first()
        detail_resp = client2.get(f"/api/sessions/{user1_session.id}/")
        self.assertEqual(detail_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_06_two_sessions_with_identical_browser_and_os_metadata_remain_separate(self):
        # Two logins with the exact same Chrome UA and IP
        client1, data1 = self._login_with_ua(self.user, self.CHROME_UA)
        client2, data2 = self._login_with_ua(self.user, self.CHROME_UA)

        sessions = UserSession.objects.filter(user=self.user, revoked_at__isnull=True)
        self.assertEqual(sessions.count(), 2)

        resp = client1.get("/api/sessions/")
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 2)
        self.assertNotEqual(results[0]["id"], results[1]["id"])

    def test_07_refreshing_tokens_preserves_session_identity_and_does_not_duplicate(self):
        client_chrome, data_chrome = self._login_with_ua(self.user, self.CHROME_UA)
        client_firefox, data_firefox = self._login_with_ua(self.user, self.FIREFOX_UA)

        # Refresh Chrome's token
        refresh_resp = client_chrome.post("/api/token/refresh/", {"refresh": data_chrome["refresh"]}, format="json")
        self.assertEqual(refresh_resp.status_code, status.HTTP_200_OK)
        new_access = refresh_resp.data["access"]

        # Verify DB still has exactly 2 sessions
        self.assertEqual(UserSession.objects.filter(user=self.user, revoked_at__isnull=True).count(), 2)

        # Chrome can still access sessions with the new access token
        client_chrome.credentials(HTTP_AUTHORIZATION=f"Bearer {new_access}")
        resp = client_chrome.get("/api/sessions/")
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 2)
        current = [s for s in results if s["is_current"]]
        self.assertEqual(len(current), 1)
        self.assertIn("Chrome", current[0]["device_name"])

    def test_08_revoking_one_session_does_not_revoke_another_session(self):
        client_chrome, data_chrome = self._login_with_ua(self.user, self.CHROME_UA)
        client_firefox, data_firefox = self._login_with_ua(self.user, self.FIREFOX_UA)

        firefox_session = UserSession.objects.filter(user=self.user, browser__icontains="Firefox").first()
        chrome_session = UserSession.objects.filter(user=self.user, browser__icontains="Chrome").first()

        # Chrome revokes Firefox session
        revoke_resp = client_chrome.post(f"/api/sessions/{firefox_session.id}/revoke/")
        self.assertEqual(revoke_resp.status_code, status.HTTP_200_OK)

        firefox_session.refresh_from_db()
        chrome_session.refresh_from_db()

        self.assertFalse(firefox_session.is_active)
        self.assertIsNotNone(firefox_session.revoked_at)
        self.assertTrue(chrome_session.is_active)
        self.assertIsNone(chrome_session.revoked_at)

    def test_09_revoked_session_cannot_use_existing_access_token(self):
        client_chrome, data_chrome = self._login_with_ua(self.user, self.CHROME_UA)
        client_firefox, data_firefox = self._login_with_ua(self.user, self.FIREFOX_UA)

        firefox_session = UserSession.objects.filter(user=self.user, browser__icontains="Firefox").first()
        # Revoke Firefox session
        client_chrome.post(f"/api/sessions/{firefox_session.id}/revoke/")

        # Firefox's existing access token should now be rejected on protected endpoints
        resp = client_firefox.get("/api/me/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

        # Chrome's token continues to work
        resp_chrome = client_chrome.get("/api/me/")
        self.assertEqual(resp_chrome.status_code, status.HTTP_200_OK)

    def test_10_expired_and_revoked_sessions_excluded_from_active_list(self):
        client, _ = self._login_with_ua(self.user, self.CHROME_UA)
        # Create an expired session manually
        from .session_utils import generate_session_key, hash_session_key
        UserSession.objects.create(
            user=self.user,
            session_key_hash=hash_session_key(generate_session_key()),
            device_name="Expired Phone",
            device_type="mobile",
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )
        # Create a revoked session
        revoked = UserSession.objects.create(
            user=self.user,
            session_key_hash=hash_session_key(generate_session_key()),
            device_name="Revoked Tablet",
            device_type="tablet",
            expires_at=timezone.now() + timezone.timedelta(days=7),
            revoked_at=timezone.now(),
        )

        resp = client.get("/api/sessions/")
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 1)
        self.assertIn("Chrome", results[0]["device_name"])

    def test_11_existing_me_and_portfolio_endpoints_continue_to_work(self):
        client, _ = self._login_with_ua(self.user, self.CHROME_UA)

        me_resp = client.get("/api/me/")
        self.assertEqual(me_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(me_resp.data["username"], "multiuser")

        portfolio_resp = client.get("/api/portfolio/")
        self.assertEqual(portfolio_resp.status_code, status.HTTP_200_OK)

        projects_resp = client.get("/api/projects/")
        self.assertEqual(projects_resp.status_code, status.HTTP_200_OK)

    def test_12_react_ui_response_contract_and_structure(self):
        client_chrome, _ = self._login_with_ua(self.user, self.CHROME_UA)
        client_firefox, _ = self._login_with_ua(self.user, self.FIREFOX_UA)

        resp = client_chrome.get("/api/sessions/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Handle both paginated or array structures as React UI does
        data = resp.data
        results = data if isinstance(data, list) else data.get("results")
        self.assertIsNotNone(results)
        self.assertEqual(len(results), 2)

        # Verify all fields expected by ActiveSessionsPage.jsx are present in each item
        expected_fields = {
            "id", "device_name", "device_type", "browser",
            "operating_system", "ip_address", "created_at",
            "last_seen_at", "is_current", "status"
        }
        for item in results:
            self.assertTrue(expected_fields.issubset(set(item.keys())),
                            f"Missing fields: {expected_fields - set(item.keys())}")
            self.assertIn(item["status"], ["active", "revoked", "expired"])
            self.assertIsInstance(item["is_current"], bool)

