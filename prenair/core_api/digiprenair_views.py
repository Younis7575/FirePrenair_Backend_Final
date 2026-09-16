from django.shortcuts import render, get_object_or_404, redirect
from .models import *
from profiles.models import CustomUser
from django.contrib.auth.decorators import login_required
from django.urls import reverse
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

# payment Integration with stripe
import stripe
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import PermissionDenied

# Create your views here.


# ai
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.safestring import mark_safe
import markdown
from groq import Groq


######
from django.shortcuts import render, redirect
from .models import *
from django.core.exceptions import ValidationError
from django.contrib import messages
from edu_prenair.models import *
from digi_prenair.models import *
from work_prenair.models import Category as WorkCategory, Gig
from commu_prenair.models import Groupcategory, Group, Post
from django.conf import settings


# ai 
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.safestring import mark_safe
import markdown
from groq import Groq





from commu_prenair.models import *
from django.views.decorators.csrf import csrf_exempt
from django.utils.text import slugify
import uuid
import json
from edu_prenair.decorators import authenticated_user_required_commu,authenticated_user_required_commu_api
from django.conf import settings
from django.contrib.auth.decorators import login_required
from profiles.models import Notification

# ai 
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.safestring import mark_safe
import markdown
from groq import Groq

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
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser,JSONParser
from .serializers import *
from django.utils.decorators import method_decorator
from django.db.models import Q
######
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import logout
from rest_framework.permissions import AllowAny

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


@api_view(["POST"])
@permission_classes([AllowAny])
def digiprenair_chatbot_view_api(request):
    user_message = request.data.get("message", "").lower()

    # Predefined responses for quick replies
    predefined_responses = {
        "name": "I am your customer support assistant, here to help you with any questions about Workprenair.",
        "who_created_you": "I was created by the development team of Digiprenair.",
        "what_can_you_do": "I can help you navigate our platform, answer questions about our services, and provide consultation details.",
    }

    for key, response in predefined_responses.items():
        if key in user_message:
            return Response({"message": response})

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

    return Response({"message": bot_reply_html}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view_api(request):
    logout(request)
    return Response({"detail": "Logged out successfully."}, status=status.HTTP_200_OK)


class DigiHomeAPIView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        categories = Category.objects.all()
        featured_items = Product.objects.filter(is_featured=True)[:10]
        featured_sellers = CustomUser.objects.filter(
            is_digi_seller=True, digi_is_featured=True
        )[:5]
        newest_items = Product.objects.order_by("-created_at")[:20]

        context = {
            "categories": digiCategorySerializer(categories, many=True).data,
            "featured_items": ProductSerializer(featured_items, many=True).data,
            "featured_sellers": UserSerializer(featured_sellers, many=True).data,
            "newest_items": ProductSerializer(newest_items, many=True).data,
        }
        return Response(context)

class DigiExploreAPIView(APIView):
    def get(self, request):
        search_term = request.GET.get("q")
        category_param = request.GET.get("params", "all")
        category_id = request.GET.get("category")

        all_items = Product.objects.all()

        if category_id:
            all_items = all_items.filter(
                Q(category__id=category_id) |
                Q(category_l_2_id=category_id) |
                Q(category_l_3_id=category_id)
            )

        if category_param != "all":
            all_items = all_items.filter(category__slug=category_param)

        if search_term:
            all_items = all_items.filter(
                Q(title__icontains=search_term) | Q(description__icontains=search_term)
            )

        order = request.GET.get("order")
        if order == "newest-to-oldest":
            all_items = all_items.order_by("-created_at")
        elif order == "oldest-to-newest":
            all_items = all_items.order_by("created_at")

        paginator = Paginator(all_items, 10)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        categories = Category.objects.all()

        context = {
            "page_obj": {
                "count": paginator.count,
                "num_pages": paginator.num_pages,
                "current_page": page_obj.number,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
                "results": ProductSerializer(page_obj, many=True).data,
            },
            "categories": digiCategorySerializer(categories, many=True).data,
            "search_term": search_term,
            "selected_category": category_param,
        }
        return Response(context)



@api_view(['GET'])
def product_search_api_api(request):
    search_term = request.GET.get('q') or request.GET.get('params')
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
            'image': product.image.url if product.image else '',
            'description': product.description[:100] + '...' if product.description else '',
            'price': str(product.price),
            'discounted_price': str(product.discounted_price),
            'url': reverse('digi_product', kwargs={'slug': product.slug}),
            'slug': product.slug
        })
        
    return Response({'results': results})

@api_view(['GET'])
def digi_sellers_api(request):
    sellers = CustomUser.objects.filter(is_digi_seller=True)

    verified = request.GET.get("verified")
    order = request.GET.get("order")
    location = request.GET.get("location")

    if verified == "verified-creators-only":
        sellers = sellers.filter(digi_is_verified=True)

    if location:
        sellers = sellers.filter(country__iexact=location)

    if order == "order-by-name":
        sellers = sellers.order_by("username")  # Order by name (A-Z)
    elif order == "order-by-registration-date":
        sellers = sellers.order_by("-digi_total_sales")  # Order by number of sales

    paginator = Paginator(sellers, 10)  # Show 10 sellers per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    sellers_data = []
    for seller in page_obj:
        sellers_data.append({
            "id": seller.id,
            "username": seller.username,
            "country": seller.country,
            "digi_total_sales": seller.digi_total_sales,
            "digi_is_verified": seller.digi_is_verified,
        })

    return Response({
        "page_obj": sellers_data,
        "current_order": order,
        "current_verified": verified,
        "location": location,
        "page_number": page_obj.number,
        "total_pages": paginator.num_pages,
    })



@api_view(['GET', 'POST'])
def digi_product_api(request, slug):
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
        in_cart = CartItem.objects.filter(cart__user=request.user, product=product).exists()
        already_purchased = OrderItem.objects.filter(order__user=request.user, product=product, order__is_paid=True).exists()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if user_review_exists:
            return Response({'error': 'You have already reviewed this product.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = DigiReviewSerializer(data=request.data)
        if serializer.is_valid():
            review = serializer.save(product=product, user=request.user)

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

            return Response({'message': 'Review submitted successfully.'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    # GET request part (return full product details)
    product_data = {
        "id": product.id,
        "title": product.title,
        "description_html": description_html,
        "price": str(product.price),
        "discounted_price": str(product.discounted_price),
        "image_url": product.image.url if product.image else None,
        "seller_username": product.seller.username,
        "slug": product.slug,
    }

    reviews_data = []
    for review in reviews:
        reviews_data.append({
            "user": review.user.username,
            "rating": review.rating,
            "body": review.body,
            "created_at": review.created_at,
        })

    prev_product_data = {
        "title": prev_product.title,
        "slug": prev_product.slug,
    } if prev_product else None

    next_product_data = {
        "title": next_product.title,
        "slug": next_product.slug,
    } if next_product else None

    response_data = {
        "product": product_data,
        "reviews": reviews_data,
        "user_review_exists": user_review_exists,
        "is_product_owner": is_product_owner,
        "in_cart": in_cart,
        "already_purchased": already_purchased,
        "prev_product": prev_product_data,
        "next_product": next_product_data,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response_data['modal'] = True
    else:
        response_data['modal'] = False

    return Response(response_data)




@api_view(['GET'])
@permission_classes([AllowAny])
def digi_profile_api(request, slug):
    seller = get_object_or_404(CustomUser, slug=slug, is_digi_seller=True)
    products = Product.objects.filter(seller=seller)

    paginator = Paginator(products, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    serialized_products = ProductSerializer(page_obj, many=True).data
    seller_data = UserSerializer(seller).data

    response_data = {
        "seller": seller_data,
        "products": serialized_products,
        "pagination": {
            "current_page": page_obj.number,
            "total_pages": paginator.num_pages,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
        }
    }
    return Response(response_data, status=status.HTTP_200_OK)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def digi_shoping_cart_api(request):
    user = request.user
    cart, create = Cart.objects.get_or_create(user=user)
    cart_items = cart.items.all()

    # Calculate total price for the cart
    total_price = sum(item.quantity * item.product.effective_price() for item in cart_items)

    # Serialize the data
    serialized_items = CartItemSerializer(cart_items, many=True).data
    serialized_cart = CartSerializer(cart).data

    # Response data
    response_data = {
        "cart": serialized_cart,
        "cart_items": serialized_items,
        "total_price": total_price,
    }

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart_api(request, slug):
    product = get_object_or_404(Product, slug=slug)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if not created:
        # If item already exists in cart, increase the quantity
        cart_item.quantity += 1
        cart_item.save()

    # Serialize the cart item to send back as response
    serialized_cart_item = CartItemSerializer(cart_item).data

    return Response({
        'message': f'{product.title} has been added to your cart.',
        'cart_item': serialized_cart_item
    }, status=status.HTTP_200_OK)



@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_from_cart_api(request, slug):
    product = get_object_or_404(Product, slug=slug)
    cart = get_object_or_404(Cart, user=request.user)
    
    cart_item = CartItem.objects.filter(cart=cart, product=product).first()
    
    if cart_item:
        cart_item.delete()

    return Response({
        'message': f'`{product.title}` has been removed from your cart.'
    }, status=status.HTTP_200_OK)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def digi_notifications_api(request):
    notifications = request.user.notifications.filter(app_name="digiprenair").order_by("-created_at")    
    results = []
    for notification in notifications:
        results.append({
            'message': notification.message,
            'created_at': notification.created_at.strftime("%B %d, %Y %H:%M"),
            'is_read': notification.is_read,
        })

    return Response({
        'notifications': results
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_as_read_api(request, notification_id):
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )
    
    notification.is_read = True
    notification.save()

    return Response({
        'message': 'Notification marked as read successfully.',
        'notification_id': notification.id,
        'is_read': notification.is_read
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_notification_api(request, notification_id):
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )    
    notification.delete()
    return Response({
        'message': 'Notification deleted successfully.',
        'notification_id': notification_id
    }, status=status.HTTP_204_NO_CONTENT)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_as_read_api(request):
    notifications = request.user.notifications.filter(app_name="digiprenair", is_read=False)    
    notifications.update(is_read=True)
    return Response({
        'message': 'All notifications have been marked as read.'
    }, status=status.HTTP_200_OK)



@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def digi_profile_info_api(request):
    user = request.user
    
    # GET request: Return user's profile information
    if request.method == 'GET':
        serializer = UserSerializer(user)
        return Response(serializer.data)

    # PATCH request: Update the user's profile information
    if request.method == 'PATCH':
        serializer = ProfileUpdateSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            if 'username' in serializer.changed_data:
                user.is_username_changed = True  # Handle custom logic if username is changed
            serializer.save()
            return Response({
                'message': 'Your profile has been updated successfully!'
            }, status=status.HTTP_200_OK)

        return Response({
            'message': 'Please correct the errors below.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def digi_profile_settings_api(request):
    user = request.user

    # Handle password change
    if request.method == 'POST':
        # Check if 'password' fields are present in the request
        if 'old_password' in request.data and 'new_password' in request.data:
            serializer = CustomPasswordChangeSerializer(user, data=request.data)

            if serializer.is_valid():
                serializer.save()

                update_session_auth_hash(request, user)

                return Response({
                    'message': 'Your password was successfully updated!'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response({
                'message': 'Invalid request. Please provide old password and new password.'
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def digi_dashboard_api(request):
    user = request.user
    if not user.is_digi_seller:
        return Response({"error": "You are not a seller. Access denied."}, status=status.HTTP_403_FORBIDDEN)

    total_items_listed = user.digi_total_items
    total_items_sold = user.digi_total_sales
    total_sales_amount = user.digi_total_earnings

    recent_sales = OrderItem.objects.filter(product__seller=user).order_by(
        "-order__created_at"
    )

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
        )
        monthly_earnings.append(earnings)
        months.append(month_start.strftime("%B %Y"))

    paginator = Paginator(recent_sales, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    data = {
        "total_items_listed": total_items_listed,
        "total_items_sold": total_items_sold,
        "total_sales_amount": total_sales_amount,
        "monthly_earnings": list(reversed(monthly_earnings)),  # Reverse to make chronological
        "months": list(reversed(months)),  # Reverse to make chronological
        # "recent_sales": [
        #     {
        #         "product_title": item.product.title,
        #         "quantity": item.quantity,
        #         "total_amount": item.order.total_amount,
        #         "order_date": item.order.created_at.strftime("%B %d, %Y"),
        #     }
        #     for item in page_obj
        # ],
        "page_number": page_number,
        "total_pages": page_obj.paginator.num_pages,
    }

    return Response(data, status=status.HTTP_200_OK)





@api_view(['POST'])
def digi_upload_item_api(request):
    user = request.user

    if not user.is_digi_seller:
        raise PermissionDenied("You are not a seller. Access denied.")

    if request.method == "POST":
        serializer = ProductUploadSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save(seller=user)
            return Response({"message": "Product uploaded successfully", "product_id": product.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def digi_manage_items_api(request):
    user = request.user

    if not user.is_digi_seller:
        raise PermissionDenied("You are not a seller. Access denied.")
    products = Product.objects.filter(seller=user)
    serializer = ProductSerializer(products, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def edit_item_api(request, slug):
    user = request.user

    if not user.is_digi_seller:
        raise PermissionDenied("You are not a seller. Access denied.")

    product = get_object_or_404(Product, slug=slug)

    serializer = ProductSerializer(product, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response({"detail": "Product updated successfully!"}, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def digi_purchases_api(request):
    user = request.user
    orders = Order.objects.filter(user=user, is_paid=True)
    
    data = [
        {
            "order_id": order.id,
            "total_amount": order.total_amount,
            "created_at": order.created_at,
            "status": "Paid" if order.is_paid else "Pending",
            # you can expand more fields if you want
        }
        for order in orders
    ]
    
    return Response({"orders": data})



@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def digi_become_seller_api(request):
    """Apply to sell on DigiPrenair, mirroring `digi_prenair.views`.

    The website answers a GET by either bouncing an existing seller to their
    dashboard or rendering the application form pre-filled from the account.
    Only POST existed here, so a client had no way to ask "am I a seller?" and
    had to guess — which is why the app's "Become a Seller" link went straight
    to the upload screen for everyone.
    """
    user = request.user

    if request.method == "GET":
        return Response(
            {
                "is_seller": user.is_digi_seller,
                "is_verified": user.digi_is_verified,
                # The form's Name field is pre-filled on the website; the rest
                # are sent back so a re-application is not typed from scratch.
                "prefill": {
                    "name": user.name or "",
                    "phone": user.phone_no or "",
                    "country": user.country or "",
                    "skills": user.digi_speciality or "",
                    "portfolio": user.digi_portfolio or "",
                    "bio": user.digi_description or "",
                },
            },
            status=status.HTTP_200_OK,
        )

    if user.is_digi_seller:
        return Response(
            {"detail": "You are already a Seller."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = BecomeSellerSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data

        user.name = data.get("name")
        user.phone_no = data.get("phone")
        user.digi_description = data.get("bio")
        user.digi_portfolio = data.get("portfolio", "")
        user.digi_speciality = data.get("skills")
        user.country = data.get("country")
        user.digi_is_verified = False
        user.is_digi_seller = True

        samples = data.get("samples", [])
        if samples:
            user.digi_sample = samples[0]  # Save only the first sample

        user.save()

        return Response(
            {"detail": "Congratulations, your Seller account request has been submitted!"},
            status=status.HTTP_201_CREATED,
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_email(to_email, subject, html_content):
    message = Mail(
        from_email="support@fireprenair.com",
        to_emails=to_email,
        subject=subject,
        html_content=html_content,
    )
    try:
        sg = SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        sg.send(message)
    except Exception as e:
        print(f"Error sending email: {e}")

#  < ------------- payment Integration with stripe --------------->

stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def checkout_api(request):
    user = request.user
    cart_items = CartItem.objects.filter(cart__user=user)

    # Calculate total product price
    total_price = sum(
        item.product.effective_price() * item.quantity for item in cart_items
    )

    # Calculate maintenance fee (5%)
    maintenance_fee = total_price * Decimal("0.05")

    # Prepare line items for Stripe
    line_items = [
        {
            "price_data": {
                "currency": "usd",
                "product_data": {"name": item.product.title},
                "unit_amount": int(item.product.effective_price() * 100),
            },
            "quantity": item.quantity,
        }
        for item in cart_items
    ]

    # Add maintenance fee line
    line_items.append({
        "price_data": {
            "currency": "usd",
            "product_data": {"name": "Platform Maintenance Fee"},
            "unit_amount": int(maintenance_fee * 100),
        },
        "quantity": 1,
    })

    try:
        success_url = request.build_absolute_uri(reverse("digi_purchases"))
        cancel_url = request.build_absolute_uri(reverse("digi_shoping_cart"))
        # success_url='Redirect to digi purchases'
        # cancel_url='Redirect to digi shopping cart'

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": user.id},
        )

        return Response(
            {"checkout_url": checkout_session.url},
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(["POST"])
@permission_classes([AllowAny])  # Webhooks don't need auth
def my_stripe_webhook_api(request):
    
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET_PRODUCT
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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

            for cart_item in cart_items:
                product = cart_item.product
                quantity = cart_item.quantity
                product_price = product.effective_price()
                commission_rate = Decimal("0.12")
                commission = product_price * commission_rate
                seller_earning = product_price - commission

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product_price,
                )

                product.item_sales += quantity
                product.save()

                seller = product.seller
                seller.digi_total_sales += quantity
                seller.digi_total_earnings += quantity * seller_earning
                seller.save()

                Notification.objects.create(
                    user=seller,
                    message=f"Your Item {product.title} has been purchased",
                    app_name="digiprenair",
                )

                # Email: Buyer
                buyer_url = request.build_absolute_uri(reverse("digi_purchases"))
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

                # Email: Seller
                seller_url = request.build_absolute_uri(reverse("digi_dashboard"))
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
                    print(f"Email sent to user: {user.email} and seller: {seller.email}")
                except Exception as e:
                    print(f"Error sending email: {e}")

            cart.items.all().delete()

    return Response({"status": "Payment was successul"}, status=status.HTTP_200_OK)

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

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def paypal_checkout_api(request):
    user = request.user
    cart_items = CartItem.objects.filter(cart__user=user)

    if not cart_items.exists():
        return Response(
            {"detail": "Your cart is empty."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Calculate pricing
    total_price = sum(
        item.product.effective_price() * item.quantity for item in cart_items
    )
    maintenance_fee = total_price * Decimal("0.05")
    total_price_with_fee = total_price + maintenance_fee

    # Build item list for PayPal
    items = [
        {
            "name": item.product.title,
            "sku": str(item.product.id),
            "price": f"{item.product.effective_price():.2f}",
            "currency": "USD",
            "quantity": item.quantity,
        }
        for item in cart_items
    ]
    items.append(
        {
            "name": "Platform Maintenance Fee",
            "sku": "maintenance_fee",
            "price": f"{maintenance_fee:.2f}",
            "currency": "USD",
            "quantity": 1,
        }
    )

    # Validate data with serializer
    serializer = CheckoutSerializer(data={
        "items": items,
        "maintenance_fee": maintenance_fee,
        "total_price": total_price_with_fee,
    })

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Create PayPal payment
    payment = Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal",
        },
        "redirect_urls": {
            "return_url": request.build_absolute_uri(reverse("paypal_payment_success")),
            "cancel_url": request.build_absolute_uri(reverse("digi_shoping_cart")),
        },
        "transactions": [
            {
                "item_list": {"items": serializer.validated_data["items"]},
                "amount": {
                    "total": f"{serializer.validated_data['total_price']:.2f}",
                    "currency": "USD",
                },
                "description": "Purchase from DigiPrenair",
            }
        ],
    })

    if payment.create():
        for link in payment.links:
            if link.rel == "approval_url":
                return Response({"approval_url": link.href}, status=status.HTTP_200_OK)
        return Response({"detail": "Approval URL not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(
        {"detail": "Error creating PayPal payment.", "error": payment.error},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def paypal_payment_success_api(request):
    payment_id = request.GET.get("paymentId")
    payer_id = request.GET.get("PayerID")

    if not payment_id or not payer_id:
        return Response(
            {"error": "Missing payment information"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    payment = Payment.find(payment_id)

    if payment.execute({"payer_id": payer_id}):
        user = request.user
        cart = get_object_or_404(Cart, user=user)
        cart_items = cart.items.all()

        total_amount = sum(
            item.quantity * item.product.effective_price() for item in cart_items
        )

        order = Order.objects.create(user=user, total_amount=total_amount, is_paid=True)

        for cart_item in cart_items:
            product = cart_item.product
            quantity = cart_item.quantity
            product_price = product.effective_price()
            commission_rate = Decimal("0.12")
            commission = product_price * commission_rate
            seller_earning = product_price - commission

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=product_price,
            )

            product.item_sales += quantity
            product.save()

            seller = product.seller
            seller.digi_total_sales += quantity
            seller.digi_total_earnings += quantity * seller_earning
            seller.save()

            Notification.objects.create(
                user=seller,
                message=f"Your Item {product.title} has been purchased",
                app_name="digiprenair",
            )

            buyer_url = request.build_absolute_uri(reverse("digi_purchases"))

            buyer_email_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
                    <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                        <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                            <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                        </div>
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
                            <p style="text-align: center; margin: 20px 0;">
                                <a href="{buyer_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">View Details</a>
                            </p>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">Need help? Our support team is always here for you.</p>
                        </div>
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

            seller_email_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f4f9;">
                    <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);">
                        <div style="background-color: #1e3a8a; padding: 20px; text-align: center;">
                            <img src="https://fireprenair.s3.amazonaws.com/images/misc/fireprenair_logo.png" alt="FirePrenair Logo" style="max-width: 150px;">
                        </div>
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
                            <p style="text-align: center; margin: 20px 0;">
                                <a href="{seller_url}" style="background-color: #ff6f61; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-size: 16px;">View Dashboard</a>
                            </p>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">Need help? Our support team is always here for you.</p>
                        </div>
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

        return Response(
            {"message": "Payment was successful!"},
            status=status.HTTP_200_OK,
        )
    else:
        return Response(
            {"error": payment.error},
            status=status.HTTP_400_BAD_REQUEST,
        )
        
        
# < ------------- Categories --------------->
     
        
@api_view(['GET'])
@permission_classes([AllowAny])
def digi_get_subcategories_api(request, category_id):
    level_2_categories = Category.objects.filter(parent_id=category_id)

    data = []
    for category in level_2_categories:
        children = category.digi_subcategories.all()
        child_data = [
            {"id": child.id, "name": child.name, "url": "#"} for child in children
        ]
        data.append({"id": category.id, "name": category.name, "children": child_data})

    return Response({"level_2_categories": data})



# getch integration

import requests
from rest_framework.authtoken.models import Token
from django.core.files.base import ContentFile
from digi_prenair.models import Category as DigiCat

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def create_product_from_getch(request):
    # 1. auth
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Token "):
        return Response({"error": "Missing or invalid Authorization header"}, status=status.HTTP_401_UNAUTHORIZED)

    token_key = auth_header.split(" ")[1]
    try:
        token = Token.objects.get(key=token_key)
        user = token.user
    except Token.DoesNotExist:
        return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

    # 2. extract data from request
    title = request.data.get("title")
    description = request.data.get("description", "")
    price = request.data.get("price")
    template_id = request.data.get("templateId")

    # Required fields check
    if not title or not price:
        return Response({"error": "Title and price are required."}, status=400)

    # 3: Process image URL or file
    thumbnail_url = request.data.get("thumbnail_url")
    product_file = request.data.get("download_file") # This can be a URL or an uploaded file

    image_file = None
    if thumbnail_url:
        try:
            img_response = requests.get(thumbnail_url)
            if img_response.status_code == 200:
                img_name = f"{slugify(title)}-thumb.jpg"
                image_file = ContentFile(img_response.content, name=img_name)
        except Exception as e:
            print("Thumbnail fetch failed:", e)

    file_field = None
    if product_file and not isinstance(product_file, str):
        file_field = product_file  # already an uploaded file
    elif isinstance(product_file, str):
        try:
            file_response = requests.get(product_file)
            if file_response.status_code == 200:
                file_ext = os.path.splitext(product_file)[-1]
                file_name = f"{slugify(title)}-file{file_ext}"
                file_field = ContentFile(file_response.content, name=file_name)
        except Exception as e:
            print("File download failed:", e)

    # 4: Create product with defaults
    try:
        product = Product.objects.create(
            title=title,
            description=description,
            price=price,
            seller=user,
            category=DigiCat.objects.get(id=66),  # 66
            category_l_2=DigiCat.objects.get(id=67), # 67
            category_l_3=DigiCat.objects.get(id=399), #399
            image=image_file,
            downloadable_file=file_field,
            softwares="Getch",
            size="",
            files_included="Zip file",
        )

        return Response({
            "message": "Product created successfully.",
            "product_id": product.id
        })

    except Exception as e:
        return Response({"error": str(e)}, status=500)