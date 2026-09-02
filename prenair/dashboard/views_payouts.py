from django.shortcuts import render, redirect
from .models import *
from django.conf import settings
from datetime import datetime
import requests
from django.core.cache import cache
from home.models import UserPlan, PricingPlan
from django.contrib import messages


# def add_payoneer_account(request):
#     if request.method == 'POST':
#         form = PayoneerAccountForm(request.POST)
#         if form.is_valid():
#             account = form.save(commit=False)
#             account.user = request.user
#             account.save()
#             return redirect('dashboard')  # Redirect to dashboard
#     else:
#         form = PayoneerAccountForm()
#     return render(request, 'dashboard/add_payoneer_account.html', {'form': form})



# program_id = settings.PAYONEER_PROGRAM_ID

# PAYONEER_BASE_URL = f"https://api.sandbox.payoneer.com/v4/programs/{program_id}/masspayouts"

# def get_payoneer_token():
#     token = cache.get('payoneer_token')
#     if not token:
#         url = "https://api.payoneer.com/v4/oauth2/token"
#         payload = {
#             'grant_type': 'client_credentials',
#             'client_id': settings.PAYONEER_CLIENT_ID,
#             'client_secret': settings.PAYONEER_CLIENT_SECRET
#         }
#         response = requests.post(url, data=payload)
#         response_data = response.json()
#         token = response_data.get('access_token')
#         if token:
#             cache.set('payoneer_token', token, timeout=30 * 24 * 3600)  # 30 days
#     return token


# def create_payout(payee_id, amount):
#     access_token = get_payoneer_token()
#     headers = {
#         "Authorization": f"Bearer {access_token}",
#         "Content-Type": "application/json"
#     }
#     payload = {
#      "Payments": [
#          {
#              "payee_id": payee_id,
#              "amount": str(amount),
#              "currency": "USD",
#              "description": "Withdrawal from Fireprenair",
#              "client_reference_id": f"payout-{datetime.now().timestamp()}"
#          }
#      ]
# }

#     response = requests.post(PAYONEER_BASE_URL, headers=headers, json=payload)
#     return response.json()




# def request_withdrawal(request):
#     if request.method == 'POST':
#         amount = request.POST.get('amount')
#         payoneer_account = request.user.payoneer_account
#         if payoneer_account:
#             WithdrawalRequest.objects.create(user=request.user, amount=amount, status='PENDING')
#             return redirect('withdrawal_history')
#         else:
#             return render(request, 'request_withdrawal.html', {'error': "No Payoneer account linked"})
#     return render(request, 'request_withdrawal.html')



# def process_withdrawals():
#     pending_requests = WithdrawalRequest.objects.filter(status='PENDING')
#     for request in pending_requests:
#         response = create_payout(request.user.payoneer_account.payee_id, request.amount)
#         if response.status_code == 200:
#             data = response.json()
#             if data.get('status') == 'SUCCESS':
#                 request.status = 'COMPLETED'
#             else:
#                 request.status = 'FAILED'
#         else:
#             # Log the error for debugging
#             print(f"Error: {response.text}")
#             request.status = 'FAILED'
#             request.processed_at = datetime.now()
#             request.save()

from work_prenair.views import send_email
from django.urls import reverse
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json


def validate_payout_eligibility(user):
    """
    Validates if a user is eligible to request a payout by checking all required KYC fields.
    Returns a dict with can_request_payout (bool) and missing_fields (list).
    """
    missing_fields = []
    
    # Check User model fields
    if not user.country:
        missing_fields.append("country")
    
    # Check phone_no
    if not user.phone_no:
        missing_fields.append("phone_no")
    
    # Check identity fields (on User model)
    if not user.identity_type:
        missing_fields.append("identity_type")
    if not user.identity_number:
        missing_fields.append("identity_number")
    
    # Check KYC Profile for identity_country (used for payout)
    kyc_profile, created = KYCProfile.objects.get_or_create(user=user)
    if not kyc_profile.identity_country:
        missing_fields.append("identity_country")
    
    return {
        "can_request_payout": len(missing_fields) == 0,
        "missing_fields": missing_fields
    }


@require_http_methods(["GET", "POST"])
def validate_payout_api(request):
    """
    API endpoint to validate payout eligibility.
    Returns JSON with can_request_payout and missing_fields.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    validation_result = validate_payout_eligibility(request.user)
    return JsonResponse(validation_result)


@require_http_methods(["POST"])
def save_identity_api(request):
    """
    API endpoint to save/update identity verification data.
    Accepts: identity_type, identity_number, identity_country, country, phone_no
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    except json.JSONDecodeError:
        data = request.POST
    
    user = request.user
    errors = []
    
    # Update User fields if provided
    if 'country' in data and data['country']:
        user.country = data['country']
    
    if 'phone_no' in data and data['phone_no']:
        user.phone_no = data['phone_no']
    
    # Update identity on User model
    if 'identity_type' in data and data['identity_type']:
        user.identity_type = data['identity_type']
    if 'identity_number' in data and data['identity_number']:
        user.identity_number = data['identity_number']
    
    # Update or create KYC Profile (sync identity + identity_country for payout)
    kyc_profile, created = KYCProfile.objects.get_or_create(user=user)
    if 'identity_type' in data and data['identity_type']:
        kyc_profile.identity_type = data['identity_type']
    if 'identity_number' in data and data['identity_number']:
        kyc_profile.identity_number = data['identity_number']
    if 'identity_country' in data and data['identity_country']:
        kyc_profile.identity_country = data['identity_country']
    
    # Validate required fields
    if not user.identity_type:
        errors.append("Identity type is required")
    if not user.identity_number:
        errors.append("Identity number is required")
    if not kyc_profile.identity_country:
        errors.append("Identity country is required")
    
    if errors:
        return JsonResponse({"success": False, "errors": errors}, status=400)
    
    # Save all changes
    user.save()
    kyc_profile.save()
    
    # Re-validate after saving
    validation_result = validate_payout_eligibility(user)
    
    return JsonResponse({
        "success": True,
        "message": "Verification details saved successfully.",
        "can_request_payout": validation_result["can_request_payout"],
        "missing_fields": validation_result["missing_fields"]
    })


def payout_request(request):
    user = request.user
    user_payoneer = PayoutAccount.objects.filter(user=user)
    if not user_payoneer:
        messages.error(request, "Please Attach your Payout Account first!")
        return redirect('payout_settings')
    
    # Always validate KYC - pass result to template
    validation_result = validate_payout_eligibility(user)
    
    if request.method == "POST":
        # For POST requests, check validation before processing
        if not validation_result["can_request_payout"]:
            # For AJAX requests, return JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    "can_request_payout": False,
                    "missing_fields": validation_result["missing_fields"],
                    "error": "Please complete identity verification first."
                }, status=400)
            # For regular form submissions, show the page with modal
            import json
            return render(request, 'dashboard/payout_form.html', {
                'user': user,
                'can_request_payout': False,
                'missing_fields': json.dumps(validation_result["missing_fields"])
            })
        amount = request.POST.get('amount')
        acc_type = request.POST.get('account_type')
        
        # Validate amount
        try:
            amount = float(amount)
        except ValueError:
            messages.error(request, "Invalid amount entered.")
            return redirect('payout_request')
        
        if acc_type == 'Payoneer' and not user.payout_account.filter(type='Payoneer').exists():
            messages.error(request, "Please add your Payoneer account in your payout settings.")
            return redirect('payout_settings')
        
        if acc_type == 'Paypal' and not user.payout_account.filter(type='Paypal').exists():
            messages.error(request, "Please add your Paypal account in your payout settings.")
            return redirect('payout_settings')
        
        if amount <= 4:
            messages.error(request, "Amount must be greater than or equal to $5.")
            return redirect('payout_request')
        
        if amount > user.available_earnings:
            messages.error(request, "You cannot withdraw more than your available balance.")
            return redirect('payout_request')
        
        amount_to_add = amount - 3
        
        withdrawal = WithdrawalRequest.objects.create(
            user=user,
            amount=amount_to_add,
            status='PENDING',
            payout_type=acc_type
        )
        user.available_earnings -= Decimal(amount)
        user.amount_being_cleared += Decimal(amount_to_add)
        user.save()
        admin_emails = ['shoutdel@gmail.com', 'fireprenair@gmail.com', 'zainaligondal121@gmail.com']
        email_subject = f"New Payout Request from {user.username}"
        admin_dashboard_url = request.build_absolute_uri(reverse("admin_withdrawal_requests"))

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
                        <h2 style="color: #1e3a8a; font-size: 22px; text-align: center;">New Withdrawal Request Submitted 🚀</h2>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">
                            A new withdrawal request has been submitted by <strong>{user.username}</strong>.
                        </p>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">
                            <strong>Details:</strong><br>
                            Amount: <strong>${withdrawal.amount}</strong><br>
                            Payout Type: <strong>{withdrawal.payout_type}</strong><br>
                            Status: <strong>{withdrawal.status}</strong><br>
                            User Email: <strong>{user.email}</strong>
                        </p>
                        <p style="color: #333; font-size: 16px; line-height: 1.6;">
                            Please review the request in the admin dashboard.
                        </p>
                        <p style="text-align: center; margin-top: 10px;">
                            <a href="{admin_dashboard_url}" 
                               style="display: inline-block; background-color: #1e3a8a; color: #fff; text-decoration: none; padding: 10px 18px; border-radius: 6px; font-weight: bold;">
                                Go to Admin Dashboard
                            </a>
                        </p>
                    </div>      

                    <!-- Footer -->
                    <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                        <p style="margin: 0; font-size: 14px;">FirePrenair Admin Notification</p>
                    </div>
                </div>
            </body>
            </html>
        """
        for email in admin_emails:
            send_email(email, email_subject, email_content)

        messages.success(request, "Your payout request has been submitted successfully.")
        return redirect('dashboard_home')

    # For GET requests, always pass validation result to template
    # The modal will automatically show if there are missing fields
    import json
    return render(request, 'dashboard/payout_form.html', {
        'user': user,
        'can_request_payout': validation_result["can_request_payout"],
        'missing_fields': json.dumps(validation_result["missing_fields"])
    })


def payout_settings(request):
    user = request.user
    paypal_add = request.GET.get('paypal', False)
    payoneer_acc = PayoutAccount.objects.filter(user=user, type='Payoneer').first()
    paypal_acc = PayoutAccount.objects.filter(user=user, type='Paypal').first()
    user_acc = PayoutAccount.objects.filter(user=user)
    if request.method == "POST":
        email = request.POST.get('email')
        name = request.POST.get('fullname')
        type = request.POST.get('acc_type')


        if not email or not name:
            messages.error(request, "Please enter both fields.")
            return redirect('payout_settings')
        
        if type == 'Paypal':
            PayoutAccount.objects.update_or_create(
                user=user,
                type='Paypal',
                defaults={
                    'email': email,
                    'name': name
                }
            )
            messages.success(request, "Paypal account details updated successfully.")
            return redirect('dashboard_home')
        
        else:
            PayoutAccount.objects.update_or_create(
                user=user,
                type='Payoneer',
                defaults={
                    'email': email,
                    'name': name,
                }
            )
        messages.success(request, "Payoneer account details updated successfully.")
        return redirect('dashboard_home')
    
    context = {
        'user1': user,
        'payoneer_account': payoneer_acc,
        'paypal_add': paypal_add,
        'paypal_account': paypal_acc,
        'user_accounts': user_acc
    }
    return render(request, 'dashboard/payout_settings.html', context)



def payment_history(request):
    user = request.user
    withdrawals = WithdrawalRequest.objects.filter(user=user)
    return render(request, 'dashboard/payment_history.html', {'withdrawals': withdrawals})


def user_billings(request):
    user = request.user
    user_plans = UserPlan.objects.filter(user=user)
    plans = PricingPlan.objects.all()
    basic_plan = PricingPlan.objects.get(title='FreeTier')
    startprenair_plan = PricingPlan.objects.get(title='StartPrenair')
    bizprenair_plan = PricingPlan.objects.get(title='BizPrenair')
    entreprenair_plan = PricingPlan.objects.get(title='EntrePrenair')

    context = {
        'user_plans': user_plans,
        'plans': plans,
        'basic_plan': basic_plan,
        'start_plan': startprenair_plan,
        'biz_plan': bizprenair_plan,
        'entre_plan': entreprenair_plan
    }
    
    return render(request, 'dashboard/billings.html', context)


def paypal_manual_transfer(request):
    user = request.user
    if request.method == 'POST':
        amount = float(request.POST.get('amount', 0))
        amount = Decimal(amount)
        
        if amount > user.available_earnings:
            messages.error(request, "You cannot withdraw more than your available balance.")
            return redirect('dashboard_home')

        user.available_earnings -= amount
        user.save()
        messages.success(request, "Your withdrawal request has been processed successfully.")
        WithdrawalRequest.objects.create(user=user, amount=amount, status='COMPLETED', payout_type='MANUAL')
        return redirect('dashboard_home')
    return render(request, 'dashboard/paypal_withdraw.html')



# -------------------------------------------- PayPal Auotmatic Payouts --------------------------------------------

# import paypalrestsdk
# import time
# from django.contrib.auth.decorators import login_required
# from django.http import JsonResponse

# def initiate_payout(paypal_email, amount, currency='USD'):
#     paypalrestsdk.configure({
#         "mode": "sandbox",  # Change to "live" in production
#         "client_id": settings.PAYPAL_CLIENT_ID,
#         "client_secret": settings.PAYPAL_CLIENT_SECRET,
#     })
    
#     payout = paypalrestsdk.Payout({
#         "sender_batch_header": {
#             "sender_batch_id": "batch_" + str(int(time.time())),
#             "email_subject": "You have a payment!"
#         },
#         "items": [{
#             "recipient_type": "EMAIL",
#             "amount": {
#                 "value": f"{amount:.2f}",
#                 "currency": currency,
#             },
#             "receiver": paypal_email,
#             "note": "Thanks for using Fireprenair!",
#         }]
#     })

#     if payout.create():
#         return payout
#     else:
#         return payout.error



# @login_required
# def paypal_transfer(request):
#     seller = request.user
#     if not seller.paypal_email:
#         messages.error(request, "Please add your PayPal email address in your Payout Methods!.")
#         return redirect('dashboard_home')
#     if request.method == 'POST':
#         amount = float(request.POST.get('amount', 0))
#         amount = Decimal(amount)
        
#         if amount > seller.available_earnings:
#             messages.error(request, "You cannot withdraw more than your available balance.")
#             return redirect('dashboard_home')

#         # Initiate payout
#         result = initiate_payout(seller.paypal_email, amount)
#         if "batch_header" in result:
#             seller.available_earnings -= amount
#             seller.save()
#             messages.success(request, "Your withdrawal request has been processed successfully.")
#             WithdrawalRequest.objects.create(user=seller, amount=amount, status='COMPLETED', payout_type='PAYPAL')
#             return redirect('dashboard_home')
#         else:
#             messages.error(request, "An error occurred while processing your withdrawal request.")
#             return redirect('dashboard_home')
#     return render(request, 'dashboard/paypal_withdraw.html')

