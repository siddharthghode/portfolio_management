"""
accounts/session_utils.py

Utilities for session creation, UA parsing, and security event recording.
No raw tokens or secrets are stored — only a SHA-256 hash of the session key.
"""

import hashlib
import secrets
from django.utils import timezone
from django.conf import settings


# ── UA Parsing ───────────────────────────────────────────────

def parse_user_agent(ua_string, client_browser=None):
    """
    Parse a User-Agent string into structured device metadata.
    Returns a dict with device_type, browser, operating_system, device_name.
    Detects Brave when client_browser is passed.
    """
    if not ua_string:
        device_name = "Unknown Device"
        if client_browser and client_browser.lower() == "brave":
            device_name = "Brave"
        return {
            "device_type": "unknown",
            "browser": "Brave" if client_browser and client_browser.lower() == "brave" else "",
            "operating_system": "",
            "device_name": device_name,
        }
    try:
        import user_agents
        ua = user_agents.parse(ua_string)

        if ua.is_mobile:
            device_type = "mobile"
        elif ua.is_tablet:
            device_type = "tablet"
        elif ua.is_pc:
            device_type = "desktop"
        else:
            device_type = "unknown"

        browser = ua.browser.family or ""
        if ua.browser.version_string:
            # Only major version to avoid noise on new-device detection
            major = ua.browser.version_string.split(".")[0]
            browser = f"{browser} {major}".strip()

        # Brave intentionally spoofs Chrome's UA header for anti-fingerprinting.
        # If client verified Brave via navigator.brave.isBrave(), reflect it accurately.
        if client_browser and client_browser.lower() == "brave":
            if "Chrome" in browser:
                browser = browser.replace("Chrome", "Brave")
            else:
                browser = f"Brave {browser}".strip()

        os_name = ua.os.family or ""
        if ua.os.version_string:
            os_name = f"{os_name} {ua.os.version_string}".strip()

        device_name = f"{browser} on {ua.os.family}" if browser and ua.os.family else (browser or ua.os.family or "Unknown Device")

        return {
            "device_type": device_type,
            "browser": browser[:100],
            "operating_system": os_name[:100],
            "device_name": device_name[:200],
        }
    except Exception:
        return {
            "device_type": "unknown",
            "browser": "",
            "operating_system": "",
            "device_name": "Unknown Device",
        }


# ── Session Key ──────────────────────────────────────────────

def generate_session_key():
    """Generate a cryptographically secure random session key (raw, 32 bytes hex)."""
    return secrets.token_hex(32)


def hash_session_key(raw_key):
    """SHA-256 hash of the raw session key. Only the hash is stored in the DB."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


# ── IP Extraction ────────────────────────────────────────────

def get_client_ip(request):
    """
    Extract client IP from request.
    Reads X-Forwarded-For only if TRUST_PROXY_HEADERS is set in settings.
    Falls back to REMOTE_ADDR.
    """
    if getattr(settings, "TRUST_PROXY_HEADERS", False):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


# ── Session Creation ─────────────────────────────────────────

def create_session(user, request, refresh_token_lifetime):
    """
    Create a UserSession record for a successful login.
    Returns (session, raw_session_key).
    The raw_session_key is embedded in the JWT claim — never stored.
    """
    from accounts.models import UserSession

    ua_string = request.META.get("HTTP_USER_AGENT", "")[:500]
    client_browser = request.META.get("HTTP_X_CLIENT_BROWSER", "")
    ua_data = parse_user_agent(ua_string, client_browser=client_browser)
    ip = get_client_ip(request)
    raw_key = generate_session_key()
    key_hash = hash_session_key(raw_key)

    session = UserSession.objects.create(
        user=user,
        session_key_hash=key_hash,
        ip_address=ip,
        user_agent=ua_string,
        expires_at=timezone.now() + refresh_token_lifetime,
        **ua_data,
    )
    return session, raw_key


# ── New Device Detection ─────────────────────────────────────

def is_new_device(user, ua_data, ip):
    """
    Compare current login signals against previous sessions.
    Returns True if this combination of OS + device_type has not been seen before.
    Deliberately coarse — avoids false positives from browser version bumps.
    """
    from accounts.models import UserSession
    seen = UserSession.objects.filter(
        user=user,
        operating_system__icontains=ua_data["operating_system"].split(" ")[0] if ua_data["operating_system"] else "",
        device_type=ua_data["device_type"],
    ).exists()
    return not seen


# ── Security Event Recording ─────────────────────────────────

def record_event(user, event_type, request=None, session=None, detail=""):
    """Record a security event. Never raises — failures are silent to avoid blocking auth."""
    from accounts.models import SecurityEvent
    try:
        ip = get_client_ip(request) if request else None
        ua = request.META.get("HTTP_USER_AGENT", "")[:500] if request else ""
        SecurityEvent.objects.create(
            user=user,
            event_type=event_type,
            session=session,
            ip_address=ip,
            user_agent=ua,
            detail=detail[:300],
        )
    except Exception:
        pass
