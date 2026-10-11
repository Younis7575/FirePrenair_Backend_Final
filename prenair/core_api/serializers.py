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
            # The profile header draws a green/grey presence dot from this
            # (partials/profile_topbar.html); it was never serialised, so the
            # app had no way to render it.
            "is_online", "last_seen", "last_seen_text",
        ]

    last_seen_text = serializers.SerializerMethodField()

    # Government-ID and birth-date values are the owner's (and staff's) only;
    # every other viewer — post authors, search results, profiles — used to
    # receive them. The keys stay (clients read them) but are blanked.
    _PRIVATE_FIELDS = ("identity_type", "identity_number", "date_of_birth", "age")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request") if hasattr(self, "context") else None
        viewer = getattr(request, "user", None)
        if viewer is not None and getattr(viewer, "is_authenticated", False):
            allowed = (
                viewer.pk == instance.pk
                or getattr(viewer, "is_staff", False)
                or getattr(viewer, "role", None) == "admin"
            )
        else:
            # No request (internal use) keeps the old behaviour; an anonymous
            # request is never the owner.
            allowed = request is None
        if not allowed:
            for key in self._PRIVATE_FIELDS:
                if key in data:
                    data[key] = None
        return data

    def get_last_seen_text(self, obj):
        # Same wording as the website's "Last seen:" line in private_chat.html.
        return obj.time_since_last_seen()

class CustomUserSerializer(serializers.ModelSerializer):
    """Admin-facing user listing.

    The admin screens search on email and phone and show account state, so
    unlike [UserSerializer] this exposes those fields. Referenced by the admin
    user and online-user endpoints, which previously raised NameError because
    no such serializer existed.
    """

    class Meta:
        model = CustomUser
        fields = [
            "id", "username", "name", "email", "phone_no", "slug", "role",
            "profile_pic", "country", "city", "language", "timezone",
            "customer_type", "company_name", "is_online", "is_active",
            "is_staff", "created_at", "last_login",
            "is_edu_instructor", "is_work_freelancer", "is_digi_seller",
            "is_corporate_client",
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
            # Presence dot / "Last seen" in chat lists and headers (website:
            # commu_messages.html, private_chat.html).
            "is_online","last_seen","last_seen_text",
            # Verified badge on product cards / seller rows (additive).
            "digi_is_verified",
        ]

    last_seen_text = serializers.SerializerMethodField()

    def get_last_seen_text(self, obj):
        return obj.time_since_last_seen()


# ---------------------------------------------------------------------------
# Relationship-aware people serializers.
#
# The website's people cards (search_people.html, connection_requests.html,
# profile_connections.html, profile_topbar.html) show the avatars + number of
# mutual connections and pick Message / Send Request / Withdraw / Accept /
# Remove from the viewer's relationship with that person. The plain user
# serializers carry none of it, so the app could not draw those cards. These
# add the data (viewer = request.user from the serializer context).
# ---------------------------------------------------------------------------
def _connection_ids(user):
    from commu_prenair.models import Connection
    ids = set(Connection.objects.filter(from_user=user).values_list('to_user_id', flat=True))
    ids |= set(Connection.objects.filter(to_user=user).values_list('from_user_id', flat=True))
    return ids


class RelationFieldsMixin(serializers.Serializer):
    mutual_connections_count = serializers.SerializerMethodField()
    mutual_connections = serializers.SerializerMethodField()
    is_connected = serializers.SerializerMethodField()
    request_sent = serializers.SerializerMethodField()
    request_received = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()
    connections_count = serializers.SerializerMethodField()

    def _viewer(self):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return user if user is not None and user.is_authenticated else None

    def _viewer_ids(self, viewer):
        cache = self.context.setdefault('_viewer_conn_ids', {})
        if viewer.id not in cache:
            cache[viewer.id] = _connection_ids(viewer)
        return cache[viewer.id]

    def _mutual_ids(self, obj):
        viewer = self._viewer()
        if viewer is None or viewer.id == obj.id:
            return []
        return sorted(self._viewer_ids(viewer) & _connection_ids(obj))

    def get_mutual_connections_count(self, obj):
        return len(self._mutual_ids(obj))

    def get_mutual_connections(self, obj):
        users = CustomUser.objects.filter(id__in=self._mutual_ids(obj)[:3])
        return [
            {
                'username': u.username,
                'name': u.name,
                'slug': u.slug,
                'profile_pic': u.profile_pic.url if u.profile_pic else None,
            }
            for u in users
        ]

    def get_is_connected(self, obj):
        viewer = self._viewer()
        return bool(viewer and viewer.id != obj.id and obj.id in self._viewer_ids(viewer))

    def get_request_sent(self, obj):
        from commu_prenair.models import FriendRequest
        viewer = self._viewer()
        return bool(viewer and FriendRequest.objects.filter(from_user=viewer, to_user=obj).exists())

    def get_request_received(self, obj):
        from commu_prenair.models import FriendRequest
        viewer = self._viewer()
        return bool(viewer and FriendRequest.objects.filter(from_user=obj, to_user=viewer).exists())

    def get_is_self(self, obj):
        viewer = self._viewer()
        return bool(viewer and viewer.id == obj.id)

    def get_connections_count(self, obj):
        return len(_connection_ids(obj))


_RELATION_FIELDS = [
    "mutual_connections_count", "mutual_connections", "is_connected",
    "request_sent", "request_received", "is_self", "connections_count",
]


class PersonSerializer(RelationFieldsMixin, UserSerializer):
    """Full user + relationship to the viewer (search, connections, profile)."""
    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + _RELATION_FIELDS


class PersonLiteSerializer(RelationFieldsMixin, UserDataSerializer):
    """Light user + relationship to the viewer (connection-request senders)."""
    class Meta(UserDataSerializer.Meta):
        fields = UserDataSerializer.Meta.fields + _RELATION_FIELDS

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


class ReplyCommentSerializer(serializers.ModelSerializer):
    """A reply under a comment.

    Same shape as a comment so the client can render either with one widget:
    the web templates read `reply.author.name`, `.slug`, `.profile_pic` and
    `reply.content`, which is exactly what UserDataSerializer provides.
    """

    author = UserDataSerializer(read_only=True)

    class Meta:
        model = ReplyComment
        fields = ['id', 'comment', 'author', 'content', 'created_at',
                  'updated_at']


class CommentSerializer(serializers.ModelSerializer):
    author = UserDataSerializer(read_only=True)
    # `fields = '__all__'` covers concrete columns only, so the `replies`
    # reverse relation was never serialised — replies could be posted but
    # never came back, which made them invisible in the app.
    replies = ReplyCommentSerializer(many=True, read_only=True)

    class Meta:
        model = Comment
        fields = '__all__'

class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    comments=CommentSerializer(many=True, read_only=True)
    # The feed, profile and group posts all draw "N likes", the heart state and
    # "N Comments" (website partials/post_card.html). None of it was serialised,
    # so after a reload every post looked unliked with no counts.
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = '__all__'

    def get_like_count(self, obj):
        return obj.likes.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            return False
        return obj.likes.filter(user=user).exists()

    def get_comment_count(self, obj):
        return obj.comment_count()
        
class GroupCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Groupcategory
        fields = '__all__'

class GroupSerializer(serializers.ModelSerializer):
    admin = UserDataSerializer(read_only=True)
    # `members` is a many-to-many; without many=True the serializer is handed
    # the related manager and blows up looking for `username` on it.
    members = UserDataSerializer(many=True, read_only=True)
    # group_list.html / group_detail.html: "<n> Member", three member avatars,
    # and View (member) vs Join (non-member) on each card.
    member_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()
    is_pending = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = '__all__'

    def _viewer(self):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return user if user is not None and user.is_authenticated else None

    def get_member_count(self, obj):
        return obj.members.count()

    def get_is_member(self, obj):
        viewer = self._viewer()
        return bool(viewer and obj.members.filter(id=viewer.id).exists())

    def get_is_admin(self, obj):
        viewer = self._viewer()
        return bool(viewer and obj.admin_id == viewer.id)

    def get_is_pending(self, obj):
        viewer = self._viewer()
        return bool(viewer and obj.group_membership_requests.filter(user=viewer).exists())

    def get_category_name(self, obj):
        cat = obj.category_l_1
        return cat.name if cat else None

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
    from_user = PersonLiteSerializer(read_only=True)
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
    # Additive: the website's course card / course page show these (course_card.html).
    total_lessons = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    enrolled_count = serializers.SerializerMethodField()
    sales_amount = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = '__all__'

    def get_total_lessons(self, obj):
        return obj.total_lessons()

    def get_average_rating(self, obj):
        return obj.average_rating()

    def get_rating_count(self, obj):
        return obj.courserating_set.count()

    def get_enrolled_count(self, obj):
        return obj.enrolled_students.count()

    def get_sales_amount(self, obj):
        try:
            return float(obj.sales_amount())
        except Exception:
            return 0

class ModuleSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    # module_lessons_eduprenair.html lists each module's lessons; kept flat
    # (no nested module) so it cannot recurse into LessonSerializer.
    lessons = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = '__all__'

    def get_lessons(self, obj):
        out = []
        for l in obj.lessons.all():
            try:
                video = l.video.url if l.video else None
            except Exception:
                video = None
            out.append({
                'id': l.id, 'title': l.title, 'description': l.description,
                'order': l.order, 'slug': l.slug, 'video': video,
            })
        return out
        
class LessonSerializer(serializers.ModelSerializer):
    module = ModuleSerializer(read_only=True)
    class Meta:
        model = Lesson
        fields = '__all__'

class StudentEnrollmentSerializer(serializers.ModelSerializer):
    # Additive: the dashboards render course cards / tables from the enrolment,
    # but `course` is only the slug.
    course_detail = serializers.SerializerMethodField()
    completed_lesson_slugs = serializers.SerializerMethodField()

    class Meta:
        model = StudentEnrollment
        fields = '__all__'

    def get_course_detail(self, obj):
        return CourseSerializer(obj.course, context=self.context).data

    def get_completed_lesson_slugs(self, obj):
        return list(obj.completed_lessons.values_list('slug', flat=True))

class CourseRatingSerializer(serializers.ModelSerializer):
    user=UserDataSerializer(read_only=True)
    course_title = serializers.SerializerMethodField()
    course_slug = serializers.SerializerMethodField()

    class Meta:
        model = CourseRating
        fields = '__all__'

    def get_course_title(self, obj):
        return obj.course.title

    def get_course_slug(self, obj):
        return obj.course.slug

class CourseWishlistSerializer(serializers.ModelSerializer):
    user=UserDataSerializer(read_only=True)
    course_detail = serializers.SerializerMethodField()

    class Meta:
        model = CourseWishlist
        fields = '__all__'

    def get_course_detail(self, obj):
        return CourseSerializer(obj.course, context=self.context).data
        
        
class CourseAnnouncementSerializer(serializers.ModelSerializer):
    course_title = serializers.SerializerMethodField()

    class Meta:
        model = CourseAnnouncement
        fields = '__all__'

    def get_course_title(self, obj):
        return obj.course.title
        
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
    # Additive: quiz_results.html lists every answered question with the
    # correct answer and explanation.
    responses = serializers.SerializerMethodField()

    class Meta:
        model = QuizAttempt
        fields = '__all__'

    def get_responses(self, obj):
        out = []
        for r in obj.quizquestionresponse_set.select_related('question').all():
            q = r.question
            out.append({
                'id': r.id,
                'question_id': q.id,
                'question_text': q.question_text,
                'selected_answer': r.selected_answer,
                'is_correct': r.is_correct,
                'correct_answer': q.correct_answer,
                'explanation': q.explanation,
            })
        return out

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
        # Card badge: the category's name/colour without a second lookup.
        category = instance.category
        data['category_name'] = category.name if category else None
        data['category_color'] = category.color if category else None
        return data


class DigiProductReviewSerializer(serializers.ModelSerializer):
    user=UserDataSerializer(read_only=True)
    class Meta:
        model = Review
        fields = '__all__'


class CartItemSerializer(serializers.ModelSerializer):
    # `product` stays the id (existing contract); the cart screens also need
    # the product itself to show a title / image / price and to remove it by
    # slug, which previously meant they could render nothing but an id.
    product_details = serializers.SerializerMethodField(read_only=True)
    line_total = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CartItem
        fields = '__all__'

    def get_product_details(self, obj):
        product = obj.product
        seller = product.seller
        return {
            'id': product.id,
            'title': product.title,
            'slug': product.slug,
            'description': product.description,
            'price': str(product.price),
            'discounted_price': str(product.discounted_price),
            'final_price': str(product.effective_price()),
            'image': product.image.url if product.image else None,
            'category_name': product.category.name if product.category else None,
            'seller': {
                'id': seller.id,
                'username': seller.username,
                'name': seller.name,
                'slug': seller.slug,
                'profile_pic': seller.profile_pic.url if seller.profile_pic else None,
            },
        }

    def get_line_total(self, obj):
        return float(obj.product.effective_price() * obj.quantity)


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
# This file already aliases `CustomUser as User` at the top (line ~173).
# Importing Django's auth.User here REBOUND that name, and because
# work_prenair_views.py does `from .serializers import *`, every
# get_object_or_404(User, ...) in that module silently started hitting the
# missing auth_user table -> OperationalError 500s (offers, work chat).
# Nothing below actually used Django's User, so the import is removed.
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
            "discounted_price",
            "category",
            "category_l_2",
            "category_l_3",
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
            "discounted_price": {"required": False},
            # Product.save() dereferences category (item_count), so a missing
            # one was a 500 instead of a 400.
            "category": {"required": True, "allow_null": False},
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
    
    
class CheckoutLineSerializer(serializers.Serializer):
    """A PayPal line item as built by paypal_checkout_api (not a CartItem row:
    CartItemSerializer demands cart/product ids, so every PayPal checkout
    failed validation with a 400)."""
    name = serializers.CharField()
    sku = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)


class CheckoutSerializer(serializers.Serializer):
    items = CheckoutLineSerializer(many=True)
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
        # `None` (not []) when the request carried no tags: a PATCH that only
        # changes the title used to wipe every tag off the gig.
        tags = validated_data.pop('tags', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if tags is not None:
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


from home.models import PlanFeature, PricingPlan
from digi_prenair.models import Review as DigiReviewModel


class DigiReviewSerializer(serializers.ModelSerializer):
    """Reviews on a DigiPrenair product.

    `ReviewSerializer` is declared twice in this module and both bind to
    work_prenair's Review, which has `gig`/`order` instead of `product` — so
    the digi views were validating and rendering against the wrong table.
    """

    user = UserSerializer(read_only=True)

    class Meta:
        model = DigiReviewModel
        fields = ['id', 'product', 'user', 'title', 'body', 'rating',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'product', 'user', 'created_at', 'updated_at']



class PlanFeatureSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='feature.name', read_only=True)
    key = serializers.CharField(source='feature.key', read_only=True)
    description = serializers.CharField(
        source='feature.description', read_only=True
    )

    class Meta:
        model = PlanFeature
        fields = ['id', 'name', 'key', 'description', 'value']


class PricingPlanSerializer(serializers.ModelSerializer):
    """Subscription plans for the pricing screen.

    Needed by the pricing endpoint, which raised NameError because this
    serializer was referenced but never written.
    """

    features = PlanFeatureSerializer(
        source='plan_features', many=True, read_only=True
    )

    class Meta:
        model = PricingPlan
        fields = [
            'id', 'title', 'description', 'price_monthly', 'price_annual',
            'access_to_dept', 'ai_tools_limit', 'product_limit',
            'service_limit', 'support_limit', 'features',
        ]
