# ============================================================
# exceptions.py — Custom Exception Handler
# ============================================================
# WHY: DRF's default exception handler returns inconsistent formats:
#   - Field errors:      {"username": ["This field is required."]}
#   - Non-field errors:  {"detail": "Authentication credentials were not provided."}
#   - Our custom errors: {"error": "Portfolio already exists"}
#
# Clients have to handle 3 different shapes. This handler normalizes
# all errors into one consistent structure:
#   {
#     "status_code": 400,
#     "errors": {
#       "username": ["This field is required."],
#       "detail": "Not authenticated."
#     }
#   }
#
# HOW DRF CALLS THIS:
#   When any exception is raised inside a view (ValidationError,
#   PermissionDenied, NotAuthenticated, NotFound, etc.), DRF catches
#   it in dispatch() and calls EXCEPTION_HANDLER(exc, context).
#   Whatever this function returns becomes the HTTP response.
#   If it returns None, DRF re-raises the exception as a 500.
# ============================================================

from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    # Call DRF's default handler first to get the standard response.
    # This handles all built-in exceptions (ValidationError, NotFound, etc.)
    response = exception_handler(exc, context)

    if response is not None:
        # Wrap the response data in a consistent envelope.
        # response.data is whatever DRF's default handler produced.
        response.data = {
            "status_code": response.status_code,
            "errors": response.data,
        }

    return response
