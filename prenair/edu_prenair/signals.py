from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CourseRating, StudentEnrollment
from profiles.models import Notification


@receiver(post_save, sender=CourseRating)
def create_review_notification(sender, instance, created, **kwargs):
    if created:  # Check if the review was just created
        Notification.objects.create(
            user=instance.course.instructor,  # Notify the instructor of the course
            message=f"{instance.user.username} left a {instance.rating}-star review on your course '{instance.course.title}'!",
            app_name="eduprenair"
        )


@receiver(post_save, sender=StudentEnrollment)
def create_purchase_notification(sender, instance, created, **kwargs):
    if created:  # Check if enrollment was just created
        Notification.objects.create(
            user=instance.course.instructor,  # Notify the instructor of the course
            message=f"{instance.user.username} purchased your course '{instance.course.title}'.",
            app_name="eduprenair"
        )
