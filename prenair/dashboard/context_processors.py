from django.conf import settings


def digiprenair_upload_context(request):
    """Expose whether to use direct S3 upload for Digiprenair (when USE_S3_STORAGE=True)."""
    return {
        "USE_S3_UPLOAD": getattr(settings, "USE_S3_STORAGE", False),
    }
