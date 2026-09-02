from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from .models import *
from home.models import *
from django.conf import settings
import stripe
from django.http import JsonResponse
from django.utils.timezone import now
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string
import string
from work_prenair.views import send_email
from django.urls import reverse
from django.template.loader import render_to_string
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from home.views import get_homepage_context
import json
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from urllib.parse import urlencode
from django.utils.html import escape
import re


# Create your views here.

def login_user(request):
    if request.method == 'POST':
        raw_login = (request.POST.get('email') or '').strip()
        password = request.POST.get('password')

        errors = {}
        if not raw_login:
            errors['email'] = 'Email or username is required.'
        if not password:
            errors['password'] = 'Password is required.'

        login_key = raw_login
        if not errors and raw_login and '@' not in raw_login:
            try:
                u = CustomUser.objects.get(username__iexact=raw_login)
                login_key = u.email
            except CustomUser.DoesNotExist:
                pass

        if not errors:
            user = authenticate(request, username=login_key, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'You have successfully logged in.')
                next_url = request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('dashboard_home')
            else:
                errors['invalid'] = 'Invalid email or password.'

        ctx = get_homepage_context(request)
        ctx.update({
            'login_errors': errors,
            'login_values': {
                'email': raw_login,
                'has_login_errors': bool(errors),
            },
        })
        return render(request, 'home/homepage.html', ctx)

    return render(request, 'home/homepage.html', get_homepage_context(request))


def _themed_email_wrapper(title, subtitle, body_html):
    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f4f4f4;">
<div style="max-width:600px;margin:0 auto;font-family:Arial,Helvetica,sans-serif;">
<div style="background:linear-gradient(135deg,#ff6f61 0%,#ff8e53 100%);padding:32px;text-align:center;">
<div style="background-color:#1e3a8a;padding:16px;text-align:center;">
<img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair" style="max-width:140px;">
</div>
<h1 style="color:#fff;font-size:26px;margin:20px 0 8px;font-weight:700;">{title}</h1>
<p style="color:rgba(255,255,255,0.92);font-size:15px;margin:0;">{subtitle}</p>
</div>
<div style="padding:32px;background:#fff;">
{body_html}
</div>
<div style="background:linear-gradient(135deg,#2c3e50 0%,#1a2530 100%);color:rgba(255,255,255,0.85);text-align:center;padding:22px;font-size:13px;">
<p style="margin:0;">&copy; FirePrenair. All rights reserved.</p>
</div>
</div>
</body></html>"""


def _password_reset_link(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    tok = default_token_generator.make_token(user)
    q = urlencode({'recover': 'reset', 'uid': uid, 'token': tok})
    return request.build_absolute_uri(f'/?{q}')


@require_POST
def forgot_password_api(request):
    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        data = {}
    email = (data.get('email') or request.POST.get('email') or '').strip().lower()
    if not email:
        return JsonResponse({'success': False, 'error': 'Please enter your email address.'}, status=400)
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return JsonResponse({'success': True, 'message': 'If an account exists for that email, you will receive password reset instructions shortly.'})
    try:
        user = CustomUser.objects.get(email__iexact=email)
    except CustomUser.DoesNotExist:
        return JsonResponse({'success': True, 'message': 'If an account exists for that email, you will receive password reset instructions shortly.'})
    reset_url = _password_reset_link(request, user)
    inner = f"""
<p style="color:#333;font-size:16px;line-height:1.6;margin:0 0 20px;">Hi <strong>{escape(user.name or 'there')}</strong>,</p>
<p style="color:#333;font-size:16px;line-height:1.6;margin:0 0 24px;">We received a request to reset your FirePrenair password. Click the button below to choose a new password. This link expires for your security.</p>
<div style="text-align:center;margin:28px 0;">
<a href="{reset_url}" style="display:inline-block;background:linear-gradient(135deg,#ff6f61 0%,#ff8e53 100%);color:#fff;text-decoration:none;padding:14px 32px;border-radius:999px;font-weight:700;font-size:15px;">Reset your password</a>
</div>
<p style="color:#666;font-size:14px;line-height:1.5;margin:0 0 16px;">If the button does not work, copy and paste this link into your browser:</p>
<p style="word-break:break-all;color:#ff6f61;font-size:13px;margin:0 0 24px;">{reset_url}</p>
<p style="color:#666;font-size:14px;margin:0;">If you did not request this, you can ignore this email.</p>
"""
    html = _themed_email_wrapper('Reset your password', 'Secure your FirePrenair account', inner)
    plain = f"Reset your FirePrenair password:\n{reset_url}\n"
    send_email(user.email, 'Reset your FirePrenair password', html, plain)
    return JsonResponse({'success': True, 'message': 'If an account exists for that email, you will receive password reset instructions shortly.'})


@require_POST
def forgot_username_api(request):
    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        data = {}
    email = (data.get('email') or request.POST.get('email') or '').strip().lower()
    if not email:
        return JsonResponse({'success': False, 'error': 'Please enter your email address.'}, status=400)
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return JsonResponse({'success': True, 'message': 'If an account exists for that email, we sent your username there.'})
    try:
        user = CustomUser.objects.get(email__iexact=email)
    except CustomUser.DoesNotExist:
        return JsonResponse({'success': True, 'message': 'If an account exists for that email, we sent your username there.'})
    inner = f"""
<p style="color:#333;font-size:16px;line-height:1.6;margin:0 0 20px;">Hi <strong>{escape(user.name or 'there')}</strong>,</p>
<p style="color:#333;font-size:16px;line-height:1.6;margin:0 0 16px;">You asked for a reminder of your FirePrenair username.</p>
<div style="background:linear-gradient(135deg,#f8f9fa 0%,#e9ecef 100%);padding:24px;border-radius:14px;text-align:center;border:2px dashed #dee2e6;margin:24px 0;">
<p style="color:#666;font-size:13px;margin:0 0 10px;text-transform:uppercase;letter-spacing:1px;">Your username</p>
<p style="color:#ff6f61;font-size:22px;font-weight:700;margin:0;word-break:break-all;">{escape(user.username)}</p>
</div>
<p style="color:#666;font-size:14px;margin:0;">Sign in with your username or email and your password.</p>
"""
    html = _themed_email_wrapper('Your FirePrenair username', 'Here is what you requested', inner)
    send_email(user.email, 'Your FirePrenair username', html, f"Your FirePrenair username: {user.username}\n")
    return JsonResponse({'success': True, 'message': 'If an account exists for that email, we sent your username there.'})


@require_POST
def password_reset_confirm_api(request):
    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        data = {}
    uid = (data.get('uid') or request.POST.get('uid') or '').strip()
    token = (data.get('token') or request.POST.get('token') or '').strip()
    password1 = data.get('password1') or request.POST.get('password1') or ''
    password2 = data.get('password2') or request.POST.get('password2') or ''
    if not uid or not token:
        return JsonResponse({'success': False, 'error': 'This reset link is invalid or has expired.'}, status=400)
    if not password1 or not password2:
        return JsonResponse({'success': False, 'error': 'Please enter and confirm your new password.'}, status=400)
    if password1 != password2:
        return JsonResponse({'success': False, 'error': 'The two passwords do not match.'}, status=400)
    try:
        pk = force_str(urlsafe_base64_decode(uid))
        user = CustomUser.objects.get(pk=pk)
    except Exception:
        return JsonResponse({'success': False, 'error': 'This reset link is invalid or has expired.'}, status=400)
    if not default_token_generator.check_token(user, token):
        return JsonResponse({'success': False, 'error': 'This reset link is invalid or has expired.'}, status=400)
    try:
        validate_password(password1, user)
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': ' '.join(e.messages)}, status=400)
    user.set_password(password1)
    user.save()
    return JsonResponse({'success': True, 'message': 'Your password has been updated. You can sign in now.'})


import base64
from django.core.files.base import ContentFile
import uuid

def register_user(request):
    if request.method == 'POST':
        # Get form data from hidden fields
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        country = request.POST.get('country')
        language = request.POST.get('language')
        user_timezone = request.POST.get('timezone')
        phone = request.POST.get('phone')
        age_confirmed = request.POST.get('age_confirmed', 'true') == 'true'
        profile_photo_data = request.POST.get('profile_photo')
        background_photo_data = request.POST.get('background_photo')
        customer_type = request.POST.get('customer_type')
        identity_type = request.POST.get('identity_type')
        identity_number = request.POST.get('identity_number')
        agree_terms = request.POST.get('agree_terms') == 'true'
        agree_privacy = request.POST.get('agree_privacy') == 'true'
        referral_code = request.POST.get('referral_code')
        errors = {}
        
        # Validate required fields
        if not full_name:
            errors['full_name'] = 'Full Name is required.'
        elif len(full_name.strip()) < 2:
            errors['full_name'] = 'Full name must be at least 2 characters.'
        
        if not email:
            errors['email'] = 'Email is required.'
        elif not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            errors['email'] = 'Please enter a valid email address.'
        elif CustomUser.objects.filter(email=email).exists():
            errors['email'] = 'An account with this email already exists.'
        
        if not username:
            errors['username'] = 'Username is required.'
        elif len(username.strip()) < 3:
            errors['username'] = 'Username must be at least 3 characters.'
        elif not re.match(r'^[a-zA-Z0-9_]+$', username):
            errors['username'] = 'Username can only contain letters, numbers, and underscores.'
        elif CustomUser.objects.filter(username=username).exists():
            errors['username'] = 'This username is already taken.'
        
        if not password:
            errors['password'] = 'Password is required.'
        else:
            # Password strength validation
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
        
        if not country:
            errors['country'] = 'Country/Region is required.'
        
        if not language:
            errors['language'] = 'Preferred language is required.'
        
        if not user_timezone:
            errors['timezone'] = 'Timezone is required.'
        
        # Validate phone format if provided
        if phone:
            # Basic E.164 validation
            if not re.match(r'^\+\d{1,15}$', phone):
                errors['phone'] = 'Please enter a valid phone number in E.164 format (e.g., +1234567890).'
        
        if not agree_terms:
            errors['terms'] = 'You must agree to the Terms of Use.'
        
        if not agree_privacy:
            errors['privacy'] = 'You must agree to the Privacy Policy.'

        print(errors)

        # Handle referral code
        referrer = None
        if referral_code:
            try:
                referrer = CustomUser.objects.get(referral_code=referral_code)
            except CustomUser.DoesNotExist:
                pass

        if not errors:
            verification_code = get_random_string(6, allowed_chars=string.ascii_uppercase + string.digits)
            
            registration_data = {
                'full_name': full_name,
                'email': email,
                'username': username,
                'password': password,
                'country': country,
                'language': language,
                'timezone': user_timezone,
                'phone': phone,
                'age_confirmed': age_confirmed,
                'profile_photo_data': profile_photo_data,
                'background_photo_data': background_photo_data,
                'verification_code': verification_code,
                'referrer': referrer.username if referrer else None,
                'terms_accepted': agree_terms,
                'privacy_accepted': agree_privacy,
                'customer_type': customer_type,
                'identity_type': identity_type,
                'identity_number': identity_number,
            }
            
            # Store in session
            request.session['registration_data'] = registration_data
            request.session.set_expiry(3600)  # 1 hour expiry

            # Send verification email
            email_content = f"""
            <html>
            <body style="font-family: 'Poppins', Arial, sans-serif; margin: 0; padding: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <div style="max-width: 600px; margin: 40px auto; background: white; border-radius: 20px; overflow: hidden; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);">
                    <!-- Header -->
                    <div style="background: linear-gradient(135deg, #ff6f61 0%, #ff8e53 100%); padding: 40px; text-align: center;">
                       <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                            <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                        </div>
                        <h1 style="color: white; font-size: 32px; margin-top: 20px; margin-bottom: 10px; font-weight: 700;">Verify Your Email</h1>
                        <p style="color: rgba(255, 255, 255, 0.9); font-size: 16px; margin: 0;">Complete your FirePrenair registration</p>
                    </div>

                    <!-- Body -->
                    <div style="padding: 40px;">
                        <p style="color: #333; font-size: 16px; line-height: 1.6; margin-bottom: 20px;">Hi <strong>{full_name}</strong>,</p>
                        
                        <p style="color: #333; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
                            Thank you for joining <strong style="color: #ff6f61;">FirePrenair</strong>! 🚀 We're excited to have you on board. 
                            To complete your registration and unlock all features, please verify your email using the code below:
                        </p>
                        
                        <!-- Verification Code Box -->
                        <div style="text-align: center; margin: 40px 0;">
                            <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 30px; border-radius: 15px; display: inline-block; border: 2px dashed #dee2e6;">
                                <p style="color: #666; font-size: 14px; margin: 0 0 15px 0; text-transform: uppercase; letter-spacing: 1px;">Verification Code</p>
                                <div style="background: white; padding: 20px 40px; border-radius: 10px; display: inline-block; border: 2px solid #ff6f61;">
                                    <h2 style="color: #ff6f61; font-size: 36px; letter-spacing: 8px; margin: 0; font-weight: 700;">{verification_code}</h2>
                                </div>
                                <p style="color: #666; font-size: 13px; margin: 15px 0 0 0;">
                                    Code expires in <strong style="color: #ff6f61;">1 hour</strong>
                                </p>
                            </div>
                        </div>
                        
                        <p style="color: #333; font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
                            Enter this code on the verification page to activate your account and start your entrepreneurial journey with us.
                        </p>
                        
                        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 30px 0; border-left: 4px solid #ff6f61;">
                            <p style="color: #666; font-size: 14px; margin: 0;">
                                <strong>Tip:</strong> Can't find the email? Check your spam folder or mark our emails as "Not Spam" to ensure you receive future communications.
                            </p>
                        </div>
                        
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">
                            If you have any questions or need assistance, don't hesitate to reach out to our support team at 
                            <a href="mailto:support@fireprenair.com" style="color: #ff6f61; text-decoration: none; font-weight: 600;">support@fireprenair.com</a>.
                        </p>
                        
                        <p style="color: #333; font-size: 16px; line-height: 1.6; margin-top: 30px;">
                            Welcome aboard!<br>
                            <strong>The FirePrenair Team</strong> 🔥
                        </p>
                    </div>

                    <!-- Footer -->
                    <div style="background: linear-gradient(135deg, #2c3e50 0%, #1a2530 100%); color: rgba(255, 255, 255, 0.8); text-align: center; padding: 25px;">
                        <p style="margin: 0 0 10px 0; font-size: 14px;">
                            &copy; 2024 FirePrenair. All rights reserved.
                        </p>
                        <p style="margin: 0; font-size: 12px; opacity: 0.7;">
                            Building the next generation of entrepreneurs.
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """

            send_email(email, '🔐 Verify Your Email - Complete Your FirePrenair Registration', email_content)

            # AJAX: return JSON so frontend can show verify step in popup without reload
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accepts('application/json'):
                return JsonResponse({'success': True, 'email': email})

            messages.success(request, 'A verification code has been sent to your email. Please check your inbox.')
            return redirect(f"{reverse('home')}?verify=true&email={email}")

        # If there are errors, return JSON for AJAX or render form
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accepts('application/json'):
            return JsonResponse({'success': False, 'errors': errors}, status=400)

        return render(request, 'home/homepage.html', {
            'errors': errors,
            'values': {
                'full_name': full_name,
                'email': email,
                'username': username,
                'country': country,
                'language': language,
                'timezone': user_timezone,
                'phone': phone,
                'has_errors': bool(errors),
            },
            'show_register_popup': True,
        })

    return render(request, 'home/homepage.html')


def verify_email(request):
    # Email from GET (traditional) or POST (AJAX)
    email = request.GET.get('email', '') or request.POST.get('email', '')

    if request.method == 'POST':
        code = request.POST.get('verification_code', '').strip()
        registration_data = request.session.get('registration_data')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accepts('application/json')

        if not registration_data:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Verification code has expired. Please register again.'}, status=400)
            messages.error(request, 'Verification code has expired or email mismatch. Please register again.')
            return redirect('home')

        if registration_data['verification_code'] != code:
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Invalid verification code. Please try again.'}, status=400)
            messages.error(request, 'Invalid verification code. Please try again.')
            return redirect(f"{reverse('home')}?verify=true&email={email}")

        try:
            # Create user with the password from registration data
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
                profile_pic='profile_pics/avatar.jpg',
                referred_by=CustomUser.objects.filter(
                    username=registration_data['referrer']
                ).first() if registration_data.get('referrer') else None,
            )
            
            # Handle profile photo if uploaded
            if registration_data.get('profile_photo_data'):
                try:
                    # Decode base64 image and save
                    format, imgstr = registration_data['profile_photo_data'].split(';base64,')
                    ext = format.split('/')[-1]
                    
                    # Generate filename
                    filename = f"profile_pics/{user.username}_{uuid.uuid4().hex[:8]}.{ext}"
                    
                    # Decode and save image
                    data = ContentFile(base64.b64decode(imgstr), name=filename)
                    user.profile_pic.save(filename, data, save=True)
                except Exception as e:
                    print(f"Error saving profile photo: {e}")

            if registration_data.get('background_photo_data'):
                try:
                    format, imgstr = registration_data['background_photo_data'].split(';base64,')
                    ext = format.split('/')[-1]
                    filename = f"digiprenair_avatar/{user.username}_{uuid.uuid4().hex[:8]}_bg.{ext}"
                    data = ContentFile(base64.b64decode(imgstr), name=filename)
                    user.digi_cover_photo.save(filename, data, save=True)
                except Exception as e:
                    print(f"Error saving background photo: {e}")

            user.save()
            
            # Clean up session
            if 'registration_data' in request.session:
                del request.session['registration_data']
            
            # Log the user in
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            # Send welcome email
            welcome_email_content = f"""
            <html>
            <body>
                <div style="text-align: center; padding: 40px;">
                    <h1 style="color: #ff6f61;">Welcome to FirePrenair! 🎉</h1>
                    <p>Your account has been successfully verified and activated.</p>
                    <p>Start your entrepreneurial journey with us today!</p>
                </div>
            </body>
            </html>
            """
            send_email(user.email, '🎉 Welcome to FirePrenair!', welcome_email_content)

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accepts('application/json'):
                return JsonResponse({'success': True, 'redirect_url': reverse('dashboard_home')})

            messages.success(request, 'Your email has been verified! Welcome to FirePrenair!')
            return redirect('dashboard_home')

        except Exception as e:
            print(f"Error creating user account: {e}")
            err_msg = str(e)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accepts('application/json'):
                return JsonResponse({'success': False, 'error': f'An error occurred: {err_msg}'}, status=500)
            messages.error(request, f'An error occurred while creating your account: {err_msg}')
            return redirect('home')

    return render(request, 'home/verify_email.html', {'email': email})



@require_http_methods(["POST"])
def check_username_availability(request):
    """
    AJAX endpoint to check if username is available
    """
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        
        if not username:
            return JsonResponse({
                'available': False,
                'message': 'Username is required'
            })
        
        if len(username) < 3:
            return JsonResponse({
                'available': False,
                'message': 'Username must be at least 3 characters'
            })
        
        if not username.replace('_', '').isalnum():
            return JsonResponse({
                'available': False,
                'message': 'Username can only contain letters, numbers, and underscores'
            })
        
        # Check if username exists
        exists = CustomUser.objects.filter(username=username).exists()
        
        if exists:
            return JsonResponse({
                'available': False,
                'message': 'This username is already taken'
            })
        
        return JsonResponse({
            'available': True,
            'message': 'Username is available'
        })
        
    except Exception as e:
        return JsonResponse({
            'available': False,
            'message': 'Error checking username'
        }, status=500)


@require_http_methods(["POST"])
def check_email_availability(request):
    """
    AJAX endpoint to check if email is available
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        
        if not email:
            return JsonResponse({
                'available': False,
                'message': 'Email is required'
            })
        
        # Basic email validation
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            return JsonResponse({
                'available': False,
                'message': 'Please enter a valid email address'
            })
        
        # Check if email exists
        exists = CustomUser.objects.filter(email=email).exists()
        
        if exists:
            return JsonResponse({
                'available': False,
                'message': 'An account with this email already exists'
            })
        
        return JsonResponse({
            'available': True,
            'message': 'Email is available'
        })
        
    except Exception as e:
        return JsonResponse({
            'available': False,
            'message': 'Error checking email'
        }, status=500)

def logout_user(request):
    logout(request)
    messages.success(request, 'You have successfully logged out.')
    return redirect('home')




# ------------------- Subscriptions and Plan Purchasing-------------------

stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def create_checkout_session(request, plan_id):
    pricing_plan = get_object_or_404(PricingPlan, id=plan_id)
    subscription_type = request.POST.get("subscription_type")

    if subscription_type not in ["monthly", "annual"]:
        subscription_type = "monthly"

    try:
        customer_id = request.user.stripe_customer_id
        user_email = request.user.email

        if customer_id:
            try:
                stripe.Customer.retrieve(customer_id)
            except stripe.error.InvalidRequestError as e:
                if "No such customer" in str(e):
                    customer_id = None
                else:
                    raise 
        if not customer_id:
            customers = stripe.Customer.list(email=user_email, limit=1)
            if customers.data:
                customer_id = customers.data[0]['id']
            else:
                customer = stripe.Customer.create(
                    email=user_email,
                    name=request.user.name or request.user.username,
                )
                customer_id = customer['id']
            request.user.stripe_customer_id = customer_id
            request.user.save(update_fields=['stripe_customer_id'])

        price_amount = pricing_plan.price_monthly if subscription_type == "monthly" else pricing_plan.price_annual
        interval = "month" if subscription_type == "monthly" else "year"

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
                        'unit_amount': int(price_amount * 100),
                        'recurring': {
                            'interval': interval,
                        },
                    },
                    'quantity': 1,
                },
            ],
            'mode': 'subscription',
            'allow_promotion_codes': True, 
            'success_url': request.build_absolute_uri('/dashboard/'),
            'cancel_url': request.build_absolute_uri('/dashboard/billing/'),
            'metadata': {
                'plan_id': pricing_plan.id,
                'subscription_type': subscription_type,
            },
        }

        checkout_session = stripe.checkout.Session.create(**session_params)
        return redirect(checkout_session.url, code=303)

    except stripe.error.StripeError as e:
        return render(request, 'profiles/error.html', {'error': str(e)})

    

ENDPOINT_SECRET = settings.STRIPE_WEBHOOK_SECRET_SUBSCRIBE

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, ENDPOINT_SECRET
        )
    except ValueError as e:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        handle_checkout_session_completed(event['data']['object'])
    elif event['type'] == 'invoice.payment_succeeded':
        handle_payment_succeeded(event['data']['object'])
    elif event['type'] == 'customer.subscription.updated':
        handle_subscription_updated(event['data']['object'])
    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_deleted(event['data']['object'])
    elif event['type'] == 'customer.subscription.created':
        handle_subscription_created(event['data']['object'])
    elif event['type'] == 'invoice.payment_failed':
        handle_payment_failed(event['data']['object'])
    elif event['type'] == 'customer.subscription.paused':
        handle_subscription_paused(event['data']['object'])
    elif event['type'] == 'customer.subscription.resumed':
        handle_subscription_resumed(event['data']['object'])
    elif event['type'] == 'customer.subscription.trial_will_end':
        handle_trial_ending_soon(event['data']['object'])
    return JsonResponse({'status': 'success'})


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
        defaults={
            'stripe_subscription_id': subscription_id,
            'plan': plan,
            'is_active': True,
            'start_date': now(),
            'end_date': now() + timedelta(days=30 if subscription_type == "monthly" else 365),
            'type': subscription_type,
            'status': 'active',
        }
    )
    if created:
        send_subscription_email(user, 'welcome', plan.title)


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
        user_plan.status = 'active'
        user_plan.save()
        send_subscription_email(user_plan.user, 'renewal', user_plan.plan.title)


def handle_subscription_updated(subscription):
    subscription_id = subscription['id']
    status = subscription['status']
    
    if subscription.get('items') and subscription['items'].get('data') and len(subscription['items']['data']) > 0:
        item = subscription['items']['data'][0]
        stripe_price_id = item.get('price', {}).get('id')
        
        plan = None
        if stripe_price_id:
            plan = PricingPlan.objects.filter(
                Q(stripe_price_id_monthly=stripe_price_id) | 
                Q(stripe_price_id_annual=stripe_price_id)
            ).first()
            
            subscription_type = "monthly" if plan and plan.stripe_price_id_monthly == stripe_price_id else "annual"

    user_plan = UserPlan.objects.filter(stripe_subscription_id=subscription_id).first()
    if user_plan:
        prev_status = user_plan.status
        prev_plan = user_plan.plan
        
        user_plan.status = status
        user_plan.is_active = status in ["active", "trialing"]
        
        if plan and prev_plan != plan:
            user_plan.plan = plan
            user_plan.type = subscription_type
            
            if subscription_type == "monthly":
                days = 30
            else:
                days = 365
                
            user_plan.end_date = now() + timedelta(days=days)
            if prev_plan.price_monthly > plan.price_monthly:
                send_subscription_email(user_plan.user, 'downgrade', plan.title)
            else:
                send_subscription_email(user_plan.user, 'upgrade', plan.title)
        
        user_plan.save()
        
        if prev_status != status:
            if status == "past_due":
                send_subscription_email(user_plan.user, 'payment_issue', user_plan.plan.title)
            elif prev_status == "past_due" and status == "active":
                send_subscription_email(user_plan.user, 'payment_resolved', user_plan.plan.title)


def handle_subscription_deleted(subscription):
    subscription_id = subscription['id']

    user_plan = UserPlan.objects.filter(stripe_subscription_id=subscription_id).first()
    if user_plan:
        user_plan.is_active = False
        user_plan.status = "canceled"
        user_plan.save()
        
        send_subscription_email(user_plan.user, 'canceled', user_plan.plan.title)


def handle_subscription_created(subscription):
    subscription_id = subscription['id']
    customer_id = subscription['customer']
    
    user = CustomUser.objects.filter(stripe_customer_id=customer_id).first()
    
    if not user:
        return
        
    if subscription.get('items') and subscription['items'].get('data') and len(subscription['items']['data']) > 0:
        item = subscription['items']['data'][0]
        stripe_price_id = item.get('price', {}).get('id')
        
        plan = None
        if stripe_price_id:
            plan = PricingPlan.objects.filter(
                Q(stripe_price_id_monthly=stripe_price_id) | 
                Q(stripe_price_id_annual=stripe_price_id)
            ).first()
            
            if not plan:
                return None
                
            subscription_type = "monthly" if plan.stripe_price_id_monthly == stripe_price_id else "annual"
            
            user_plan, created = UserPlan.objects.update_or_create(
                user=user,
                defaults={
                    'stripe_subscription_id': subscription_id,
                    'plan': plan,
                    'is_active': subscription['status'] in ["active", "trialing"],
                    'start_date': now(),
                    'end_date': now() + timedelta(days=30 if subscription_type == "monthly" else 365),
                    'type': subscription_type,
                    'status': subscription['status'],
                }
            )
            
            if created:
                send_subscription_email(user, 'welcome', plan.title)


def handle_payment_failed(invoice):
    """Handle when a payment fails"""
    subscription_id = invoice['subscription']
    user_plan = UserPlan.objects.filter(stripe_subscription_id=subscription_id).first()
    
    if user_plan:
        user_plan.status = "past_due"
        user_plan.save()
        
        send_subscription_email(user_plan.user, 'payment_failed', user_plan.plan.title)


def handle_subscription_paused(subscription):
    subscription_id = subscription['id']
    user_plan = UserPlan.objects.filter(stripe_subscription_id=subscription_id).first()
    
    if user_plan:
        user_plan.status = "paused"
        user_plan.is_active = False
        user_plan.save()        
        send_subscription_email(user_plan.user, 'paused', user_plan.plan.title)


def handle_subscription_resumed(subscription):
    subscription_id = subscription['id']
    user_plan = UserPlan.objects.filter(stripe_subscription_id=subscription_id).first()
    
    if user_plan:
        user_plan.status = "active"
        user_plan.is_active = True
        
        # Update end date
        if user_plan.type == "monthly":
            days = 30
        else:
            days = 365
            
        user_plan.end_date = now() + timedelta(days=days)
        user_plan.save()        
        send_subscription_email(user_plan.user, 'resumed', user_plan.plan.title)


def handle_trial_ending_soon(subscription):
    subscription_id = subscription['id']
    user_plan = UserPlan.objects.filter(stripe_subscription_id=subscription_id).first()
    
    if user_plan:
        send_subscription_email(user_plan.user, 'trial_ending', user_plan.plan.title)


def send_subscription_email(user, event_type, plan_name):
    subject_mapping = {
        'welcome': f"Welcome to {plan_name} Plan",
        'renewal': f"Your {plan_name} subscription has been renewed",
        'canceled': f"Your {plan_name} subscription has been canceled",
        'payment_failed': f"Payment failed for your {plan_name} subscription",
        'payment_issue': f"Action required: Issue with your {plan_name} subscription",
        'payment_resolved': f"Payment successful for your {plan_name} subscription",
        'upgrade': f"You've upgraded to the {plan_name} Plan",
        'downgrade': f"You've changed to the {plan_name} Plan",
        'paused': f"Your {plan_name} subscription has been paused",
        'resumed': f"Your {plan_name} subscription has been resumed",
        'trial_ending': f"Your {plan_name} trial is ending soon"
    }
    
    subject = subject_mapping.get(event_type, f"Update on your {plan_name} subscription")
    template = f"profiles/emails_subscription/subscription_{event_type}.html"
    
    try:
        html_content = render_to_string(template, {
            'user': user,
            'plan_name': plan_name
        })
        
        message = Mail(
            from_email='support@fireprenair.com',
            to_emails=user.email,
            subject=subject,
            html_content=html_content
        )
        
        sg = SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        response = sg.send(message)
        return response
        
    except Exception as e:
        print(f"Error sending email: {e}")
        return None


@login_required
def stripe_billing_portal(request):
    try:
        user = request.user
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(email=user.email, name=user.name)
            user.stripe_customer_id = customer.id
            user.save()
        else:
            try:
                stripe.Customer.retrieve(user.stripe_customer_id)
            except stripe.error.InvalidRequestError as e:
                if e.http_status == 404:
                    customer = stripe.Customer.create(email=user.email, name=user.name)
                    user.stripe_customer_id = customer.id
                    user.save()
                else:
                    raise 
        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=request.build_absolute_uri('/dashboard/'),
        )
        return redirect(session.url)
    except Exception as e:
        return render(request, 'profiles/error.html', {'error': str(e)})


from django.utils.translation import activate

@login_required
def update_language(request):
    if request.method == "POST":
        lang = request.POST.get("language")
        next_url = request.POST.get("next", request.META.get("HTTP_REFERER", "home"))  
        request.user.language = lang
        request.user.save()
        activate(lang)
        request.session["django_language"] = lang
        messages.success(request, "Language updated successfully!")
        return redirect(next_url)
    return redirect("home")
