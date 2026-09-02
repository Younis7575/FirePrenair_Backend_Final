from django.db import models
from profiles.models import CustomUser as User
from django.utils.text import slugify
from django.core.validators import FileExtensionValidator
import random
from django.db.models import Q


# Create your models here.


class Category(models.Model):
    Colors = (
        ("ui-templates", "ui-templates"),
        ("video-tutorials", "video-tutorials"),
        ("coded-templates", "coded-templates"),
        ("social-graphics", "social-graphics"),
    )
    
    def get_random_color():
        return random.choice([color[0] for color in Category.Colors]) 
    
    name = models.CharField(max_length=100, unique=True, null=True, blank=True)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='digi_subcategories'
    )
    item_count = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    img = models.ImageField(upload_to='digi_prenair_category_images/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=100, choices=Colors, default=get_random_color)
    

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        if self.parent:
            return f"{self.parent.name or 'Unnamed'} > {self.name or 'Unnamed'}"
        return self.name or 'Unnamed'



class Product(models.Model):
    RATING_CHOICES = (
        (1, "1 Star"),
        (2, "2 Stars"),
        (3, "3 Stars"),
        (4, "4 Stars"),
        (5, "5 Stars"),
    )

    downloadable_file = models.FileField(
        upload_to="digiprenair_product_files/",
        validators=[FileExtensionValidator(allowed_extensions=["zip", "pdf"])],
        blank=True,
        null=True,
    )
    # S3 key for production: file is uploaded via presigned URL; we store only the key
    downloadable_file_s3_key = models.CharField(max_length=512, blank=True, null=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    slug = models.SlugField(unique=True, blank=True, max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products_category_l1", null=True, blank=True)
    category_l_2 = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products_category_l2", null=True, blank=True)
    category_l_3 = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products_category_l3", null=True, blank=True)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="products")
    image = models.ImageField(upload_to="digiprenair_product_images/")
    rating = models.IntegerField(choices=RATING_CHOICES, default=0)
    likes = models.IntegerField(default=0)
    item_sales = models.IntegerField(default=0)
    files_included = models.CharField(max_length=200, blank=True)
    softwares = models.CharField(max_length=200, blank=True)
    size = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_featured = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not self.slug:
            self.slug = slugify(self.title)
        if not self.image:
            self.image = "digiprenair_product_images/AI.jpg"
            self.downloadable_file = None
        super(Product, self).save(*args, **kwargs)

        if is_new:
            self.category.item_count += 1
            self.category.save()

            # Update the seller's digi_total_items
            self.seller.digi_total_items += 1
            self.seller.save()

    def delete(self, *args, **kwargs):
        # Decrease category item_count on product deletion
        category = self.category
        super(Product, self).delete(*args, **kwargs)
        category.item_count -= 1
        category.save()

    def five_star_rating(self):
        return self.reviews.filter(rating=5).count()

    def __str__(self):
        return self.title

    def update_average_rating(self):
        reviews = self.reviews.all()  # Get all reviews for this product
        if reviews.exists():
            average_rating = reviews.aggregate(models.Avg("rating"))["rating__avg"]
            self.rating = round(
                average_rating
            )  # Round the average rating to the nearest integer
        else:
            self.rating = 0  # No reviews, set rating to 0
        self.save()  # Save the updated product instance

    def effective_price(self):
        """Return the discounted price if available, otherwise the original price."""
        return self.discounted_price if self.discounted_price > 0 else self.price
    
    def next_product(self):
        """Get the next product by ID (assuming ascending order)."""
        return Product.objects.filter(id__gt=self.id).order_by('id').first()

    def previous_product(self):
        """Get the previous product by ID (assuming descending order)."""
        return Product.objects.filter(id__lt=self.id).order_by('-id').first()
    
    def related_products(self, limit=6):
        """Fetch related products based on category, seller, or similar titles."""
        related_queryset = Product.objects.filter(
            Q(category=self.category) | Q(seller=self.seller)
        ).exclude(id=self.id).distinct()

        # If we need more products, fetch similar title matches
        # if related_queryset.count() < limit:
        #     title_keywords = self.title.split()[:3]  # Use first 3 words as keywords
        #     title_query = Q()
        #     for word in title_keywords:
        #         title_query |= Q(title__icontains=word)
        #     extra_products = Product.objects.filter(title_query).exclude(id=self.id)
        #     related_queryset = related_queryset | extra_products

        return related_queryset.order_by("-created_at")[:limit]



class Review(models.Model):
    product = models.ForeignKey(
        "Product", on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    rating = models.IntegerField(
        choices=[(i, f"{i} Star") for i in range(1, 6)], default=5
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super(Review, self).save(*args, **kwargs)
        self.product.update_average_rating() 

    def __str__(self):
        return f"Review by {self.user.username} - {self.rating} Stars on {self.product.title}"


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart of {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product.title} in cart of {self.cart.user.username}"

    @property
    def total_price(self):
        return self.product.price * self.quantity
    
    
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)  
    
    def __str__(self):
        return f"Order by {self.user.username} for ${self.total_amount}"
    
    def order_items(self):
        return self.order_items.all()



class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2) 

    def __str__(self):
        return f"{self.quantity} x {self.product.title} for order {self.order.id}"
    
    
class Project(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order_items = models.ManyToManyField("OrderItem", related_name="projects",blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'name')

    def __str__(self):
        return f"{self.user.username}'s Project: {self.name}"