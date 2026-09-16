from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from edu_prenair.models import Course
from .models import Notification, CustomUser
from dashboard.models import *
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from work_prenair.models import *
from home.models import PricingPlan, UserPlan
import stripe
from django.conf import settings

@receiver(post_save, sender=Notification)
def send_notification_to_user(sender, instance, created, **kwargs):
    """
    Send a notification to the user when a new notification is created.
    """
    if created:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{instance.user.id}",
            {
                "type": "send_notification",
                "content": {
                    "message": instance.message,
                    "app_name": instance.app_name
                }
            }
        )

@receiver(pre_save, sender=Course)
def detect_publish_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            previous = Course.objects.get(pk=instance.pk)
            instance._previous_is_published = previous.is_published
        except Course.DoesNotExist:
            instance._previous_is_published = False
    else:
        instance._previous_is_published = False

@receiver(post_save, sender=Course)
def notify_users_on_course_published(sender, instance, created, **kwargs):
    if not created and instance.is_published and not instance._previous_is_published:
        users = CustomUser.objects.all() 
        for user in users:
            Notification.objects.create(
                user=user,
                message=f"A new course '{instance.title}' has been published.",
                app_name="eduprenair"
            )




def update_user_badge(user):
    """Update user's badge based on predefined criteria."""
    completed_projects = user.user_completed_orders
    earnings = user.work_total_earnings
    rating = user.user_avg_work_rating

    new_level = 1
    if completed_projects >= 30 and earnings >= 5000 and rating >= 4.0:
        new_level = 4
    elif completed_projects >= 15 and earnings >= 2000 and rating >= 3.5:
        new_level = 3
    elif completed_projects >= 2 and earnings >= 500 and rating >= 3.5:
        new_level = 2

    badge, created = Badge.objects.get_or_create(user=user)
    if badge.level != new_level:
        badge.level = new_level
        badge.save()



@receiver(post_save, sender=Order)
@receiver(post_save, sender=Review)
@receiver(post_save, sender=CustomUser)
def update_badge_on_activity(sender, instance, **kwargs):
    if isinstance(instance, CustomUser):
        update_user_badge(instance)  
    else:
        update_user_badge(instance.user)



# ----------------------- Stripe Product Creation / Updation --------------------------------#
stripe.api_key = settings.STRIPE_SECRET_KEY

@receiver(post_save, sender=PricingPlan)
def sync_pricing_plan_with_stripe(sender, instance, created, **kwargs):
    # Without Stripe credentials every call below raises, which made saving a
    # PricingPlan impossible at all on a local/dev setup — the admin, fixtures
    # and the seed command all failed before the row could be written. Skip
    # the sync instead; the plan is still stored, only checkout is unavailable.
    if not stripe.api_key:
        print(
            'Stripe not configured (STRIPE_SECRET_KEY is empty) — saved '
            f'pricing plan "{instance.title}" without syncing prices.'
        )
        instance._original_price_monthly = instance.price_monthly
        instance._original_price_annual = instance.price_annual
        return

    needs_save = False
    product = None

    if not instance.stripe_product_id:
        product = stripe.Product.create(name=instance.title)
        instance.stripe_product_id = product.id
        needs_save = True

    monthly_changed = instance.has_price_monthly_changed()
    print("Change in Monthly: ", monthly_changed)
    if created or monthly_changed or product:
        if instance.stripe_price_id_monthly:
            stripe.Price.modify(instance.stripe_price_id_monthly, active=False)

        monthly_price = stripe.Price.create(
            unit_amount=instance.monthly_price_cents(),
            currency="usd",
            recurring={"interval": "month"},
            product=instance.stripe_product_id,
        )
        instance.stripe_price_id_monthly = monthly_price.id
        needs_save = True

    annual_changed = instance.has_price_annual_changed()
    print("Change in Annual: ", annual_changed)
    if created or annual_changed or product:
        if instance.stripe_price_id_annual:
            stripe.Price.modify(instance.stripe_price_id_annual, active=False)

        annual_price = stripe.Price.create(
            unit_amount=instance.annual_price_cents(),
            currency="usd",
            recurring={"interval": "year"},
            product=instance.stripe_product_id,
        )
        instance.stripe_price_id_annual = annual_price.id
        needs_save = True

    if needs_save:
        post_save.disconnect(sync_pricing_plan_with_stripe, sender=PricingPlan)
        instance.save()
        post_save.connect(sync_pricing_plan_with_stripe, sender=PricingPlan)

    instance._original_price_monthly = instance.price_monthly
    instance._original_price_annual = instance.price_annual




@receiver(post_save, sender=User)
def assign_default_plan(sender, instance, created, **kwargs):
    if created:
        try:
            free_plan = PricingPlan.objects.get(title__iexact="FreeTier")
            UserPlan.objects.create(
                user=instance,
                plan=free_plan,
                type="monthly", 
                is_active=True,
                status="active"
            )
        except PricingPlan.DoesNotExist:
            print("Default FreeTier plan not found.")
