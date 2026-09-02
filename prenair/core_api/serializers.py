# serializers.py
from rest_framework import serializers
from commu_prenair.models import *
from profiles.models import CustomUser,Notification

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        # fields = '__all__'
        fields = [
            "id","username","name","slug","bio","profile_pic","gender","age","date_of_birth",
            "country","city","province","customer_type","company_name","language","timezone","identity_type","identity_number",
            "commu_bio","edu_bio","is_edu_instructor","featured_instructor","digi_is_verified","digi_average_rating",
            "digi_is_featured","digi_speciality","digi_cover_photo","digi_portfolio","digi_description","work_bio",
            "is_work_freelancer","work_expertise","is_work_profile_approved","portfolio_link",
        ]

class UserDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        # fields = '__all__'
        fields = [
            "id","username","name","slug","bio","profile_pic","gender","age",
            "country","city","province","language","timezone",
            "commu_bio","edu_bio","featured_instructor","work_bio","digi_average_rating",
            "is_work_freelancer","work_expertise","is_work_profile_approved","portfolio_link",
        ]

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'username',
            'name',
            'phone_no',
            'digi_description',
            'country',
            'profile_pic',
            'digi_cover_photo',
            'digi_speciality',
            'digi_portfolio',
        ]
        extra_kwargs = {
            'digi_description': {'required': False},  # You can add more customizations like making fields optional if necessary
            'profile_pic': {'required': False},
            'digi_cover_photo': {'required': False},
        }

    # Optionally, you can define custom validations or methods if necessary
    def validate_phone_no(self, value):
        if not value or not value.strip():
            return value or ""
        if not value.replace(" ", "").replace("-", "").replace("+", "").isdigit():
            raise serializers.ValidationError("Phone number must be numeric")
        return value


class CommentSerializer(serializers.ModelSerializer):
    author=UserDataSerializer(read_only=True)
    class Meta:
        model = Comment
        fields = '__all__'

class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    comments=CommentSerializer(many=True, read_only=True)
    class Meta:
        model = Post
        fields = '__all__'
        
class GroupCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Groupcategory
        fields = '__all__'

class GroupSerializer(serializers.ModelSerializer):
    admin=UserDataSerializer(read_only=True)
    members=UserDataSerializer(read_only=True)
    class Meta:
        model = Group
        fields = '__all__'

class GroupMemberShipRequestsSerializer(serializers.ModelSerializer):
    user=UserDataSerializer(read_only=True)
    class Meta:
        model = GroupMemberShipRequests
        fields = '__all__'

class ConnectionSerializer(serializers.ModelSerializer):
    from_user =UserDataSerializer(read_only=True)
    to_user =UserDataSerializer(read_only=True)
    
    class Meta:
        model = Connection
        fields = '__all__'

class FriendRequestSerializer(serializers.ModelSerializer):
    from_user = UserDataSerializer(read_only=True)
    to_user = UserDataSerializer(read_only=True)
    class Meta:
        model = FriendRequest
        fields = '__all__'

class PrivateChatSerializer(serializers.ModelSerializer):
    user1=UserDataSerializer(read_only=True)
    user2=UserDataSerializer(read_only=True)
    class Meta:
        model = PrivateChat
        fields = '__all__'

class MessageSerializer(serializers.ModelSerializer):
    sender=UserDataSerializer(read_only=True)
    receiver=UserDataSerializer(read_only=True)
    class Meta:
        model = Message
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    user=UserDataSerializer(read_only=True)
    class Meta:
        model= Notification
        fields = '__all__'
#######################  work prenair serializers   ###########################################
from rest_framework import serializers
from profiles.models import CustomUser as User
from work_prenair.models import Category, Tag, Gig, Order, Delivery, RevisionRequest, Review, CustomOffer, Badge


class WorkCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class GigSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Gig
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    gig = GigSerializer(read_only=True)

    class Meta:
        model = Order
        fields = '__all__'


class DeliverySerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)
    developer = serializers.StringRelatedField()

    class Meta:
        model = Delivery
        fields = '__all__'


class RevisionRequestSerializer(serializers.ModelSerializer):
    delivery = DeliverySerializer(read_only=True)
    client = serializers.StringRelatedField()

    class Meta:
        model = RevisionRequest
        fields = '__all__'


class ReviewSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)
    gig = GigSerializer(read_only=True)
    user = serializers.StringRelatedField()

    class Meta:
        model = Review
        fields = '__all__'


class CustomOfferSerializer(serializers.ModelSerializer):
    gig = GigSerializer(read_only=True)
    sender = serializers.StringRelatedField()
    recipient = serializers.StringRelatedField()

    class Meta:
        model = CustomOffer
        fields = '__all__'


class BadgeSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = Badge
        fields = '__all__'




################################ EDU PRENAIR SERIALIZERS  #######################################
from edu_prenair.models import *

class CourseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseCategory
        fields = '__all__'
        
        
class CourseSerializer(serializers.ModelSerializer):
    instructor=UserDataSerializer(read_only=True)
    category_l_1 = CourseCategorySerializer(read_only=True)
    category_l_2 = CourseCategorySerializer(read_only=True)
    category_l_3 = CourseCategorySerializer(read_only=True)
    class Meta:
        model = Course
        fields = '__all__'
        
class ModuleSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    class Meta:
        model = Module
        fields = '__all__'
        
class LessonSerializer(serializers.ModelSerializer):
    module = ModuleSerializer(read_only=True)
    class Meta:
        model = Lesson
        fields = '__all__'

class StudentEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentEnrollment
        fields = '__all__'

class CourseRatingSerializer(serializers.ModelSerializer):
    user=UserDataSerializer(read_only=True)
    class Meta:
        model = CourseRating
        fields = '__all__'

class CourseWishlistSerializer(serializers.ModelSerializer):
    user=UserDataSerializer(read_only=True)
    class Meta:
        model = CourseWishlist
        fields = '__all__'
        
        
class CourseAnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseAnnouncement
        fields = '__all__'
        
class QuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = '__all__'
        
class QuizQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestion
        fields = '__all__'
        
class QuizAttemptSerializer(serializers.ModelSerializer):
    user=UserDataSerializer(read_only=True)
    class Meta:
        model = QuizAttempt
        fields = '__all__'

class QuizQuestionResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestionResponse
        fields = '__all__'
        
################################################ DIGI PRENAIR SERIALIZERS #####################################################fom 

from digi_prenair.models import Category as digiCategory
from digi_prenair.models import Product, Review, Cart, CartItem, Order, OrderItem

class digiCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = digiCategory
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    seller = UserDataSerializer()
    class Meta:
        model = Product
        fields = '__all__'
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.image:
            request = self.context.get('request')
            if request:
                data['image'] = request.build_absolute_uri(instance.image.url)
        return data


class DigiProductReviewSerializer(serializers.ModelSerializer):
    user=UserDataSerializer(read_only=True)
    class Meta:
        model = Review
        fields = '__all__'


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = '__all__'


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = '__all__'


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'


class DigiCheckoutOrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)
    user=UserDataSerializer(read_only=True)
    class Meta:
        model = Order
        fields = '__all__'
        
#######################################################---->Work prenair <-----################################################## 
from work_prenair.models import Category as WorkCategory, Tag, Gig, Order, Delivery, RevisionRequest, Review, CustomOffer, Badge, Todo

class WorkCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkCategory
        fields = '__all__'


class CategoryWithSubcategoriesSerializer(serializers.ModelSerializer):
    subcategories = serializers.SerializerMethodField()
    gig_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'parent', 'is_featured', 'img', 'gig_count', 'subcategories']
    
    def get_subcategories(self, obj):
        # Get all subcategories for this category
        subcategories = obj.subcategories.all()
        return [{
            'id': sub.id,
            'name': sub.name,
            'description': sub.description,
            'parent': sub.parent.id,
            'is_featured': sub.is_featured,
            'img': sub.img.url if sub.img else None,
            'gig_count': sub.gig_count(),
        } for sub in subcategories]




class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class GigSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Gig
        fields = '__all__'


class DeliverySerializer(serializers.ModelSerializer):
    developer = UserSerializer(read_only=True)

    class Meta:
        model = Delivery
        fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    gig = GigSerializer(read_only=True)
    work_review = ReviewSerializer(many=True, read_only=True)
    delivery = DeliverySerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = '__all__'

class DeliverySerializer(serializers.ModelSerializer):
    order_id = serializers.PrimaryKeyRelatedField(source='order', read_only=True)
    developer_id = serializers.PrimaryKeyRelatedField(source='developer', read_only=True)
    revisions = serializers.SerializerMethodField()

    class Meta:
        model = Delivery
        fields ='__all__'

    def get_revisions(self, obj):
        return [str(r) for r in obj.revisions()]  # You can customize this further



class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Review
        fields = '__all__'




class CustomOfferSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)
    gig = GigSerializer(read_only=True)

    class Meta:
        model = CustomOffer
        fields = '__all__'


class BadgeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Badge
        fields = '__all__'


class TodoSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Todo
        fields = '__all__'
        
        
        
################################################## dashboard ############################333
from dashboard.models import *


class PayoutAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutAccount
        fields = '__all__'


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequest
        fields = '__all__'


class TrafficLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrafficLog
        fields = '__all__'


        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
####################################################33
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class CustomPasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_new_password = serializers.CharField(required=True, write_only=True)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def validate_old_password(self, value):
        # Authenticate the user with the old password
        if not self.user.check_password(value):
            raise serializers.ValidationError("The old password is incorrect.")
        return value

    def validate(self, data):
        # Ensure new password and confirm new password match
        new_password = data.get('new_password')
        confirm_new_password = data.get('confirm_new_password')

        if new_password != confirm_new_password:
            raise serializers.ValidationError("The new passwords do not match.")
        
        # Check for password strength (optional)
        if len(new_password) < 8:
            raise serializers.ValidationError("The new password must be at least 8 characters long.")
        
        return data

    def save(self):
        # Save the new password
        new_password = self.validated_data['new_password']
        self.user.set_password(new_password)
        self.user.save()
        
        
class ProductUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "title",
            "description",
            "price",
            "category",
            "image",
            "files_included",
            "downloadable_file",
            "softwares",
            "size",
        ]
        extra_kwargs = {
            "description": {"style": {"base_template": "textarea.html"}},
            "files_included": {"help_text": "e.g., .zip, .pdf"},
            "softwares": {"help_text": "e.g., Photoshop, Illustrator"},
            "image": {"required": False},
            "downloadable_file": {"required": False},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image"].label = "Preview Image"
        
        
        
class BecomeSellerSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    bio = serializers.CharField()
    portfolio = serializers.URLField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20)
    skills = serializers.CharField()
    country = serializers.CharField(max_length=100)
    samples = serializers.ListField(
        child=serializers.FileField(), required=False
    )

    def validate_samples(self, value):
        if len(value) > 5:
            raise serializers.ValidationError("You can upload a maximum of 5 samples.")
        return value
    
    
class CheckoutSerializer(serializers.Serializer):
    items = CartItemSerializer(many=True)
    maintenance_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    
    
    

class GigCreateSerializer(serializers.ModelSerializer):
    category_level_1 = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), required=False)
    category_level_2 = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), required=False)
    category_level_3 = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), required=False)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True, required=False)

    class Meta:
        model = Gig
        fields = [
            'title', 'description', 'image',
            'category_level_1', 'category_level_2', 'category_level_3',
            'tags',
            # Basic Package
            'basic_name', 'basic_description', 'basic_delivery_time', 'basic_revisions', 'basic_price',
            # Standard Package
            'standard_name', 'standard_description', 'standard_delivery_time', 'standard_revisions', 'standard_price',
            # Premium Package
            'premium_name', 'premium_description', 'premium_delivery_time', 'premium_revisions', 'premium_price',
        ]

    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        user = self.context['request'].user

        u_id = uuid.uuid4()
        slug = slugify(f"{validated_data['title']}-{user.username}-{u_id}")

        gig = Gig.objects.create(
            user=user,
            slug=slug,
            **validated_data
        )
        gig.tags.set(tags)

        # Optionally mark user as freelancer
        if not user.is_work_freelancer:
            user.is_work_freelancer = True
            user.save()

        return gig


class GigUpdateSerializer(GigCreateSerializer):  # Inherit the same fields
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.tags.set(tags)
        instance.save()
        return instance



class SubcategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class EditUserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['name', 'work_bio', 'profile_pic']
