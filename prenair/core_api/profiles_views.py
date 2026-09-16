import re
from importlib import import_module
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login,logout
from django.contrib import messages
from profiles.models import CustomUser
from rest_framework.exceptions import AuthenticationFailed
from profiles.models import *
from home.models import *
from django.shortcuts import redirect
from work_prenair.views import send_email
import string
from django.utils.crypto import get_random_string
from django.conf import settings
from django.urls import reverse
from rest_framework.permissions import AllowAny
from django.contrib.sessions.models import Session
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
import stripe
# @method_decorator(csrf_exempt, name='dispatch')
class LoginUserAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self,request):
        email = request.data.get('email')
        password = request.data.get('password')
        if not email or not password:
            return Response({"error": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)
        errors = {}

        if not email:
            errors['email'] = 'Email is required.'
        if not password:
            errors['password'] = 'Password is required.'
        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(request, username=email, password=password)

        if user is None:
            raise AuthenticationFailed("Invalid email or password.")
        
        login(request, user)

        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        next_url = request.data.get('next', None)
        response_data = {
            'message': 'You have successfully logged in.',
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'username': user.username,
                'role': user.role,
                'slug': user.slug,
                'profile_pic': user.profile_pic.url if user.profile_pic else None,
                'is_edu_instructor': user.is_edu_instructor,
                'is_work_freelancer': user.is_work_freelancer,
                'is_digi_seller': user.is_digi_seller,
                'is_corporate_client': user.is_corporate_client,
                'is_staff': user.is_staff,
                'country': user.country,
                'language': user.language,
                'timezone': user.timezone,
            },
            'tokens': {
                'accessToken': access_token,
                'refreshToken': str(refresh)
            }
        }

        if next_url:
            response_data['next_url'] = next_url

        return Response(response_data, status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class LogoutUserAPIView(APIView):
    def post(self, request, *args, **kwargs):
        logout(request)
        return Response({
            'message': 'You have successfully logged out.'
        }, status=status.HTTP_200_OK)

def _as_bool(value, default=False):
    """Registration flags arrive as JSON booleans from the app and as the
    strings 'true'/'on' from the web form. Accept either."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('true', '1', 'yes', 'on', 'agree')


def _registration_session(request):
    """Returns (session_store, registration_data).

    The web flow carries the session in a cookie. Mobile clients can't rely on
    a cookie jar, so they replay the `session_id` handed back by /register/
    (in the body, or the X-Session-Id header) and we open that store directly.
    """
    data = request.session.get('registration_data')
    if data:
        return request.session, data

    key = (
        request.data.get('session_id')
        or request.headers.get('X-Session-Id')
        or ''
    )
    key = str(key).strip()
    if key:
        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore(session_key=key)
        data = store.get('registration_data')
        if data:
            return store, data

    return request.session, None


def _auth_payload(user):
    """The same user + tokens shape LoginUserAPIView returns, so a client can
    treat a completed verification exactly like a fresh login."""
    refresh = RefreshToken.for_user(user)
    return {
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'username': user.username,
            'role': user.role,
            'slug': user.slug,
            'profile_pic': user.profile_pic.url if user.profile_pic else None,
            'is_edu_instructor': user.is_edu_instructor,
            'is_work_freelancer': user.is_work_freelancer,
            'is_digi_seller': user.is_digi_seller,
            'is_corporate_client': user.is_corporate_client,
            'is_staff': user.is_staff,
            'country': user.country,
            'language': user.language,
            'timezone': user.timezone,
        },
        'tokens': {
            'accessToken': str(refresh.access_token),
            'refreshToken': str(refresh),
        },
    }


@method_decorator(csrf_exempt, name='dispatch')
class RegisterUserAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        full_name = (data.get('full_name') or '').strip()
        email = (data.get('email') or '').strip()
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        country = (data.get('country') or '').strip()
        language = (data.get('language') or 'en').strip()
        user_timezone = (data.get('timezone') or 'UTC').strip()
        phone = (data.get('phone') or '').strip()
        age_confirmed = _as_bool(data.get('age_confirmed'), default=True)
        customer_type = (data.get('customer_type') or '').strip()
        identity_type = (data.get('identity_type') or '').strip()
        identity_number = (data.get('identity_number') or '').strip()
        referral_code = (data.get('referral_code') or '').strip()
        terms_accepted = _as_bool(data.get('agree_terms')) or data.get('agree') == 'agree'
        privacy_accepted = _as_bool(data.get('agree_privacy'))
        errors = {}

        # Full Name validation
        if not full_name:
            errors['full_name'] = 'Full Name is required.'
        elif len(full_name) < 2:
            errors['full_name'] = 'Full name must be at least 2 characters.'

        # Email validation
        if not email:
            errors['email'] = 'Email is required.'
        elif not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            errors['email'] = 'Please enter a valid email address.'
        elif CustomUser.objects.filter(email__iexact=email).exists():
            errors['email'] = 'An account with this email already exists.'

        # Username validation
        if not username:
            errors['username'] = 'Username is required.'
        elif len(username) < 3:
            errors['username'] = 'Username must be at least 3 characters.'
        elif not re.match(r'^[a-zA-Z0-9_]+$', username):
            errors['username'] = 'Username can only contain letters, numbers, and underscores.'
        elif CustomUser.objects.filter(username__iexact=username).exists():
            errors['username'] = 'This username is already taken.'

        # Password validation (strong)
        if not password:
            errors['password'] = 'Password is required.'
        else:
            if len(password) < 8:
                errors['password'] = 'Password must be at least 8 characters long.'
            elif not re.search(r'[A-Z]', password):
                errors['password'] = 'Password must contain at least one uppercase letter.'
            elif not re.search(r'[a-z]', password):
                errors['password'] = 'Password must contain at least one lowercase letter.'
            elif not re.search(r'[0-9]', password):
                errors['password'] = 'Password must contain at least one number.'
            elif not re.search(r'[^A-Za-z0-9]', password):
                errors['password'] = 'Password must contain at least one special character.'

        # Country required
        if not country:
            errors['country'] = 'Country/Region is required.'

        # Language required
        if not language:
            errors['language'] = 'Preferred language is required.'

        # Timezone required
        if not user_timezone:
            errors['timezone'] = 'Timezone is required.'

        # Phone E.164 format (optional but must be valid if provided)
        if phone and not re.match(r'^\+\d{1,14}$', phone):
            errors['phone'] = 'Please enter a valid phone number in E.164 format (e.g., +1234567890).'

        # Optional KYC fields must still match the values the model accepts,
        # otherwise create_user() stores something no form can render back.
        valid_customer_types = dict(CustomUser.CUSTOMER_TYPE)
        if customer_type and customer_type not in valid_customer_types:
            errors['customer_type'] = 'Please choose a valid customer type.'

        valid_identity_types = dict(CustomUser.IDENTITY_TYPE_CHOICES)
        if identity_type and identity_type not in valid_identity_types:
            errors['identity_type'] = 'Please choose a valid identity type.'
        if identity_type and not identity_number:
            errors['identity_number'] = 'Identity number is required for the selected identity type.'

        # Terms & Privacy
        if not terms_accepted:
            errors['terms'] = 'You must agree to the Terms of Use.'
        if not privacy_accepted:
            errors['privacy'] = 'You must agree to the Privacy Policy.'

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        verification_code = get_random_string(6, allowed_chars=string.ascii_uppercase + string.digits)

        request.session['registration_data'] = {
            'full_name': full_name,
            'email': email,
            'username': username,
            'password': password,
            'country': country,
            'language': language,
            'timezone': user_timezone,
            'phone': phone,
            'age_confirmed': age_confirmed,
            'customer_type': customer_type,
            'identity_type': identity_type,
            'identity_number': identity_number,
            'referral_code': referral_code,
            'terms_accepted': terms_accepted,
            'privacy_accepted': privacy_accepted,
            'verification_code': verification_code,
        }
        request.session.set_expiry(3600)

        email_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
            <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                <!-- Header -->
                <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                    <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                </div>

                <!-- Body -->
                <div style="padding: 20px;">
                    <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🔒 Verify Your Email</h2>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {full_name},</p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                        Thank you for signing up on <strong>FirePrenair</strong>! 🚀 We're excited to have you on board. To complete your registration, please verify your email using the code below:
                    </p>
                    <div style="text-align: center; margin: 20px 0;">
                        <h2 style="background-color: #f9fafb; padding: 10px 20px; display: inline-block; color: #1e3a8a; border: 1px solid #ddd; border-radius: 8px;">{verification_code}</h2>
                    </div>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                        This code is valid for <strong>1 hour</strong>. Please make sure to complete your registration before the code expires.
                    </p>
                    <p style="color: #333; font-size: 16px; line-height: 1.6;">If you have any questions, feel free to reach out to our support team.</p>
                </div>

                <!-- Footer -->
                <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                    <p style="margin: 0; font-size: 14px;">Thank you for joining FirePrenair! 🚀</p>
                </div>
            </div>
        </body>
        </html>
        """
        try:
            send_email(email, '🔒 Verify Your Email - FirePrenair', email_content)
        except Exception as exc:
            # The code lives in the session either way — a mail outage
            # shouldn't wipe out a registration the user just completed.
            print(f'Registration: could not send verification email to {email}: {exc}')

        request.session.save()

        # Always on the server console, so a dev can complete the flow when
        # mail delivery is unavailable.
        print(f'[REGISTER] verification code for {email}: {verification_code}')

        payload = {
            'message': 'A verification code has been sent to your email.',
            'redirect_url': f"{reverse('home')}?verify=true&email={email}",
            'email': email,
            'session_id': request.session.session_key,
            'expires_in': 3600,
        }
        # Only echoed back while DEBUG is on — never in production, where it
        # would hand the code to anyone who can call this endpoint.
        if settings.DEBUG:
            payload['debug_verification_code'] = verification_code

        return Response(payload, status=status.HTTP_200_OK)

    def get(self, request):
        return Response({'message': 'Send a POST request to register.'}, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class VerifyEmailAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        code = (request.data.get('verification_code') or '').strip().upper()
        email = (request.data.get('email') or '').strip()
        session_store, registration_data = _registration_session(request)

        if not code:
            return Response(
                {'error': 'verification_code is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not registration_data:
            return Response(
                {'error': 'Verification code has expired or email mismatch. Please register again.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if email and registration_data.get('email', '').lower() != email.lower():
            return Response(
                {'error': 'Verification code has expired or email mismatch. Please register again.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if registration_data.get('verification_code') != code:
            return Response(
                {'error': 'Invalid verification code. Please try again.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # The window between /register/ and /verify-email/ is long enough for
        # someone else to claim the same email or username.
        if CustomUser.objects.filter(email__iexact=registration_data['email']).exists():
            return Response(
                {'error': 'An account with this email already exists. Please sign in instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if CustomUser.objects.filter(username__iexact=registration_data['username']).exists():
            return Response(
                {'error': 'This username is already taken. Please register again with a different username.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        referrer = None
        if registration_data.get('referral_code'):
            referrer = CustomUser.objects.filter(
                referral_code=registration_data['referral_code']
            ).first()

        try:
            user = CustomUser.objects.create_user(
                name=registration_data['full_name'],
                email=registration_data['email'],
                username=registration_data['username'],
                password=registration_data['password'],
                country=registration_data.get('country', ''),
                language=registration_data.get('language', 'en'),
                timezone=registration_data.get('timezone', 'UTC'),
                phone_no=registration_data.get('phone', ''),
                customer_type=registration_data.get('customer_type') or None,
                identity_type=registration_data.get('identity_type') or None,
                identity_number=registration_data.get('identity_number') or None,
                referred_by=referrer,
                profile_pic='profile_pics/avatar.jpg',
            )
            user.save()
        except Exception as exc:
            print(f'Verification: could not create account: {exc}')
            return Response(
                {'error': f'An error occurred while creating your account: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        # Consume the code so it can't be replayed.
        try:
            del session_store['registration_data']
            session_store.save()
        except KeyError:
            pass

        welcome_email_content = """
        <html>
        <body>
            <div style="text-align: center; padding: 40px; font-family: Arial, sans-serif;">
                <h1 style="color: #ff6f61;">Welcome to FirePrenair! 🎉</h1>
                <p>Your account has been successfully verified and activated.</p>
                <p>Start your entrepreneurial journey with us today!</p>
            </div>
        </body>
        </html>
        """
        try:
            send_email(user.email, '🎉 Welcome to FirePrenair!', welcome_email_content)
        except Exception as exc:
            print(f'Verification: could not send welcome email to {user.email}: {exc}')

        payload = {
            'message': 'Your email has been verified, and your account is now active!',
            'redirect_url': reverse('dashboard_home'),
        }
        # Hand back tokens so the client lands on the dashboard signed in,
        # exactly like the web flow does.
        payload.update(_auth_payload(user))
        return Response(payload, status=status.HTTP_200_OK)



stripe.api_key = settings.STRIPE_SECRET_KEY
class CreateCheckoutSessionAPIView(APIView):
    permission_classes = [IsAuthenticated]  # Ensures only logged-in users can access

    def post(self, request, plan_id):
        pricing_plan = get_object_or_404(PricingPlan, id=plan_id)
        subscription_type = request.data.get("subscription_type", "monthly")

        if subscription_type not in ["monthly", "annual"]:
            subscription_type = "monthly"

        promo_codes = Promo.objects.filter(active=True)
        discounts = [{'coupon': promo.code} for promo in promo_codes]

        try:
            customer_id = request.user.stripe_customer_id

            price_id = (
                pricing_plan.price_monthly if subscription_type == "monthly" else pricing_plan.price_annual
            )

            session_params = {
                'customer': customer_id,
                'payment_method_types': ['card'],
                'line_items': [
                    {
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': pricing_plan.title,
                                'description': pricing_plan.description,
                            },
                            'unit_amount': int(price_id * 100),  # Convert price to cents
                            'recurring': {
                                'interval': 'month' if subscription_type == "monthly" else 'year',
                            },
                        },
                        'quantity': 1,
                    },
                ],
                'mode': 'subscription',
                'success_url': request.build_absolute_uri('/dashboard/'),
                'cancel_url': request.build_absolute_uri('/pricing/'), 
                'metadata': {
                    'plan_id': pricing_plan.id,
                    'subscription_type': subscription_type,
                },
            }

            if discounts:
                session_params['discounts'] = discounts

            checkout_session = stripe.checkout.Session.create(**session_params)
            return Response({"checkout_url": checkout_session.url}, status=200)

        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)


ENDPOINT_SECRET = settings.STRIPE_WEBHOOK_SECRET_SUBSCRIBE
@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookAPIView(APIView):
    authentication_classes = []  # Disable authentication for webhooks
    permission_classes = []      # Disable permission checks for webhooks

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, ENDPOINT_SECRET
            )
        except ValueError:
            return Response({'error': 'Invalid payload'}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)

        event_type = event['type']
        event_data = event['data']['object']

        if event_type == 'checkout.session.completed':
            handle_checkout_session_completed(event_data)
        elif event_type == 'invoice.payment_succeeded':
            handle_payment_succeeded(event_data)
        elif event_type == 'customer.subscription.updated':
            handle_subscription_updated(event_data)
        elif event_type == 'customer.subscription.deleted':
            handle_subscription_deleted(event_data)
        else:
            return Response({'status': f'Unhandled event type: {event_type}'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 'success'}, status=status.HTTP_200_OK)
    

def handle_checkout_session_completed(session):
    customer_email = session.get('customer_details', {}).get('email')
    customer_id = session['customer']
    subscription_id = session['subscription']
    plan_id = session['metadata'].get('plan_id')
    subscription_type = session['metadata'].get('subscription_type')
    plan = PricingPlan.objects.get(id=plan_id)
    user = CustomUser.objects.get(email=customer_email)

    user_plan, created = UserPlan.objects.update_or_create(
        user=user,
        stripe_subscription_id=subscription_id,
        defaults={
            'plan': plan,
            'is_active': True,
            'start_date': now(),
            'end_date': now() + timedelta(days=30 if subscription_type == "monthly" else 365),
            'type': subscription_type,
        }
    )


def handle_payment_succeeded(invoice):
    subscription_id = invoice['subscription']
    user_plan = UserPlan.objects.filter(stripe_subscription_id=subscription_id).first()
    
    if user_plan:
        if user_plan.type == "monthly":
            days = 30
        else:
            days = 365

        user_plan.end_date = now() + timedelta(days=days)
        user_plan.is_active = True
        user_plan.save()


def handle_subscription_updated(subscription):
    subscription_id = subscription['id']
    status = subscription['status']

    user_plan = UserPlan.objects.filter(stripe_subscription_id=subscription_id).first()
    if user_plan:
        user_plan.status = status
        user_plan.is_active = status == "active"
        user_plan.save()


def handle_subscription_deleted(subscription):
    subscription_id = subscription['id']

    user_plan = UserPlan.objects.filter(stripe_subscription_id=subscription_id).first()
    if user_plan:
        user_plan.is_active = False
        user_plan.status = "canceled"
        user_plan.save()


class StripeBillingPortalAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            session = stripe.billing_portal.Session.create(
                customer=request.user.stripe_customer_id,
                return_url=request.build_absolute_uri('/dashboard/'),
            )
            return Response({'billing_portal_url': session.url}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

from django.utils.translation import activate

class UpdateLanguageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        lang = request.data.get("language")
        next_url = request.data.get("next") or request.META.get("HTTP_REFERER", "/")

        if not lang:
            return Response({'error': 'language not provided.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update the user's language preference
        request.user.language = lang
        request.user.save()

        # Activate and set the language in session
        activate(lang)
        request.session["django_language"] = lang

        return Response({
            'message': 'Language updated successfully!',
            'next_url': next_url
        }, status=status.HTTP_200_OK)
