from django.shortcuts import render, get_object_or_404, redirect
from .models import *
from profiles.models import CustomUser
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .forms import *
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.core.paginator import Paginator
from django.contrib.auth import logout
from django.db.models import Q
from django.db.models import Sum
from django.utils.timezone import now
from datetime import timedelta
from django.http import JsonResponse
from profiles.models import Notification
import markdown
from decimal import Decimal
from django.views.decorators.http import require_POST
# payment Integration with stripe
import stripe
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Create your views here.


# ai
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.safestring import mark_safe
import markdown
from groq import Groq


knowledge_base = {
    "digiprenair": {
        "description": (
            "Digiprenair is a digital marketplace where users can buy and sell digital products like eBooks, software, "
            "designs, templates, music, and other downloadable content. Sellers can list their products, and buyers can make "
            "purchases using secure payment methods."
        ),
        "faq": {
            "What is Digiprenair?": (
                "Digiprenair is a digital marketplace that connects buyers and sellers of digital products. Sellers list their products, "
                "and buyers can make purchases using secure payment options."
            ),
            "How can I become a seller on Digiprenair?": (
                "To become a seller, sign up on Digiprenair, complete your profile, and list your digital products with appropriate descriptions, "
                "pricing, and file uploads."
            ),
            "How do I buy products on Digiprenair?": (
                "To buy products, browse the marketplace, add items to your cart, and proceed to checkout. You can pay via the available payment methods."
            ),
            "What types of digital products can I sell?": (
                "You can sell a wide range of digital products, including eBooks, software, digital designs, music, courses, templates, and more."
            ),
            "How do I get paid as a seller?": (
                "Sellers receive payments once a purchase is made and the buyer has received their digital product. Payments can be withdrawn using available methods."
            ),
            "Is Digiprenair safe to use?": (
                "Yes, Digiprenair offers a secure environment with encrypted transactions, a reliable payment system, and dispute resolution options for both buyers and sellers."
            ),
            "How do I download purchased products?": (
                "After completing a purchase, buyers can download the product directly from the order confirmation page or via a secure link sent via email."
            ),
            "Can I request a refund for a product?": (
                "Refund requests are handled based on the seller’s policy. If a product is faulty or doesn't match the description, you can request a refund."
            ),
            "How do I leave a review for a product?": (
                "Once a purchase is complete and the product is downloaded, buyers can leave a review based on their experience, which helps other buyers."
            ),
            "How can I update my seller profile?": (
                "You can update your seller profile by going to the 'Profile' section of your account, where you can modify your business name, description, logo, and contact details."
            ),
            "Can I edit or delete my product listings?": (
                "Yes, as a seller, you can edit or delete your product listings at any time by accessing your seller dashboard and managing your products."
            ),
            "How do I handle disputes with buyers?": (
                "If there is a dispute, Digiprenair offers a mediation process to help resolve the issue between buyers and sellers to ensure satisfaction."
            ),
            "Do I need to pay upfront as a buyer?": (
                "Yes, buyers need to complete payment before the seller delivers the digital product. The payment is securely processed through the platform."
            ),
            "How do I cancel an order as a buyer?": (
                "Buyers can cancel an order if the product hasn’t been delivered yet. Once the product is delivered, cancellations are not typically allowed."
            ),
        },
    }
}


@csrf_exempt
def digiprenair_chatbot_view(request):
    if request.method == "POST":
        user_message = request.POST.get("message", "").lower()

        # Predefined responses for quick replies
        predefined_responses = {
            "name": "I am your customer support assistant, here to help you with any questions about Workprenair.",
            "who_created_you": "I was created by the development team of Digiprenair.",
            "what_can_you_do": "I can help you navigate our platform, answer questions about our services, and provide consultation details.",
        }

        for key, response in predefined_responses.items():
            if key in user_message:
                return JsonResponse({"message": response})

        # Interact with Groq API
        client = Groq(api_key=settings.GROQ_API_KEY)
        groq_response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": json.dumps(
                        {
                            "knowledge_base": knowledge_base,
                            "instruction": "Please generate short, clear, and professional responses. "
                            "Limit unnecessary details, ensure the tone is formal, and provide concise answers. "
                            "Avoid elaboration and keep responses to the point."
                            "Give answer according to question.",
                        }
                    ),
                },
                {"role": "user", "content": user_message},
            ],
            model="llama3-8b-8192",
        )

        # Process the Groq response
        bot_reply = groq_response.choices[0].message.content.strip()
        bot_reply_html = markdown.markdown(bot_reply)
        bot_reply_html = mark_safe(bot_reply_html)

        return JsonResponse({"message": bot_reply_html})

    return JsonResponse({"message": "Only POST requests are allowed."}, status=400)


# Custom logout view
def logout_view(request):
    logout(request)
    return redirect("digi_home")


def digi_home(request):
    categories = Category.objects.all()
    featured_items = Product.objects.filter(is_featured=True)[:10]
    featured_sellers = CustomUser.objects.filter(
        is_digi_seller=True, digi_is_featured=True
    )[
        :5
    ]  # Get featured digital sellers
    newest_items = Product.objects.order_by("-created_at")[:20]

    # Render the data in context to be accessed in the template
    context = {
        "categories": categories,
        "featured_items": featured_items,
        "featured_sellers": featured_sellers,
        "newest_items": newest_items,
    }
    return render(request, "digi_prenair/home.html", context)


def digi_explore(request):
    search_term = request.GET.get("q", "").strip()
    category_param = request.GET.get("params", "all")
    category_id = request.GET.get("category")
    selected_asset_types = request.GET.getlist('asset_type')

    all_items = Product.objects.all()

    if category_id:
        all_items = all_items.filter(
            Q(category__id=category_id)
            | Q(category_l_2_id=category_id)
            | Q(category_l_3_id=category_id)
        )

    if category_param != "all":
        all_items = all_items.filter(category__id=category_param)

    if selected_asset_types:
        all_items = all_items.filter(category__id__in=selected_asset_types)

    if search_term:
        all_items = all_items.filter(
            Q(title__icontains=search_term) | Q(description__icontains=search_term)
        )

    order = request.GET.get("order")
    if order == "newest-to-oldest":
        all_items = all_items.order_by("-created_at")
    elif order == "oldest-to-newest":
        all_items = all_items.order_by("created_at")

    # Fetch asset types (replace slugs with your actual category slugs)
    asset_types = Category.objects.filter(
        name__in=['vectors', 'illustrations', 'photos', 'icons', 
                 'videos', 'psd', 'templates', 'mockups', '3d-models']
    )

    paginator = Paginator(all_items, 100)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "categories": Category.objects.all(),
        "asset_types": asset_types,
        "selected_asset_types": selected_asset_types,
        "search_term": search_term,
        "selected_category": category_param,
    }
    return render(request, "digi_prenair/explore.html", context)


def product_search_api(request):
    search_term = request.GET.get('q', '').strip() or request.GET.get('params', '').strip()
    products = Product.objects.all()
    
    if search_term:
        products = products.filter(
            Q(title__icontains=search_term) | 
            Q(description__icontains=search_term)
        )[:5]  
        
    results = []
    for product in products:
        results.append({
            'title': product.title,
            'image': product.image.url,
            'description': product.description[:100] + '...' if product.description else '',
            'price': str(product.price),
            'discounted_price': str(product.discounted_price),
            'url': reverse('digi_product', kwargs={'slug': product.slug}),
            'slug': product.slug
        })
        
    return JsonResponse({'results': results})


def digi_sellers(request):
    # Start with all sellers
    sellers = CustomUser.objects.filter(is_digi_seller=True)

    # Get filter parameters from the request (e.g., from query parameters)
    verified = request.GET.get("verified")
    order = request.GET.get("order")
    location = request.GET.get("location")

    # Apply filters
    if verified == "verified-creators-only":
        sellers = sellers.filter(digi_is_verified=True)

    if location:
        sellers = sellers.filter(country__iexact=location)

    # Apply sorting
    if order == "order-by-name":
        sellers = sellers.order_by("username")  # Order by name (A-Z)
    elif order == "order-by-registration-date":
        sellers = sellers.order_by(
            "-digi_total_sales"
        )  # Order by number of sales (high to low)

    # Implement pagination for the filtered and sorted sellers
    paginator = Paginator(sellers, 10)  # Show 10 sellers per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "digi_prenair/sellers.html",
        {
            "page_obj": page_obj,
            "current_order": order,
            "current_verified": verified,
            "location": location,
        },
    )


def digi_product(request, slug):
    product = get_object_or_404(Product, slug=slug)
    reviews = product.reviews.all() 

    prev_product = Product.objects.filter(created_at__lt=product.created_at).order_by('-created_at').first()
    next_product = Product.objects.filter(created_at__gt=product.created_at).order_by('created_at').first()

    description_html = markdown.markdown(product.description)
    user_review_exists = False
    is_product_owner = False
    in_cart = False
    already_purchased = False

    if request.user.is_authenticated:
        user_review_exists = reviews.filter(user=request.user).exists()
        is_product_owner = product.seller == request.user
        in_cart = CartItem.objects.filter(
            cart__user=request.user, product=product
        ).exists()
        already_purchased = OrderItem.objects.filter(
            order__user=request.user, product=product, order__is_paid=True
        ).exists()

    if (
        request.method == "POST"
        and request.user.is_authenticated
        and not user_review_exists
    ):
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            Notification.objects.create(
                user=product.seller,
                message=f"{request.user.username} has reviewed your product",
                app_name="digiprenair",
            )

            # Send email notification to the seller
            seller_email_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
                    <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                        <!-- Header -->
                        <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                            <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                        </div>

                        <!-- Body -->
                        <div style="padding: 20px;">
                            <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">📢 New Review for Your Product</h2>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {product.seller.username},</p>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">
                                Your product <strong>{product.title}</strong> has received a new review from <strong>{request.user.username}</strong>.
                            </p>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Review Details:</strong></p>
                            <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                                <li style="margin-bottom: 10px;"><strong>Rating:</strong> {review.rating}</li>
                                <li style="margin-bottom: 10px;"><strong>Comment:</strong> {review.body}</li>
                            </ul>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">You can view the review and respond to it from your seller dashboard:</p>
                            <p style="text-align: center; margin: 20px 0;">
                                <a href="{request.build_absolute_uri(reverse('digi_dashboard'))}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">View Dashboard</a>
                            </p>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">Need help? Our support team is always here for you.</p>
                        </div>

                        <!-- Footer -->
                        <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                            <p style="margin: 0; font-size: 14px;">Thank you for being a valued seller on FirePrenair! 🚀</p>
                        </div>
                    </div>
                </body>
                </html>
            """

            send_email(
                product.seller.email,
                "📢 New Review for Your Product",
                seller_email_content,
            )

            return redirect(reverse("digi_product", kwargs={"slug": slug}))
    else:
        form = ReviewForm()

    context = {
        "product": product,
        "reviews": reviews,
        "form": form,
        "description_html": description_html,
        "user_review_exists": user_review_exists,
        "is_product_owner": is_product_owner,
        "in_cart": in_cart,
        "already_purchased": already_purchased,
        "prev_product": prev_product,
        "next_product": next_product,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        template = 'digi_prenair/product_modal_content.html'
    else:
        template = 'digi_prenair/product.html'
    return render(request, template, context)


def digi_profile(request, slug):
    seller = get_object_or_404(CustomUser, slug=slug, is_digi_seller=True)
    products = Product.objects.filter(seller=seller)

    paginator = Paginator(products, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "user": seller,
        "cover_photo": seller.digi_cover_photo,
        "country": seller.country,
        "speciality": seller.digi_speciality,
        "joined_date": seller.created_at.strftime("%B %d, %Y"),
        "page_obj": page_obj,  # Pass the page_obj to the template
    }
    return render(request, "digi_prenair/profile.html", context)


@login_required
def digi_shoping_cart(request):
    user = request.user
    cart, create = Cart.objects.get_or_create(user=user)
    cart_items = cart.items.all()

    # Calculate total price for the cart
    total_price = sum(
        item.quantity * item.product.effective_price() for item in cart_items
    )

    context = {
        "cart": cart,
        "cart_items": cart_items,
        "total_price": total_price,
    }
    return render(request, "digi_prenair/shopping_cart.html", context)

@login_required
def add_to_cart(request, slug):
    product = get_object_or_404(Product, slug=slug)

    if request.user.is_authenticated:
        # Authenticated user: use database-based cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

        if not created:
            # If item already exists in cart, increase the quantity
            cart_item.quantity += 1
            cart_item.save()

        messages.success(request, f"{product.title} has been added to your cart.")
    else:
        # Anonymous user: ask them to log in first
        messages.info(request, "Please `log in` to add items to your cart.")
        # return redirect(reverse('digi_home'))  # Replace 'login' with the name of your login URL

    return redirect("digi_product", slug=slug)


def remove_from_cart(request, slug):
    product = get_object_or_404(Product, slug=slug)
    cart = get_object_or_404(Cart, user=request.user)
    cart_item = CartItem.objects.filter(cart=cart, product=product).first()
    if cart_item:
        cart_item.delete()

    messages.error(request, f"`{product.title}` has been removed from cart.")
    return redirect("digi_shoping_cart")


@login_required
def digi_notifications(request):
    notifications = request.user.notifications.filter(app_name="digiprenair").order_by(
        "-created_at"
    )
    return render(
        request, "digi_prenair/notification.html", {"notifications": notifications}
    )


@login_required
def mark_notification_as_read(request, notification_id):
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )
    notification.is_read = True
    notification.save()
    # Redirect to the previous page or a fallback URL
    previous_url = request.META.get("HTTP_REFERER", "/")
    return redirect(previous_url)


@login_required
def delete_notification(request, notification_id):
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )
    notification.delete()
    return JsonResponse({"success": True})


@login_required
def mark_all_notifications_as_read(request):
    # Mark all notifications as read
    notifications = request.user.notifications.filter(app_name="digiprenair")
    notifications.update(is_read=True)
    messages.success(request, "All notifications have been marked as read.")

    # Redirect to the previous page or a fallback URL
    previous_url = request.META.get("HTTP_REFERER", "/")
    return redirect(previous_url)


@login_required
def digi_profile_info(request):
    user = request.user
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            if "username" in form.changed_data:
                user.is_username_changed = True
            form.save()
            messages.success(request, "Your profile has been updated successfully!")
            return redirect("digi_profile_info")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProfileUpdateForm(instance=user)

    return render(request, "digi_prenair/profile_info.html", {"form": form})


@login_required
def digi_profile_settings(request):
    if request.method == "POST":
        password_form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(
                request, password_form.user
            )  # Prevents logout after password change
            messages.success(request, "Your password was successfully updated!")
            return redirect("digi_profile_settings")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        password_form = CustomPasswordChangeForm(user=request.user)

    context = {
        "password_form": password_form,
    }
    return render(request, "digi_prenair/profile_settings.html", context)


@login_required
def digi_dashboard(request):
    user = request.user

    # Check if the user is a seller
    if not user.is_digi_seller:
        messages.error(request, "You are not a seller. Access denied.")
        return redirect("digi_home")

    total_items_listed = user.digi_total_items
    total_items_sold = user.digi_total_sales
    total_sales_amount = user.digi_total_earnings

    # Fetch recent sales and paginate them
    recent_sales = OrderItem.objects.filter(product__seller=user).order_by(
        "-order__created_at"
    )

    # Calculate monthly earnings for the last 12 months
    current_date = now()
    monthly_earnings = []
    months = []
    for i in range(12):
        month_start = (
            current_date - timedelta(days=current_date.day - 1) - timedelta(days=30 * i)
        )
        month_end = month_start + timedelta(days=30)
        earnings = (
            recent_sales.filter(
                order__created_at__gte=month_start, order__created_at__lt=month_end
            ).aggregate(total=Sum("order__total_amount"))["total"]
            or 0
        )  # Use total_amount instead of total_price
        monthly_earnings.append(earnings)
        months.append(month_start.strftime("%B %Y"))

    paginator = Paginator(recent_sales, 5)  # Show 5 items per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "total_items_listed": total_items_listed,
        "total_items_sold": total_items_sold,
        "total_sales_amount": total_sales_amount,
        "monthly_earnings": list(
            reversed(monthly_earnings)
        ),  # Reverse to make chronological
        "months": list(reversed(months)),  # Reverse to make chronological
        "page_obj": page_obj,
    }

    return render(request, "digi_prenair/dashboard.html", context)


@login_required
def digi_upload_item(request):
    user = request.user

    if not user.is_digi_seller:
        messages.error(request, "You are not a seller. Access denied.")
        return redirect("digi_home")

    if request.method == "POST":
        form = ProductUploadForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user  # Associate product with the current user
            product.save()
            return redirect("digi_profile", user.slug)
    else:
        form = ProductUploadForm()

    return render(request, "digi_prenair/upload_item.html", {"form": form})


@login_required
def digi_manage_items(request):
    user = request.user

    if not user.is_digi_seller:
        messages.error(request, "You are not a seller. Access denied.")
        return redirect("digi_home")

    products = Product.objects.filter(
        seller=request.user
    )  # Fetch products for the current user
    return render(request, "digi_prenair/manage_items.html", {"products": products})


@login_required
def edit_item(request, slug):
    user = request.user

    if not user.is_digi_seller:
        messages.error(request, "You are not a seller. Access denied.")
        return redirect("digi_home")

    product = get_object_or_404(Product, slug=slug)

    if request.method == "POST":
        form = ProductUploadForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect("digi_manage_items")
    else:
        form = ProductUploadForm(instance=product)
    return render(
        request, "digi_prenair/upload_item.html", {"form": form, "product": product}
    )


@login_required
def digi_purchases(request):
    user = request.user
    orders = Order.objects.filter(user=user, is_paid=True)
    
    new_order = request.GET.get('new_order') == 'true'
    print(new_order)
    latest_order_items = None
    projects = Project.objects.filter(user=user)
    
    if new_order:
        latest_order = orders.order_by('-created_at').first()
        if latest_order:
            latest_order_items = latest_order.order_items.all()

    return render(request, "digi_prenair/purchases.html", {
        "orders": orders,
        "show_project_modal": new_order and latest_order_items,
        "latest_order_items": latest_order_items,
        "projects": projects
    })

@login_required
@require_POST
def add_to_project(request):
    user = request.user
    data = json.loads(request.body)
    
    item_ids = data.get('item_ids', [])
    project_id = data.get('project_id')
    project_name = data.get('project_name')
    
    try:
        items = OrderItem.objects.filter(
            id__in=item_ids,
            order__user=user
        )
        
        if project_id: 
            project = Project.objects.get(id=project_id, user=user)
        elif project_name: 
            project = Project.objects.create(
                user=user,
                name=project_name,
                description=data.get('project_description', '')
            )
        else:
            return JsonResponse({'success': False, 'message': 'Invalid request'})
        
        project.order_items.add(*items)
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def digi_become_seller(request):
    if request.user.is_digi_seller:
        messages.warning(request, "You are already a Seller")
        return redirect("dashboard_digiprenair")

    if request.method == "POST":
        name = request.POST.get("name")
        bio = request.POST.get("bio")
        portfolio = request.POST.get("portfolio")
        phone = request.POST.get("phone")
        skills = request.POST.get("skills")
        country = request.POST.get("country")
        samples = request.FILES.getlist("samples")

        user = request.user
        user.name = name
        user.phone_no = phone
        user.digi_description = bio
        user.digi_portfolio = portfolio
        user.digi_speciality = skills
        user.country = country
        user.digi_is_verified = False 
        user.is_digi_seller = True

        for sample in samples:
            user.digi_sample = sample 

        user.save()

        messages.success(
            request, "Congratulations, your Seller account has been approved!"
        )
        return redirect("upload_item_digiprenair")

    return render(request, "digi_prenair/become_seller.html")


# ------------------- Email Notifications -------------------
import smtplib
from django.core.mail import EmailMultiAlternatives

def send_email(to_email, subject, html_content, plain_text="This is a plain text fallback."):
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        print("✅ Email sent successfully.")
    except smtplib.SMTPAuthenticationError as e:
        print("❌ Authentication error:", e)
    except smtplib.SMTPConnectError as e:
        print("❌ Connection error:", e)
    except smtplib.SMTPRecipientsRefused as e:
        print("❌ Recipient refused:", e.recipients)
    except smtplib.SMTPException as e:
        print("❌ General SMTP error:", e)
    except Exception as e:
        print("❌ Other error:", e)


#  < ------------- payment Integration with stripe --------------->

stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def checkout(request):
    user = request.user
    cart_items = CartItem.objects.filter(cart__user=user)

    # Calculate total product price
    total_price = sum(
        item.product.effective_price() * item.quantity for item in cart_items
    )

    # Calculate maintenance fee (10%)
    maintenance_fee = total_price * Decimal("0.1")

    # Prepare line items for Stripe
    line_items = [
        {
            "price_data": {
                "currency": "usd",
                "product_data": {"name": item.product.title},
                "unit_amount": int(
                    item.product.effective_price() * 100
                ),  # Effective price in cents
            },
            "quantity": item.quantity,
        }
        for item in cart_items
    ]

    line_items.append(
        {
            "price_data": {
                "currency": "usd",
                "product_data": {"name": "Platform Maintenance Fee"},
                "unit_amount": int(maintenance_fee * 100),
            },
            "quantity": 1,
        }
    )

    try:
        success_url = request.build_absolute_uri(reverse("digi_purchases") + "?new_order=true")
        cancel_url = request.build_absolute_uri(reverse("digi_shoping_cart"))

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": user.id},
        )

        # Redirect to the Stripe checkout page
        return redirect(checkout_session.url, code=303)

    except Exception as e:
        return render(request, "error.html", {"error": str(e)})


@csrf_exempt
def my_stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET_PRODUCT
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        print(str(e))
        return JsonResponse({"error": str(e)}, status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")

        if user_id:
            user = get_object_or_404(User, id=user_id)
            cart = get_object_or_404(Cart, user_id=user_id)
            cart_items = cart.items.all()

            total_amount = sum(
                item.quantity * item.product.effective_price() for item in cart_items
            )

            order = Order.objects.create(
                user_id=user_id, total_amount=total_amount, is_paid=True
            )

            # Collect product info for admin notification
            products_info = []
            sellers_info = {}  # Store seller info by product
            for cart_item in cart_items:
                product = cart_item.product
                quantity = cart_item.quantity
                product_price = product.effective_price()
                seller = product.seller
                products_info.append({
                    'title': product.title,
                    'quantity': quantity,
                    'price': product_price,
                    'total': quantity * product_price,
                    'seller_name': seller.username,
                    'seller_id': seller.id
                })

            for cart_item in cart_items:
                product = cart_item.product
                quantity = cart_item.quantity
                product_price = product.effective_price()
                commission_rate = Decimal("0.12")  # Commission as Decimal
                commission = product_price * commission_rate  # 12% commission
                seller_earning = (
                    product_price - commission
                )  # Amount after deducting commission

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product_price,
                )

                # Update the item_sales count for the sold product
                product.item_sales += quantity
                product.save()

                # Update the seller's digi_total_sales count and earnings
                seller = product.seller
                seller.digi_total_sales += quantity
                seller.digi_total_earnings += quantity * seller_earning
                seller.total_earnings += quantity * seller_earning
                seller.available_earnings += quantity * seller_earning
                seller.save()
                Notification.objects.create(
                    user=seller,
                    message=f"Your Item {product.title} has been purchased",
                    app_name="digiprenair",
                )

                buyer_url = request.build_absolute_uri(reverse("digi_purchases"))

                # Send email notification to the buyer
                buyer_email_content = f"""
                                        <html>
                                        <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
                                            <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                                                <!-- Header -->
                                                <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                                                    <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                                                </div>

                                                <!-- Body -->
                                                <div style="padding: 20px;">
                                                    <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🛒 Order Confirmed! Your Purchase #{order.id} is Ready</h2>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {user.username},</p>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                                                        Thank you for your purchase on <strong>FirePrenair</strong>! 🎉 Your order has been successfully processed.
                                                    </p>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Order Details:</strong></p>
                                                    <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                                                        <li style="margin-bottom: 10px;"><strong>Order ID:</strong> {order.id}</li>
                                                        <li style="margin-bottom: 10px;"><strong>Product/Service:</strong> {product.title}</li>
                                                        <li style="margin-bottom: 10px;"><strong>Total Amount:</strong> ${product.price}</li>
                                                    </ul>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Your order is now active! You can download your purchased product from the link below:</p>
                                                    <p style="text-align: center; margin: 20px 0;">
                                                        <a href="{buyer_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">View Details</a>
                                                    </p>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Need help? Our support team is always here for you.</p>
                                                </div>

                                                <!-- Footer -->
                                                <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                                                    <p style="margin: 0; font-size: 14px;">Thank you for choosing FirePrenair! 🚀</p>
                                                </div>
                                            </div>
                                        </body>
                                        </html>
                                    """

                send_email(
                    user.email,
                    f"🛒 Order Confirmed! Your Digital Product Order #{order.id} is Purchased!",
                    buyer_email_content,
                )
                seller_url = request.build_absolute_uri(reverse("digi_dashboard"))

                # Send email notification to the seller
                seller_email_content = f"""
                                        <html>
                                        <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
                                            <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                                                <!-- Header -->
                                                <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                                                    <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                                                </div>

                                                <!-- Body -->
                                                <div style="padding: 20px;">
                                                    <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🎉 Congratulations! Your Product #{product.id} Has Been Purchased</h2>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {seller.username},</p>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                                                        We are excited to inform you that your product <strong>{product.title}</strong> has been successfully purchased on <strong>FirePrenair</strong>! 🎉
                                                    </p>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Order Details:</strong></p>
                                                    <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                                                        <li style="margin-bottom: 10px;"><strong>Order ID:</strong> {order.id}</li>
                                                        <li style="margin-bottom: 10px;"><strong>Product/Service:</strong> {product.title}</li>
                                                        <li style="margin-bottom: 10px;"><strong>Total Amount:</strong> ${product.price}</li>
                                                    </ul>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">You can view the details of this order and manage your products from your seller dashboard:</p>
                                                    <p style="text-align: center; margin: 20px 0;">
                                                        <a href="{seller_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">View Dashboard</a>
                                                    </p>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Need help? Our support team is always here for you.</p>
                                                </div>

                                                <!-- Footer -->
                                                <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                                                    <p style="margin: 0; font-size: 14px;">Thank you for being a valued seller on FirePrenair! 🚀</p>
                                                </div>
                                            </div>
                                        </body>
                                        </html>
                                    """

                try:
                    send_email(
                        seller.email,
                        f"🎉 Congratulations! Your Product #{product.id} Has Been Purchased",
                        seller_email_content,
                    )
                    print(
                        f"Email sent successfully to user:{user.email} and seller:{seller.email}"
                    )
                except Exception as e:
                    print(f"Error sending email: {e}")

            # Build products HTML for admin email
            products_html = ""
            for product_info in products_info:
                products_html += f"""
                <div style="background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #1e3a8a;">
                    <p style="margin: 5px 0;"><strong>Product:</strong> {product_info['title']}</p>
                    <p style="margin: 5px 0;"><strong>Seller:</strong> {product_info['seller_name']} (ID: {product_info['seller_id']})</p>
                    <p style="margin: 5px 0;"><strong>Quantity:</strong> {product_info['quantity']}</p>
                    <p style="margin: 5px 0;"><strong>Price per item:</strong> ${product_info['price']}</p>
                    <p style="margin: 5px 0;"><strong>Subtotal:</strong> ${product_info['total']}</p>
                </div>
                """

            # Send email notification to all admins
            admin_email_content = f"""
                                    <html>
                                    <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
                                        <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                                            <!-- Header -->
                                            <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                                                <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                                            </div>

                                            <!-- Body -->
                                            <div style="padding: 20px;">
                                                <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">📊 New Sale Notification - Order #{order.id}</h2>
                                                <p style="color: #333; font-size: 16px; line-height: 1.6;">Hello Admin,</p>
                                                <p style="color: #333; font-size: 16px; line-height: 1.6;">
                                                    A new sale has been completed on <strong>FirePrenair</strong>! 🎉
                                                </p>
                                                
                                                <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Buyer Information:</strong></p>
                                                <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                                                    <li style="margin-bottom: 10px;"><strong>Username:</strong> {user.username}</li>
                                                    <li style="margin-bottom: 10px;"><strong>Email:</strong> {user.email}</li>
                                                    <li style="margin-bottom: 10px;"><strong>User ID:</strong> {user.id}</li>
                                                </ul>

                                                <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Order Summary:</strong></p>
                                                <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                                                    <li style="margin-bottom: 10px;"><strong>Order ID:</strong> {order.id}</li>
                                                    <li style="margin-bottom: 10px;"><strong>Total Amount:</strong> ${total_amount}</li>
                                                    <li style="margin-bottom: 10px;"><strong>Order Date:</strong> {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}</li>
                                                </ul>

                                                <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Products Sold:</strong></p>
                                                {products_html}

                                                <p style="color: #333; font-size: 16px; line-height: 1.6; margin-top: 20px;">
                                                    This is an automated notification for administrative purposes.
                                                </p>
                                            </div>

                                            <!-- Footer -->
                                            <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                                                <p style="margin: 0; font-size: 14px;">FirePrenair Administration</p>
                                            </div>
                                        </div>
                                    </body>
                                    </html>
                                """

            # Send email to all admin emails
            admin_emails = ['shoutdel@gmail.com', 'fireprenair@gmail.com', 'zainaligondal121@gmail.com']
            for admin_email in admin_emails:
                try:
                    send_email(
                        admin_email,
                        f"📊 New Sale Completed - Order #{order.id}",
                        admin_email_content,
                    )
                    print(f"Admin notification sent to: {admin_email}")
                except Exception as e:
                    print(f"Error sending admin email to {admin_email}: {e}")

            cart.items.all().delete()

            messages.success(request, "Payment was successful!")
    return JsonResponse({"status": "success"})


#  < ------------- payment Integration with paypal --------------->

import paypalrestsdk
from paypalrestsdk import Payment
from django.shortcuts import redirect

# Configure PayPal
paypalrestsdk.configure(
    {
        "mode": settings.PAYPAL_MODE,  # "sandbox" or "live"
        "client_id": settings.PAYPAL_CLIENT_ID,
        "client_secret": settings.PAYPAL_CLIENT_SECRET,
    }
)


@login_required
def paypal_checkout(request):
    user = request.user
    cart_items = CartItem.objects.filter(cart__user=user)

    # Calculate total product price
    total_price = sum(
        item.product.effective_price() * item.quantity for item in cart_items
    )

    # Calculate maintenance fee (5%)
    maintenance_fee = total_price * Decimal("0.1")
    total_price_with_fee = total_price + maintenance_fee

    # Prepare PayPal payment
    payment = Payment(
        {
            "intent": "sale",
            "payer": {
                "payment_method": "paypal",
            },
            "redirect_urls": {
                "return_url": request.build_absolute_uri(
                    reverse("paypal_payment_success")
                ),
                "cancel_url": request.build_absolute_uri(reverse("digi_shoping_cart")),
            },
            "transactions": [
                {
                    "item_list": {
                        "items": [
                            {
                                "name": item.product.title,
                                "sku": str(item.product.id),
                                "price": f"{item.product.effective_price():.2f}",
                                "currency": "USD",
                                "quantity": item.quantity,
                            }
                            for item in cart_items
                        ]
                        + [
                            {
                                "name": "Platform Maintenance Fee",
                                "sku": "maintenance_fee",
                                "price": f"{maintenance_fee:.2f}",
                                "currency": "USD",
                                "quantity": 1,
                            }
                        ],
                    },
                    "amount": {
                        "total": f"{total_price_with_fee:.2f}",
                        "currency": "USD",
                    },
                    "description": "Purchase from DigiPrenair",
                }
            ],
        }
    )

    if payment.create():
        for link in payment.links:
            if link.rel == "approval_url":
                # Redirect the user to PayPal for payment approval
                return redirect(link.href)
    else:
        return render(request, "profiles/error.html", {"error": payment.error})


@csrf_exempt
def paypal_payment_success(request):
    payment_id = request.GET.get("paymentId")
    payer_id = request.GET.get("PayerID")

    if not payment_id or not payer_id:
        return render(
            request, "profiles/error.html", {"error": "Missing payment information"}
        )

    payment = Payment.find(payment_id)

    if payment.execute({"payer_id": payer_id}):
        # Fetch user and process the order
        user = request.user
        cart = get_object_or_404(Cart, user=user)
        cart_items = cart.items.all()

        total_amount = sum(
            item.quantity * item.product.effective_price() for item in cart_items
        )

        # Create an order
        order = Order.objects.create(user=user, total_amount=total_amount, is_paid=True)

        for cart_item in cart_items:
            product = cart_item.product
            quantity = cart_item.quantity
            product_price = product.effective_price()
            commission_rate = Decimal("0.12")  # Commission as Decimal
            commission = product_price * commission_rate  # 12% commission
            seller_earning = (
                product_price - commission
            )  # Amount after deducting commission

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=product_price,
            )

            # Update the item_sales count for the sold product
            product.item_sales += quantity
            product.save()

            # Update the seller's digi_total_sales count and earnings
            seller = product.seller
            seller.digi_total_sales += quantity
            seller.digi_total_earnings += quantity * seller_earning
            seller.available_earnings += quantity * seller_earning
            seller.save()
            Notification.objects.create(
                user=seller,
                message=f"Your Item {product.title} has been purchased",
                app_name="digiprenair",
            )

            buyer_url = request.build_absolute_uri(reverse("digi_purchases"))

            # Send email notification to the buyer
            buyer_email_content = f"""
                                        <html>
                                        <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
                                            <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                                                <!-- Header -->
                                                <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                                                    <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                                                </div>

                                                <!-- Body -->
                                                <div style="padding: 20px;">
                                                    <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🛒 Order Confirmed! Your Purchase #{order.id} is Ready</h2>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {user.username},</p>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                                                        Thank you for your purchase on <strong>FirePrenair</strong>! 🎉 Your order has been successfully processed.
                                                    </p>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Order Details:</strong></p>
                                                    <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                                                        <li style="margin-bottom: 10px;"><strong>Order ID:</strong> {order.id}</li>
                                                        <li style="margin-bottom: 10px;"><strong>Product/Service:</strong> {product.title}</li>
                                                        <li style="margin-bottom: 10px;"><strong>Total Amount:</strong> ${product.price}</li>
                                                    </ul>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Your order is now active! You can download your purchased product from the link below:</p>
                                                    <p style="text-align: center; margin: 20px 0;">
                                                        <a href="{buyer_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">View Details</a>
                                                    </p>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Need help? Our support team is always here for you.</p>
                                                </div>

                                                <!-- Footer -->
                                                <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                                                    <p style="margin: 0; font-size: 14px;">Thank you for choosing FirePrenair! 🚀</p>
                                                </div>
                                            </div>
                                        </body>
                                        </html>
                                    """

            send_email(
                user.email,
                f"🛒 Order Confirmed! Your Digital Product Order #{order.id} is Purchased!",
                buyer_email_content,
            )
            seller_url = request.build_absolute_uri(reverse("digi_dashboard"))

            # Send email notification to the seller
            seller_email_content = f"""
                                        <html>
                                        <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
                                            <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                                                <!-- Header -->
                                                <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                                                    <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                                                </div>

                                                <!-- Body -->
                                                <div style="padding: 20px;">
                                                    <h2 style="color: #1e3a8a; font-size: 24px; text-align: center;">🎉 Congratulations! Your Product #{product.id} Has Been Purchased</h2>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Hi {seller.username},</p>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">
                                                        We are excited to inform you that your product <strong>{product.title}</strong> has been successfully purchased on <strong>FirePrenair</strong>! 🎉
                                                    </p>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;"><strong>Order Details:</strong></p>
                                                    <ul style="color: #333; font-size: 16px; line-height: 1.6; list-style: none; padding: 0;">
                                                        <li style="margin-bottom: 10px;"><strong>Order ID:</strong> {order.id}</li>
                                                        <li style="margin-bottom: 10px;"><strong>Product/Service:</strong> {product.title}</li>
                                                        <li style="margin-bottom: 10px;"><strong>Total Amount:</strong> ${product.price}</li>
                                                    </ul>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">You can view the details of this order and manage your products from your seller dashboard:</p>
                                                    <p style="text-align: center; margin: 20px 0;">
                                                        <a href="{seller_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">View Dashboard</a>
                                                    </p>
                                                    <p style="color: #333; font-size: 16px; line-height: 1.6;">Need help? Our support team is always here for you.</p>
                                                </div>

                                                <!-- Footer -->
                                                <div style="background-color: #1e3a8a; color: #fff; text-align: center; padding: 10px;">
                                                    <p style="margin: 0; font-size: 14px;">Thank you for being a valued seller on FirePrenair! 🚀</p>
                                                </div>
                                            </div>
                                        </body>
                                        </html>
                                    """

            try:
                send_email(
                    seller.email,
                    f"🎉 Congratulations! Your Product #{product.id} Has Been Purchased",
                    seller_email_content,
                )
                print(
                    f"Email sent successfully to user:{user.email} and seller:{seller.email}"
                )
            except Exception as e:
                print(f"Error sending email: {e}")

        cart.items.all().delete()
        messages.success(request, "Payment was successful!")
        return redirect("digi_purchases")
    else:
        return render(request, "profiles/error.html", {"error": payment.error})


# < ------------- Categories --------------->


def get_subcategories(request, category_id):
    level_2_categories = Category.objects.filter(parent_id=category_id)

    data = []
    for category in level_2_categories:
        children = category.digi_subcategories.all()
        child_data = [
            {"id": child.id, "name": child.name, "url": f"#"} for child in children
        ]
        data.append({"id": category.id, "name": category.name, "children": child_data})

    return JsonResponse({"level_2_categories": data})
