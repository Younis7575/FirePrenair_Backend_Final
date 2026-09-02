from django.db import models
from profiles.models import CustomUser as User
from django.utils.text import slugify
import uuid
from django.utils.safestring import mark_safe
import re
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    is_featured = models.BooleanField(default=False)
    img = models.ImageField(upload_to='work_prenair_category_images/', blank=True, null=True)

    def __str__(self):
        if self.parent:
            return f"{self.parent} > {self.name}"
        return self.name
    
    def gig_count(self):
        return self.gigs_level_1.count() + self.gigs_level_2.count() + self.gigs_level_3.count()


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Gig(models.Model):
    # Basic gig details
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="gigs")
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    description = models.TextField()
    image = models.ImageField(upload_to='work_prenair_gig_images/')
    tags = models.ManyToManyField(Tag, related_name="gigs")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    top_rated = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)

    category_level_1 = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="gigs_level_1")
    category_level_2 = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="gigs_level_2")
    category_level_3 = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="gigs_level_3")

    # Basic package
    basic_name = models.CharField(max_length=100, default="Basic")
    basic_description = models.TextField()
    basic_delivery_time = models.PositiveIntegerField(help_text="Delivery time in days")
    basic_revisions = models.PositiveIntegerField(default=1)
    basic_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Standard package
    standard_name = models.CharField(max_length=100, default="Standard")
    standard_description = models.TextField()
    standard_delivery_time = models.PositiveIntegerField(help_text="Delivery time in days")
    standard_revisions = models.PositiveIntegerField(default=2)
    standard_price = models.DecimalField(max_digits=10, decimal_places=2)

    # Premium package
    premium_name = models.CharField(max_length=100, default="Premium")
    premium_description = models.TextField()
    premium_delivery_time = models.PositiveIntegerField(help_text="Delivery time in days")
    premium_revisions = models.PositiveIntegerField(default=3)
    premium_price = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.title = "I will " + self.title
        if not self.slug:
            self.slug = slugify(f"{self.title}-{self.user.username}")

        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.title} by {self.user.username}"
    
    def completed_orders(self):
        return self.orders.filter(status="completed")
    
    def active_orders(self):
        return self.orders.filter(status="active")
    
    def get_related_gigs(self):
        return Gig.objects.filter(category_level_1=self.category_level_1).exclude(id=self.id).order_by('?')[:6]
    
    def gig_reviews(self):
        return self.gig_work_reviews.filter(is_client_review=True)
    
    def reviews_5_star_percentage(self):
        reviews = self.gig_work_reviews.filter(is_client_review=True)
        if reviews:
            five_star_reviews = reviews.filter(rating=5)
            return int((len(five_star_reviews) / len(reviews)) * 100)
        return 0
    
    def reviews_4_star_percentage(self):
        reviews = self.gig_work_reviews.filter(is_client_review=True)
        if reviews:
            four_star_reviews = reviews.filter(rating=4)
            return (len(four_star_reviews) / len(reviews)) * 100
        return 0
    
    def reviews_3_star_percentage(self):
        reviews = self.gig_work_reviews.filter(is_client_review=True)
        if reviews:
            three_star_reviews = reviews.filter(rating=3)
            return (len(three_star_reviews) / len(reviews)) * 100
        return 0
    

    def reviews_2_star_percentage(self):
        reviews = self.gig_work_reviews.filter(is_client_review=True)
        if reviews:
            two_star_reviews = reviews.filter(rating=2)
            return (len(two_star_reviews) / len(reviews)) * 100
        return 0
    

    def reviews_1_star_percentage(self):
        reviews = self.gig_work_reviews.filter(is_client_review=True)
        if reviews:
            one_star_reviews = reviews.filter(rating=1)
            return (len(one_star_reviews) / len(reviews)) * 100
        return 0

    def gig_average_rating(self):
        reviews = self.gig_work_reviews.filter(is_client_review=True)
        if reviews:
            total = 0
            for review in reviews:
                total += review.rating
            return total / len(reviews)
        return 0
    
    def gig_fivestar_reviews(self):
        return self.gig_work_reviews.filter(rating=5)
    
    def get_package_name(self, package):
        return getattr(self, f"{package}_name", "")

    def get_package_description(self, package):
        return getattr(self, f"{package}_description", "")

    def get_package_delivery_time(self, package):
        return getattr(self, f"{package}_delivery_time", 0)

    def get_package_revisions(self, package):
        return getattr(self, f"{package}_revisions", 0)

    def get_package_price(self, package):
        return getattr(self, f"{package}_price", 0.0)
    
    def tags_count(self):
        return self.tags.count()
    
    def description_html(self):
        # get gig without html tags
        return mark_safe(re.sub(r'<[^>]*>', '', self.description))



class Order(models.Model):
    GIG_PACKAGE_CHOICES = [
        ("basic", "Basic"),
        ("standard", "Standard"),
        ("premium", "Premium"),
        ("custom_offer", "Custom Offer")
    ]

    ORDER_STATUS_CHOICES = [
        ("pending_requirements", "Pending Requirements"),
        ("active", "Active"),
        ("delivered", "Delivered"),
        ("completed", "Completed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    gig = models.ForeignKey('Gig', on_delete=models.CASCADE, related_name="orders")
    requirements = models.TextField(blank=True, null=True, help_text="Client must submit requirements before order becomes active.")
    slug = models.SlugField(max_length=300, unique=True, blank=True, null=True)
    package_type = models.CharField(
        max_length=100, choices=GIG_PACKAGE_CHOICES
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    status = models.CharField(max_length=30, choices=ORDER_STATUS_CHOICES, default="pending_requirements")
    is_delivered = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    delivery_date = models.DateTimeField(null=True, blank=True)
    delivery_days = models.PositiveIntegerField(default=0)
    completed_on = models.DateTimeField(null=True, blank=True)
    has_client_reviewed = models.BooleanField(default=False)
    has_seller_reviewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Order by {self.user.username} for {self.gig.title} ({self.package_type})"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            unique_id = uuid.uuid4()
            self.slug = slugify(f"Order-by-{self.user.username}-on-{self.gig.title}-{self.package_type}-{unique_id}")
        super().save(*args, **kwargs)


    def deliveries(self):
        return self.delivery.all()
    
    def client_reviews(self):
        return self.work_review.filter(is_client_review=True)
    
    def seller_review(self):
        return self.work_review.filter(is_client_review=False)
    
    def order_review(self):
        return self.work_review.all()



class Delivery(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="delivery")
    developer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="deliveries")
    message = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='work_prenair_deliveries/', blank=True, null=True)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Delivery for Order #{self.order.id}"
    
    def revisions(self):
        return self.revision_requests.all()


class RevisionRequest(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name="revision_requests")
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name="revision_requests")
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Revision for Delivery #{self.delivery.id} - {self.is_resolved}"


class Review(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="work_review")
    gig = models.ForeignKey(Gig, on_delete=models.CASCADE, related_name="gig_work_reviews", null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="work_reviews")
    rating = models.PositiveIntegerField()
    review = models.TextField()
    is_client_review = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for Order #{self.order.id}"
    




class CustomOffer(models.Model):
    # Linking the offer to a gig and its creator
    gig = models.ForeignKey('Gig', on_delete=models.CASCADE, related_name="custom_offers")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_offers")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_offers")
    
    # Offer details
    title = models.CharField(max_length=255)
    description = models.TextField()
    delivery_time = models.PositiveIntegerField(help_text="Delivery time in days")
    price = models.DecimalField(max_digits=10, decimal_places=2)

    # Status and timestamps
    is_accepted = models.BooleanField(default=False)
    is_declined = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Offer from {self.sender} to {self.recipient} for {self.gig.title}"


class Badge(models.Model):
    LEVEL_CHOICES = [
        (1, "Level 1"),
        (2, "Level 2"),
        (3, "Level 3"),
        (4, "Level 4"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    level = models.IntegerField(choices=LEVEL_CHOICES, default=1)
    awarded_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_level_display()}"
    
    def get_badge_image(self):
        return f"https://fireprenair.s3.amazonaws.com/images/misc/user_bage_{self.level}.png"



class Todo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="todos")
    title = models.CharField(max_length=255, unique=False, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} - {self.title}"


