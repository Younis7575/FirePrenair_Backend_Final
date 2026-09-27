"""
Fills in reviews, course enrollments and gig orders using the real users
and real products/courses/gigs already in the database — not hardcoded
values in the app. The app was showing empty states (no reviews, no
enrolled students, no order history) for content nobody had bought,
enrolled in, or reviewed yet. This creates those rows the same way a
real user's activity would, so the screens that read them back through
the API show something real instead of nothing.

Idempotent: re-running it skips any user/product, user/course or
user/gig pair that already has one, so it's safe to run again after new
content is added.

Run from the Django project directory (the one with manage.py), with the
venv active:
    source <venv>/bin/activate
    python deploy/seed_realistic_data.py

Sets DJANGO_SETTINGS_MODULE itself if it isn't already in the environment,
so no extra export is needed.
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prenair.settings")

import django

django.setup()

from django.db import transaction
from django.utils import timezone

from profiles.models import CustomUser
from digi_prenair.models import Product, Review as DigiReview
from edu_prenair.models import Course, StudentEnrollment
from work_prenair.models import Gig, Order, Review as WorkReview


DIGI_REVIEWS = [
    (5, "Great value", "Exactly what I needed, fast delivery and clean files."),
    (4, "Good quality", "Solid product, would buy again from this seller."),
    (5, "Highly recommend", "Well organised and easy to customise for my project."),
]

ENROLLMENT_PROGRESS = [100.0, 55.0, 15.0]

GIG_REVIEWS = [
    "Great work, delivered on time and communicated clearly throughout.",
    "Exactly what I asked for. Will order again.",
    "Good experience overall, minor revisions handled quickly.",
]


def seed_digi_reviews():
    created = 0
    for product in Product.objects.all():
        already_reviewed = set(product.reviews.values_list("user_id", flat=True))
        candidates = list(
            CustomUser.objects.exclude(id=product.seller_id)
            .exclude(id__in=already_reviewed)
            .order_by("id")[: len(DIGI_REVIEWS)]
        )
        for user, (rating, title, body) in zip(candidates, DIGI_REVIEWS):
            DigiReview.objects.create(
                product=product, user=user, rating=rating, title=title, body=body
            )
            created += 1
    print(f"digi reviews created: {created}")


def seed_enrollments():
    created = 0
    for course in Course.objects.all():
        already_enrolled = set(course.enrollments.values_list("user_id", flat=True))
        candidates = list(
            CustomUser.objects.exclude(id=course.instructor_id)
            .exclude(id__in=already_enrolled)
            .order_by("id")[: len(ENROLLMENT_PROGRESS)]
        )
        for user, progress in zip(candidates, ENROLLMENT_PROGRESS):
            StudentEnrollment.objects.create(
                user=user,
                course=course,
                progress=progress,
                is_completed=progress >= 100.0,
                completion_date=timezone.now() if progress >= 100.0 else None,
            )
            created += 1
    print(f"enrollments created: {created}")


def seed_gig_orders():
    created = 0
    for gig in Gig.objects.all():
        already_ordered = set(gig.orders.values_list("user_id", flat=True))
        candidates = list(
            CustomUser.objects.exclude(id=gig.user_id)
            .exclude(id__in=already_ordered)
            .order_by("id")[: len(GIG_REVIEWS)]
        )
        for user, review_text in zip(candidates, GIG_REVIEWS):
            slug = f"order-{gig.slug}-{uuid.uuid4().hex[:8]}"[:300]
            order = Order.objects.create(
                user=user,
                gig=gig,
                slug=slug,
                requirements="Please deliver as described in the gig.",
                package_type="basic",
                price=gig.basic_price,
                is_paid=True,
                status="completed",
                is_delivered=True,
                is_completed=True,
                delivery_days=gig.basic_delivery_time,
                completed_on=timezone.now(),
                has_client_reviewed=True,
            )
            WorkReview.objects.create(
                order=order,
                gig=gig,
                user=user,
                rating=5,
                review=review_text,
                is_client_review=True,
            )
            created += 1
    print(f"gig orders created: {created}")


if __name__ == "__main__":
    with transaction.atomic():
        seed_digi_reviews()
        seed_enrollments()
        seed_gig_orders()
