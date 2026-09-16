"""
FCM (Firebase Cloud Messaging) API endpoints and push notification helper.
Handles device token registration and sending push notifications.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
import logging

from profiles.models import FCMDeviceToken, Notification

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_fcm_token(request):
    """Register or update an FCM device token for the authenticated user."""
    token = request.data.get('token', '').strip()
    platform = request.data.get('platform', 'android').lower()

    if not token:
        return Response({'error': 'FCM token is required.'},
                        status=status.HTTP_400_BAD_REQUEST)

    if platform not in ('android', 'ios', 'web'):
        return Response({'error': 'Platform must be android, ios, or web.'},
                        status=status.HTTP_400_BAD_REQUEST)

    obj, created = FCMDeviceToken.objects.update_or_create(
        token=token,
        defaults={
            'user': request.user,
            'platform': platform,
            'is_active': True,
        }
    )

    # Deactivate any other tokens for this user on the same platform
    # (keeps only the most recent active token per platform)
    FCMDeviceToken.objects.filter(
        user=request.user, platform=platform
    ).exclude(id=obj.id).update(is_active=False)

    return Response({
        'message': 'FCM token registered successfully.',
        'created': created,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unregister_fcm_token(request):
    """Deactivate an FCM device token."""
    token = request.data.get('token', '').strip()
    if not token:
        return Response({'error': 'FCM token is required.'},
                        status=status.HTTP_400_BAD_REQUEST)

    updated = FCMDeviceToken.objects.filter(
        token=token, user=request.user
    ).update(is_active=False)

    return Response({
        'message': 'Token unregistered.' if updated else 'Token not found.',
    })


def send_push_notification(user, title, body, data=None, app_name=None):
    """
    Send an FCM push notification to all active devices of a user.
    Called automatically whenever a Notification object is created.
    Falls back gracefully if Firebase is not configured.
    """
    try:
        import firebase_admin
        from firebase_admin import messaging

        # Check if Firebase is initialized
        if not firebase_admin._apps:
            logger.debug("Firebase not initialized — skipping push notification")
            return

        tokens = list(
            FCMDeviceToken.objects.filter(
                user=user, is_active=True
            ).values_list('token', flat=True)
        )

        if not tokens:
            logger.debug(f"No FCM tokens for user {user.username}")
            return

        notification = messaging.Notification(
            title=title,
            body=body,
        )

        # Build the data payload
        data_payload = {}
        if data:
            data_payload = {k: str(v) for k, v in data.items()}
        if app_name:
            data_payload['app_name'] = app_name

        # Send to each token
        success_count = 0
        for token in tokens:
            try:
                message = messaging.Message(
                    notification=notification,
                    data=data_payload,
                    token=token,
                )
                messaging.send(message)
                success_count += 1
            except messaging.UnregisteredError:
                # Token is no longer valid — deactivate it
                FCMDeviceToken.objects.filter(token=token).update(is_active=False)
                logger.debug(f"Deactivated expired token for {user.username}")
            except Exception as e:
                logger.warning(f"FCM send failed for token: {e}")

        logger.info(f"Push sent to {success_count}/{len(tokens)} devices for {user.username}")

    except ImportError:
        logger.debug("firebase_admin not installed — skipping push")
    except Exception as e:
        logger.warning(f"Push notification error: {e}")


@api_view(['POST'])
@permission_classes([AllowAny])
def test_push_notification(request):
    """
    Test endpoint — sends a push notification to a specific FCM token.
    Use this to test FCM locally from the backend.

    POST /api/my_accounts/test-push/
    Body: {"token": "...", "title": "Test", "body": "Hello!"}
    """
    token = request.data.get('token', '').strip()
    title = request.data.get('title', 'FirePrenair Test')
    body = request.data.get('body', 'This is a test push notification from your local server!')

    if not token:
        return Response({'error': 'FCM token is required.'},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        import firebase_admin
        from firebase_admin import messaging

        if not firebase_admin._apps:
            return Response({
                'error': 'Firebase not initialized. Place fcm_service_account.json in prenair/ root.',
            }, status=status.HTTP_400_BAD_REQUEST)

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=token,
        )
        response = messaging.send(message)
        return Response({
            'message': f'Push notification sent successfully!',
            'message_id': response,
            'title': title,
            'body': body,
        })

    except Exception as e:
        return Response({
            'error': f'Failed to send push: {str(e)}',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
