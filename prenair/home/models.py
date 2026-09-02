from django.db import models
from profiles.models import CustomUser as User
from django.utils.text import slugify
from django.urls import reverse
from django.utils import timezone

# Create your models here.

class Subscribe(models.Model):
    email = models.EmailField()
    name = models.CharField(max_length=100)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
    

class Feature(models.Model):
    DATA_TYPE_CHOICES = [
        ('boolean', 'Yes/No'),
        ('integer', 'Number'),
        ('string', 'Text'),
        ('unlimited', 'Unlimited')
    ]
    
    name = models.CharField(max_length=100)
    key = models.SlugField(max_length=100, unique=True, blank=True, null=True)  # e.g. "product_limit"
    description = models.TextField(blank=True, null=True)
    data_type = models.CharField(max_length=10, choices=DATA_TYPE_CHOICES)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class PlanFeature(models.Model):
    plan = models.ForeignKey("PricingPlan", on_delete=models.CASCADE, related_name='plan_features', default=1)
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE)
    value = models.CharField(max_length=400)

    class Meta:
        unique_together = ('plan', 'feature')

    def __str__(self):
        return f"{self.plan.title} - {self.feature.name}"
    

class PricingPlan(models.Model):
    title = models.CharField(max_length=100)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)  
    price_annual = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    
    # features
    access_to_dept = models.IntegerField(null=True, blank=True)
    ai_tools_limit = models.CharField(max_length=400, null=True, blank=True)
    product_limit = models.IntegerField(null=True, blank=True)
    service_limit = models.IntegerField(null=True, blank=True)
    support_limit = models.CharField(null=True, blank=True, max_length=400)

    # stripe 
    stripe_product_id = models.CharField(max_length=100, blank=True)
    stripe_price_id_monthly = models.CharField(max_length=100, blank=True)
    stripe_price_id_annual = models.CharField(max_length=100, blank=True)
    
    _original_price_monthly = None
    _original_price_annual = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_price_monthly = self.price_monthly
        self._original_price_annual = self.price_annual

    def __str__(self):
        return self.title
    
    def int_monthly_price(self):
        return int(self.price_monthly)
    
    def int_annual_price(self):
        return int(self.price_annual)
    
    def dec_monthly_price(self):
        return f"{int((self.price_monthly - int(self.price_monthly)) * 100):02d}"

    def dec_annual_price(self):
        return f"{int((self.price_annual - int(self.price_annual)) * 100):02d}"
    
    def monthly_price_cents(self):
        return int(self.price_monthly * 100)
    
    def annual_price_cents(self):
        return int(self.price_annual * 100)
    
    def has_price_monthly_changed(self):
        if not self.pk:  
            return True
        return self._original_price_monthly != self.price_monthly
    
    def has_price_annual_changed(self):
        if not self.pk:  
            return True
        return self._original_price_annual != self.price_annual


    
class UserPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(PricingPlan, on_delete=models.CASCADE)
    stripe_subscription_id = models.CharField(max_length=100, null=True, blank=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    type = models.CharField(max_length=50, default="monthly", choices=(("monthly", "Monthly"), ("annual", "Annual")))
    status = models.CharField(max_length=50, default="active")  


    def __str__(self):
        return f"{self.user.username} has Purchased {self.plan.title}"
    

    def amount(self):
        return self.plan.price_monthly if self.type == "monthly" else self.plan.price_annual
    

    class Meta:
        ordering = ['-is_active', '-start_date']


class Promo(models.Model):
    code = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class BlogPost(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()
    featured_image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    excerpt = models.TextField(max_length=300, blank=True)
    published = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0)
    published_date = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog:post_detail', args=[self.slug])
    


class CorporateProject(models.Model):
    CATEGORY_CHOICES = [
        ('web_dev', 'Web Development'),
        ('mobile', 'Mobile Applications'),
        ('ui_ux', 'UI/UX Design'),
        ('ai_automation', 'AI & Automation'),
        ('digital_marketing', 'Digital Marketing'),
        ('content', 'Content & Copywriting'),
        ('ecommerce', 'E-Commerce'),
        ('data_analytics', 'Data & Analytics'),
        ('brand', 'Brand Identity'),
        ('video', 'Video & Motion'),
        ('cloud_devops', 'Cloud & DevOps'),
        ('consulting', 'Business Consulting'),
    ]

    BUDGET_CHOICES = [
        ('under_1k', 'Under $1,000'),
        ('1k_5k', '$1,000 – $5,000'),
        ('5k_20k', '$5,000 – $20,000'),
        ('20k_50k', '$20,000 – $50,000'),
        ('50k_plus', '$50,000+'),
        ('custom', 'Custom / Let\'s Discuss'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('scoping', 'In Scoping'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='corporate_projects')
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    budget = models.CharField(max_length=20, choices=BUDGET_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.title}"

    def get_category_display_label(self):
        return dict(self.CATEGORY_CHOICES).get(self.category, self.category)

    def get_budget_display_label(self):
        return dict(self.BUDGET_CHOICES).get(self.budget, self.budget)


class ChatThread(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    thread_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name}'s Thread created on {self.created_at}"
