from django.db import models
from profiles.models import CustomUser as User
from django.utils import timezone
# Create your models here.

class PayoutAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payout_account")
    type = models.CharField(max_length=50, choices=[('Payoneer', 'Payoneer'),('Stripe', 'Stripe'), ('Paypal', 'Paypal')], default='Payoneer')
    email = models.EmailField(null=True, blank=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Payoneer Account"


class WithdrawalRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="withdrawals")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, choices=[
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed')
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    payout_type = models.CharField(max_length=50, choices=[('Payoneer', 'Payoneer'),('Stripe', 'Stripe'), ('Paypal', 'Paypal')], default='Payoneer')
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} requested withdrawal of ${self.amount}"
    
    def get_payoneer_info(self):
        return self.user.payout_account.filter(type='Payoneer').first()
    
    def get_paypal_info(self):
        return self.user.payout_account.filter(type='Paypal').first()


class TrafficLog(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    url = models.CharField(max_length=500)
    referrer = models.CharField(max_length=500, blank=True)
    country = models.CharField(max_length=100, blank=True)
    device_type = models.CharField(max_length=50)
    client_ip = models.GenericIPAddressField(null=True, blank=True)
    is_staff = models.BooleanField(default=False)  # filter internal traffic
    
    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['country']),
            models.Index(fields=['client_ip']),
        ]
    def __str__(self):
        return f"{self.timestamp} - {self.url} - {self.country} - {self.device_type} - {self.client_ip}"
    


class TemplateCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    def __str__(self):
        parent_name = "None" if self.parent is None else self.parent.name
        return f"{self.name} - Parent: {parent_name}"

    class Meta:
        verbose_name_plural = "Template Categories"


class Template(models.Model):
    name = models.CharField(max_length=255)
    html_content = models.TextField()
    thumbnail = models.ImageField(upload_to='template_thumbnails/')
    category = models.ForeignKey(TemplateCategory, on_delete=models.SET_NULL, null=True, related_name='templates')

    def __str__(self):
        return f"{self.name}: Category: {self.category.name if self.category else 'No Category'}"


class UserWebsite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, null=True, blank=True)
    template = models.ForeignKey(Template, on_delete=models.SET_NULL, null=True)
    edited_html = models.TextField()
    is_published = models.BooleanField(default=False)
    subdomain = models.CharField(max_length=255, unique=True, blank=True, null=True)
    custom_domain = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.name if self.name else 'No Name'}"


class Funnel(models.Model):
    TAG_CHOICES = [
        ('ebooks', 'Ebooks'),
        ('courses', 'Courses'),
        ('logo', 'Logo'),
        ('Website_templates', 'Website Templates'),
        ('web_dev', 'Web Development'),
        ('digital_products', 'Digital Products'),
        ('marketing', 'Marketing'),
        ('custom', 'Custom'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="funnels")
    name = models.CharField(max_length=255)
    visitors = models.ManyToManyField(User, blank=True, related_name="visited_funnels")
    department = models.CharField(max_length=100)
    tag = models.CharField(max_length=50, choices=TAG_CHOICES, default='ebooks')
    custom_tag = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=False)
    subdomain = models.CharField(max_length=255, unique=True, blank=True, null=True)
    custom_domain = models.CharField(max_length=255, blank=True, null=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_next_step(self, current_step_order):
        return self.steps.filter(step_order__gt=current_step_order).order_by('step_order').first()
    
    def get_products(self):
        return self.products.filter(is_active=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class FunnelStep(models.Model):
    GOAL_CHOICES = [
        ('visit', 'Visit'),
        ('form_submit', 'Form Submit'),
        ('purchase', 'Purchase')
    ]

    funnel = models.ForeignKey(Funnel, on_delete=models.CASCADE, related_name="steps")
    user_website = models.ForeignKey(UserWebsite, on_delete=models.CASCADE)
    step_order = models.IntegerField()
    goal_type = models.CharField(max_length=50, choices=GOAL_CHOICES)

    def get_next_step(self):
        return self.funnel.get_next_step(self.step_order)


    def __str__(self):
        return f"Step {self.step_order} of {self.funnel.name}"
    

class FunnelProduct(models.Model):
    funnel = models.ForeignKey(Funnel, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_price_id = models.CharField(max_length=255, blank=True, null=True)  # created via Stripe API
    downloadable_file = models.FileField(upload_to='funnel_products/files/', blank=True, null=True,help_text="Upload a file (eBook, PDF, ZIP, etc.) that buyers will receive after purchase.")
    external_link = models.URLField(blank=True, null=True, help_text="Optional external link (e.g. Google Drive, Flipbook, or membership area).")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def has_downloads(self):
        return bool(self.downloadable_file or self.external_link)

    def __str__(self):
        return f"{self.name} - ${self.price}"


class FunnelOrder(models.Model):
    ORDER_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    funnel = models.ForeignKey(Funnel, on_delete=models.CASCADE, related_name="orders")
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="funnel_orders")
    product = models.ForeignKey(FunnelProduct, on_delete=models.SET_NULL, null=True)
    stripe_payment_intent = models.CharField(max_length=255, null=True, blank=True)
    stripe_session_id = models.CharField(max_length=255, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, choices=ORDER_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.buyer.username} - {self.product.name if self.product else 'N/A'}"


class FunnelLead(models.Model):
    funnel = models.ForeignKey(Funnel, on_delete=models.CASCADE, related_name="leads")
    name = models.CharField(max_length=255)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.email}) - {self.funnel.name}"


class KYCProfile(models.Model):
    IDENTITY_TYPE_CHOICES = [
        ('passport', 'Passport'),
        ('national_id', 'National ID'),
        ('drivers_license', "Driver's License"),
        ('other', 'Other'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="kyc_profile")
    identity_type = models.CharField(max_length=50, choices=IDENTITY_TYPE_CHOICES, blank=True, null=True)
    identity_number = models.CharField(max_length=100, blank=True, null=True)
    identity_country = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"KYC Profile for {self.user.username}"
    
    class Meta:
        verbose_name = "KYC Profile"
        verbose_name_plural = "KYC Profiles"