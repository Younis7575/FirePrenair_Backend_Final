from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.utils.text import slugify
from django.db.models import Avg
from django.db.models import Q
from django.utils import timezone   
import stripe
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Avg
from django.apps import apps
import zoneinfo


# Create your models here.
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("user", "User"),
    ]

    GENDER = [
        ("male", "Male",),
        ("female", "Female",),
    ]

    CUSTOMER_TYPE = [
        ("individual", "Individual"),
        ("company", "Company"),
    ]

    IDENTITY_TYPE_CHOICES = [
        ("passport", "Passport"),
        ("national_id", "National ID"),
        ("drivers_license", "Driver's License"),
        ("other", "Other"),
    ]
    
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    name = models.CharField(max_length=150, null=True, blank=True)
    slug = models.SlugField(max_length=150, unique=True, null=True, blank=True)
    bio = models.TextField(blank=True, null=True)
    profile_pic = models.ImageField(upload_to="profile_pics/", blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="user")
    gender = models.CharField(max_length=10, choices=GENDER, blank=True, null=True)

    # customer details
    phone_no = models.CharField(max_length=15, blank=True, null=True)
    country = models.CharField(max_length=150, blank=True, null=True)
    city = models.CharField(max_length=150, blank=True, null=True)
    province = models.CharField(max_length=150, blank=True, null=True)
    postal_code = models.CharField(max_length=15, blank=True, null=True)
    identity_type = models.CharField(max_length=50, choices=IDENTITY_TYPE_CHOICES, blank=True, null=True)
    identity_number = models.CharField(max_length=100, blank=True, null=True)
    customer_type = models.CharField(max_length=150, blank=True, null=True, choices=CUSTOMER_TYPE)
    company_name = models.CharField(max_length=150, blank=True, null=True)
    company_number = models.CharField(max_length=15, blank=True, null=True)
    tax_number = models.CharField(max_length=15, blank=True, null=True)
    
    
    age = models.PositiveIntegerField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_username_changed = models.BooleanField(default=False)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
    # stripe_payment_method_id = models.CharField(max_length=255, blank=True, null=True)

    total_earnings = models.DecimalField(max_digits=100, decimal_places=2, default=0.00)
    available_earnings = models.DecimalField(max_digits=100, decimal_places=2, default=0.00)
    amount_being_cleared = models.DecimalField(max_digits=100, decimal_places=2, default=0.00)

    # eduprenair fields
    edu_bio = models.TextField(blank=True, null=True)
    is_edu_instructor = models.BooleanField(default=False)
    edu_total_earnings = models.DecimalField(
        max_digits=100, decimal_places=2, default=0.00
    )
    featured_instructor = models.BooleanField(default=False)

    # digiprenair fields
    is_digi_seller = models.BooleanField(default=False)
    digi_cover_photo = models.ImageField(
        upload_to="digiprenair_avatar/", blank=True, null=True
    )
    digi_speciality = models.CharField(max_length=150, blank=True)
    digi_total_items = models.IntegerField(default=0)
    digi_total_sales = models.IntegerField(default=0)
    digi_average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    digi_total_earnings = models.DecimalField(
        max_digits=100, decimal_places=2, default=0.00
    )
    digi_is_verified = models.BooleanField(default=False)
    digi_is_featured = models.BooleanField(default=False)
    digi_portfolio = models.URLField(max_length=200, blank=True, null=True)
    digi_speciality = models.CharField(max_length=150, blank=True)
    digi_sample = models.FileField(upload_to="digi_samples/", blank=True, null=True)
    digi_description = models.TextField(blank=True, null=True)


    #commuprenair fields
    commu_bio = models.CharField(max_length=500, null=True, blank=True)

    # corporate client flag
    is_corporate_client = models.BooleanField(default=False)

    # workprenair fields
    work_bio = models.TextField(blank=True, null=True)
    is_work_freelancer = models.BooleanField(default=False)
    work_expertise = models.CharField(max_length=150, blank=True)
    is_work_profile_approved = models.BooleanField(default=False)
    work_total_earnings = models.DecimalField(max_digits=100, decimal_places=2, default=0.00)
    portfolio_link = models.URLField(max_length=200, blank=True, null=True)

    language = models.CharField(max_length=10, choices=[('en', 'English'),('es', 'Spanish'),('fr', 'French'),('it', 'Italian'),('zh-hans', 'Simplified Chinese'),('ko', 'Korean'),('nl', 'Dutch'),], default='en')
    timezone = models.CharField(max_length=32, choices=[(tz, tz) for tz in zoneinfo.available_timezones()], default='UTC')

    referred_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals")
    has_listed_and_sold = models.BooleanField(default=False)
    referral_code = models.CharField(max_length=20, unique=True, null=True, blank=True)

    # relationships
    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.slug = slugify(self.username)
        if not self.pk and not self.stripe_customer_id and stripe.api_key:
            try:
                customer = stripe.Customer.create(
                    email=self.email,
                    name=self.username, 
                )
                self.stripe_customer_id = customer.id
            except Exception:
                self.stripe_customer_id = 'cus_dev_placeholder'
        super(CustomUser, self).save(*args, **kwargs)

    # digi_prenair helper methods
    # Add the method to calculate average rating
    def seller_average_rating(self):
        products = self.products.all()  # Get all products sold by the user
        if products.exists():
            # Aggregate the average rating of all products
            digi_average_rating = products.aggregate(Avg("rating"))["rating__avg"]
            return round(digi_average_rating, 1)  # Round to one decimal place
        return 0.0  # Return 0 if no products exist

    def edu_instrcutor_courses(self):
        return self.course_set.filter(is_published=True)

    def edu_instructor_courses_length(self):
        # get the course length in hours for the instructor
        courses = self.course_set.filter(is_published=True)
        total_hours = 0
        for course in courses:
            total_hours += course.duration
        return total_hours

    def edu_instructor_total_students(self):
        courses = self.course_set.filter(is_published=True)
        total_students = 0
        for course in courses:
            total_students += course.enrolled_students.count() - 1
        return total_students

    def instructor_courses_rating(self):
        courses = self.course_set.filter(is_published=True)
        overall_avg_rating = (
            courses.aggregate(average=Avg("courserating__rating"))["average"] or 0
        )
        return round(overall_avg_rating, 1)

    def instructor_course_categories(self):
        categories = (
            self.course_set.filter(is_published=True)
            .values_list(
                "category_l_1__name", 
                "category_l_2__name", 
                "category_l_3__name"
            )
            .distinct()
        )
        # Flatten the results and remove any None values
        flattened_categories = set(filter(None, [category for sublist in categories for category in sublist]))
        return list(flattened_categories)

    

    def mutual_connections(self, user):
        # Get connections of the current user (self)
        current_user_connections = CustomUser.objects.filter(
            Q(connections_sent__to_user=self) | Q(connections_received__from_user=self)
        )

        # Get connections of the other user
        other_user_connections = CustomUser.objects.filter(
            Q(connections_sent__to_user=user) | Q(connections_received__from_user=user)
        )

        # Return mutual connections by finding the intersection
        mutual_connections = current_user_connections & other_user_connections
        return mutual_connections
    

    def mutual_connections_count(self, user):
        return self.mutual_connections(user).count()
    
    def is_friend_request_pending(self, user):
        return self.friend_requests_sent.filter(to_user=user).exists()
    
    def is_friend_request_received(self, user):
        return self.friend_requests_received.filter(from_user=user).exists()
    

    def is_already_connected(self, user):
        return self.connections_sent.filter(to_user=user).exists() or \
               self.connections_received.filter(from_user=user).exists()
    
    def user_connections(self):
        return CustomUser.objects.filter(
            Q(connections_sent__to_user=self) | Q(connections_received__from_user=self)
        )
    

    def user_groups(self):
        return self.group_members.all()
    

    def friend_requests_received(self):
        return self.friend_requests_received.all()
    

    def get_all_chats(self):
            """
            Retrieve all chats where the user is either `user1` or `user2`.
            """
            return (self.chats1.filter(commu_prenair_chat=True) | self.chats2.filter(commu_prenair_chat=True)).distinct()
    

    def get_work_chats(self):
        return (self.chats1.filter(commu_prenair_chat=False) | self.chats2.filter(commu_prenair_chat=False)).distinct()
    
    def user_gigs(self):
        return self.gigs.all()
    
    def profile_completion_percentage(self):
        # Fields considered for profile completion
        fields_to_check = ['name', 'bio', 'profile_pic', 'phone_no', 'age', 'country']
        completed_fields = sum(1 for field in fields_to_check if getattr(self, field))
        total_fields = len(fields_to_check)
        return int((completed_fields / total_fields) * 100) if total_fields > 0 else 0
    
    def missing_profile_fields(self):
        # Fields considered for profile completion
        fields_to_check = ['name', 'bio', 'profile_pic', 'phone_no', 'age', 'country']
        # Return missing fields
        return [field for field in fields_to_check if not getattr(self, field)]
    
    def time_since_last_seen(self):
        if not self.last_seen:
            return "Never"

        delta = now() - self.last_seen

        if delta < timedelta(minutes=1):
            return "Just now"
        elif delta < timedelta(hours=1):
            minutes = int(delta.total_seconds() // 60)
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        elif delta < timedelta(days=1):
            hours = int(delta.total_seconds() // 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif delta < timedelta(weeks=1):
            days = delta.days
            return f"{days} day{'s' if days > 1 else ''} ago"
        elif delta < timedelta(days=30):
            weeks = delta.days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        elif delta < timedelta(days=365):
            months = delta.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = delta.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
        
    @property
    def user_completed_orders(self):
        return apps.get_model('work_prenair.Order').objects.filter(gig__user=self, status="completed").count()
    
    @property
    def user_avg_work_rating(self):
        reviews = apps.get_model('work_prenair.Review').objects.filter(gig__user=self)  # Get all reviews for this user's gigs
        avg_rating = reviews.aggregate(Avg("rating"))["rating__avg"]
        return round(avg_rating, 2) if avg_rating else 0
    
    def user_badge(self):
        return apps.get_model('work_prenair.Badge').objects.get(user=self) if apps.get_model('work_prenair.Badge').objects.filter(user=self).exists() else None
    
        

class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    is_message = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    app_name = models.CharField(max_length=100,blank=True, null=True, choices=[('digiprenair', 'Digiprenair'), ('eduprenair', 'Eduprenair'), ('commuprenair', 'Commuprenair'), ('workprenair', 'Workprenair')])

    def __str__(self):
        return f"Notification for {self.user.name} - {self.message[:20]}"
    
    class Meta:
        ordering = ['-created_at']