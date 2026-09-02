from django.db import models
from profiles.models import CustomUser as User
from django.utils.text import slugify
import uuid
# Create your models here.

class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=255)
    content = models.TextField()
    image = models.ImageField(upload_to='post_images/', blank=True, null=True)
    video = models.FileField(upload_to='post_videos/', blank=True, null=True)
    slug = models.SlugField(max_length=200, unique=True, auto_created=False)
    is_group_post = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ('-created_at',)

    def has_media(self):
        return self.image or self.video
    
    def comments(self):
        return self.comments.all()
    
    def comments_with_replies(self):
        # Return comments that have at least one reply
        return self.comments.annotate(reply_count=models.Count('replies')).filter(reply_count__gt=0)

    def comments_with_no_replies(self):
        return self.comments.annotate(reply_count=models.Count('replies')).filter(reply_count=0)
    
    def comment_count(self):
        return self.comments.count() + sum([comment.replies.count() for comment in self.comments.all()])
    
    def likes(self):
        return Like.objects.filter(post=self)
    
    def like(self, user):
        return self.likes.filter(user=user).exists()
    
    def save(self, *args, **kwargs):
        # Only create a new slug if it doesn't already exist
        if not self.slug:
            base_slug = slugify(self.title)
            unique_id = str(uuid.uuid4().int)[:6] 
            self.slug = f"{base_slug}-by-{self.author.username}{unique_id}"
        super(Post, self).save(*args, **kwargs)
    

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment by {self.author} on {self.post}"
    
    def replies(self):
        return self.replies.all()


class ReplyComment(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='replies')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reply by {self.author} on {self.comment}"



class Like(models.Model):
    post = models.ForeignKey(Post, to_field='slug', on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')

    def __str__(self):
        return f"{self.user} liked {self.post}"
    

class Groupcategory(models.Model):
    name = models.CharField(max_length=255)
    desc = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='group_categories')
    is_featured = models.BooleanField(default=False)
    img = models.ImageField(upload_to='work_prenair_category_images/', blank=True, null=True)

    def __str__(self):
        if self.parent:
            return f"{self.parent.name or 'Unnamed'} > {self.name or 'Unnamed'}"
        return self.name or 'Unnamed'
    

    def group_count(self):
        return self.group_category_l1.count() + self.group_category_l2.count() + self.group_category_l3.count()



class Group(models.Model):
    name = models.CharField(max_length=255)
    desc = models.TextField()
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_admin', null=True, blank=True)
    slug = models.SlugField(max_length=200, unique=True, primary_key=True, auto_created=False)
    group_posts = models.ManyToManyField(Post, related_name='group_posts', null=True, blank=True)
    members = models.ManyToManyField(User, related_name='group_members', null=True, blank=True)
    is_private = models.BooleanField(default=False)
    profile_img = models.ImageField(upload_to='commu_group_images/', blank=True, null=True)
    bg_img = models.ImageField(upload_to='commu_group_bg_images/', blank=True, null=True)
    is_featured = models.BooleanField(default=False)

    category_l_1 = models.ForeignKey(Groupcategory, on_delete=models.CASCADE, related_name='group_category_l1', null=True, blank=True)
    category_l_2 = models.ForeignKey(Groupcategory, on_delete=models.CASCADE, related_name='group_category_l2', null=True, blank=True)
    category_l_3 = models.ForeignKey(Groupcategory, on_delete=models.CASCADE, related_name='group_category_l3', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            unique_id = str(uuid.uuid4().int)[:6] 
            self.slug = f"{base_slug}{unique_id}"
        super(Group, self).save(*args, **kwargs)

    def is_public(self):
        return not self.is_private
    
    def is_admin(self, user):
        return self.admin == user
    
    def is_member(self, user):
        return self.members.filter(slug=user.slug).exists()
    
    def is_pending(self, user):
        return self.group_membership_requests.filter(user=user).exists()
    
    def posts(self):
        return self.group_posts.all()
    
    def friends_who_joined(self, user):
        friends = user.user_connections() 
        friends_in_group = self.members.filter(slug__in=friends.values_list('slug', flat=True))
        return friends_in_group
    
    def __str__(self):
        return self.name



class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    attendees = models.ManyToManyField(User, related_name='events_attending', blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_virtual = models.BooleanField(default=True)
    virtual_link = models.URLField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    category = models.ForeignKey(Groupcategory, on_delete=models.SET_NULL, null=True)
    event_image = models.ImageField(upload_to='events/')
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, max_length=255)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title) + "-" + str(uuid.uuid4())[:6]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class GroupMemberShipRequests(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='group_membership_requests')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_membership_requests')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'user')

    def __str__(self):
        return f"{self.user} requested to join {self.group}"
    

class Connection(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connections_sent')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connections_received')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user} connected with {self.to_user}"
    



class FriendRequest(models.Model):
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friend_requests_sent')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friend_requests_received')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user} sent friend request to {self.to_user}"
    


class PrivateChat(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chats1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chats2')
    slug = models.SlugField(max_length=200, unique=True, primary_key=True, auto_created=False)
    commu_prenair_chat = models.BooleanField(default=True)  # If False, it's a workprenair chat
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Chat between {self.user1} and {self.user2}"



class Message(models.Model):
    chat = models.ForeignKey(PrivateChat, on_delete=models.CASCADE, related_name='chat_messages', null=True, blank=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField(blank=True)
    file = models.FileField(upload_to='commu_prenair_chat_files/', null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender} to {self.receiver} - {self.timestamp}"
    
    @property
    def is_image(self):
        if self.file:
            return self.file.name.endswith(('.png', '.jpg', '.jpeg', '.gif'))
        return False
    
    def file_name(self):
        return self.file.name.split('/')[-1]