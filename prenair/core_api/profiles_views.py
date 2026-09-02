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

@method_decorator(csrf_exempt, name='dispatch')
class RegisterUserAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        data = request.data
        full_name = data.get('full_name')
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')
        country = data.get('country', '')
        language = data.get('language', 'en')
        user_timezone = data.get('timezone', 'UTC')
        phone = data.get('phone', '')
        customer_type = data.get('customer_type', '')
        identity_type = data.get('identity_type', '')
        identity_number = data.get('identity_number', '')
        referral_code = data.get('referral_code', '')
        terms_accepted = data.get('agree')
        errors = {}
        if not full_name:
            errors['full_name'] = 'Full Name is required.'
        if not email:
            errors['email'] = 'Email is required.'
        elif CustomUser.objects.filter(email=email).exists():
            errors['email'] = 'An account with this email already exists.'
        if not username:
            errors['username'] = 'Username is required.'
        elif CustomUser.objects.filter(username=username).exists():
            errors['username'] = 'This username is already taken.'
        if not password:
            errors['password'] = 'Password is required.'
        if not terms_accepted:
            errors['terms'] = 'You must accept the Terms of Service and Privacy Policy.'
        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
        if not errors:
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
            'customer_type': customer_type,
            'identity_type': identity_type,
            'identity_number': identity_number,
            'referral_code': referral_code,
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
        send_email(email, '🔒 Verify Your Email - FirePrenair', email_content)
        request.session.save()
        print(request.session.session_key)  # This will print the session ID

        return Response({
            'message': 'A verification code has been sent to your email.',
            'redirect_url': f"{reverse('home')}?verify=true&email={email}",
            'session_id': request.session.session_key,  # Include session key
            'session': request.session
        }, status=status.HTTP_200_OK)
    def get(self, request):
        return Response({'message': 'Send a POST request to register.'}, status=status.HTTP_200_OK)
    
from rest_framework.permissions import AllowAny    
@method_decorator(csrf_exempt, name='dispatch')
class VerifyEmailAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        code = request.data.get('verification_code')
        registration_data = request.session.get('registration_data')
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
        if registration_data['verification_code'] != code:
            return Response(
                {'error': 'Invalid verification code.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        referrer = None
        if registration_data.get('referral_code'):
            referrer = CustomUser.objects.filter(referral_code=registration_data['referral_code']).first()

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
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        del request.session['registration_data']
        return Response(
            {
                'message': 'Your email has been verified, and your account is now active!',
                'redirect_url': reverse('dashboard_home')
            },
            status=status.HTTP_200_OK
        )



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
