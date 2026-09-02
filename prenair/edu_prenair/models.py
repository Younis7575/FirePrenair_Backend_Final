from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.text import slugify
from django.utils.timezone import now
from profiles.models import CustomUser as User
from django.utils import timezone
import os
from moviepy.editor import VideoFileClip
from django.conf import settings
import uuid

# Create your models here.
class CourseCategory(models.Model):
    name = models.CharField(max_length=100, unique=False, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='courses_subcategories')
    is_featured = models.BooleanField(default=False)
    img = models.ImageField(upload_to='edu_prenair_category_images/', blank=True, null=True)

    def __str__(self):
        if self.parent:
            return f"{self.parent.name or 'Unnamed'} > {self.name or 'Unnamed'}"
        return self.name or 'Unnamed'
    
    def course_count(self):
        return self.courses_l_1.count() + self.courses_l_2.count() + self.courses_l_3.count()


class Course(models.Model):

    LEVEL_CHOICES = (
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
    )

    title = models.CharField(max_length=200)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE)

    category_l_1 = models.ForeignKey(CourseCategory, on_delete=models.SET_NULL, null=True, related_name='courses_l_1')
    category_l_2 = models.ForeignKey(CourseCategory, on_delete=models.SET_NULL, null=True, related_name='courses_l_2')
    category_l_3 = models.ForeignKey(CourseCategory, on_delete=models.SET_NULL, null=True, related_name='courses_l_3')

    slug = models.SlugField(max_length=200, unique=True, primary_key=True, auto_created=False)
    description = models.TextField(blank=False)
    requirements = models.CharField(max_length=200)
    language = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.00)])
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.00)], blank=True, null=True)
    monthly_subscription = models.BooleanField(default=False)
    is_free = models.BooleanField(default=False)
    level = models.CharField(max_length=200, choices=LEVEL_CHOICES)
    enrolled_students = models.ManyToManyField(User, related_name='enrolled_courses', blank=True)
    thumbnail = models.ImageField(upload_to='Course_thumbnails/')
    duration = models.PositiveIntegerField(help_text="Duration in hours")
    is_published = models.BooleanField(default=False)
    submit_for_approval = models.BooleanField(default=False)
    best_selling = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    def total_lessons(self):
        return Lesson.objects.filter(module__course=self).count()
    
    def total_students(self):
        return self.enrolled_students.count() - 1
    
    def related_courses(self):
        categories = [
            self.category_l_1,
            self.category_l_2,
            self.category_l_3
        ]
        return Course.objects.filter(
            models.Q(category_l_1__in=categories) |
            models.Q(category_l_2__in=categories) |
            models.Q(category_l_3__in=categories)
        ).exclude(slug=self.slug).distinct()[:8]

    
    def course_price(self):
        return self.discount_price if self.discount_price else self.price
    
    def is_course_on_discount(self):
        return True if self.discount_price else False
    
    def total_modules(self):
        return Module.objects.filter(course=self)
    
    def average_rating(self):
        ratings = self.courserating_set.all()
        if ratings:
            return int(sum(rating.rating for rating in ratings) / ratings.count())
        return 0
    
    def all_ratings(self):
        return self.courserating_set.all()
    
    def five_star_ratings(self):
        ratings = self.courserating_set.filter(rating=5)
        return ratings if ratings else 0
    
    def check_wishlist(self, user):
        return True if CourseWishlist.objects.filter(user=user, course=self).exists() else False
    
    def sales_amount(self):
        return int(self.enrolled_students.count() * self.price) - (self.price)
    
    def is_user_enrolled(self, user):
        return True if self.enrolled_students.filter(pk=user.pk).exists() else False
    
    def get_first_video(self):
        modules = self.modules.all().order_by('order')
        for module in modules:
            lessons = module.lessons.filter(video__isnull=False).order_by('order')
            print(lessons)
            for lesson in lessons:
                if not lesson.is_pdf() and lesson.video:
                    return lesson
        return None


    def save(self, *args, **kwargs):
        # Only create a new slug if it doesn't already exist
        if not self.slug:
            base_slug = slugify(self.title)
            unique_id = str(uuid.uuid4().int)[:6] 
            self.slug = f"{base_slug}-by-{self.instructor.username}{unique_id}"
        super(Course, self).save(*args, **kwargs)


class Module(models.Model):
    """A Module represents a section within a course, like Module 1, Module 2."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(help_text="The order in which this module appears in the course")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.title} (Course: {self.course.title})"
    
    def all_lessons(self):
        return Lesson.objects.filter(module=self).order_by('order')
    



class Lesson(models.Model):
    """A Lesson represents a video or content piece within a specific Module."""
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    video = models.FileField(upload_to='course_videos/')
    order = models.PositiveIntegerField(help_text="The order in which this lesson appears in the module")
    slug = models.SlugField(unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def is_pdf(self):
        return True if self.video.name.endswith('.pdf') else False


    def get_video_duration_display(self):
        if not self.video:
            return "No video"

        video_path = os.path.join(settings.MEDIA_ROOT, self.video.name)

        try:
            with VideoFileClip(video_path) as video:
                duration = video.duration  # seconds
                minutes, seconds = divmod(duration, 60)
                hours, minutes = divmod(minutes, 60)
                if hours > 0:
                    return f"{int(hours)}:{int(minutes):02}:{int(seconds):02}"
                else:
                    return f"{int(minutes)}:{int(seconds):02}"
        except Exception as e:
            return "Duration not available"

    def __str__(self):
        return f"{self.title} (Module: {self.module.title})"
    


class StudentEnrollment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey("Course", on_delete=models.CASCADE, related_name="enrollments")
    enrolled_date = models.DateTimeField(default=timezone.now)
    is_completed = models.BooleanField(default=False)
    completion_date = models.DateTimeField(null=True, blank=True)
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)  # percentage (0.0 to 100.0)
    certificate_url = models.URLField(max_length=500, null=True, blank=True)
    subscription_id = models.CharField(max_length=100, blank=True, null=True)
    completed_lessons = models.ManyToManyField("Lesson", blank=True, related_name="completed_by_students")

    def __str__(self):
        return f"{self.user} enrolled in {self.course}"

    def calculate_progress(self):
        
        total_lessons = self.course.modules.aggregate(total_lessons=models.Count('lessons'))['total_lessons']
        if total_lessons > 0:
           
            completed_lessons_count = self.completed_lessons.count()
           
            self.progress = (completed_lessons_count / total_lessons) * 100
        else:
            self.progress = 0

        
        if self.progress == 100:
            self.is_completed = True
            self.completion_date = timezone.now()
        else:
            self.is_completed = False
            self.completion_date = None

        self.save()

    def add_completed_lesson(self, lesson):
        if lesson not in self.completed_lessons.all():
            self.completed_lessons.add(lesson)
            self.calculate_progress()

    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-enrolled_date']

class CourseRating(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])  # Ratings 1-5
    review = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('course', 'user')  

    def __str__(self):
        return f"{self.rating} stars by {self.user.username} for {self.course}"
    


class CourseWishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user} added {self.course} to wishlist"
    


class CourseAnnouncement(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} for {self.course}"
    

class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.title} (Course: {self.course.title})"

class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    explanation = models.TextField(blank=True, null=True)
    correct_answer = models.CharField(max_length=500)
    answer_options = models.JSONField()  # Stores list of answer choices
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"Question {self.order}: {self.question_text[:50]}..."

class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    questions = models.ManyToManyField(QuizQuestion, through='QuizQuestionResponse')
    
    def __str__(self):
        return f"{self.user.username}'s attempt on {self.quiz.title}"

class QuizQuestionResponse(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE)
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    selected_answer = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('attempt', 'question')
    
    def __str__(self):
        return f"Response to {self.question.question_text[:50]}..."