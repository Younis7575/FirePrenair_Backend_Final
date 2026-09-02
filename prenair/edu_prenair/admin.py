from django.contrib import admin
from .models import *


admin.site.register(CourseCategory)
admin.site.register(Course)
admin.site.register(Module)
admin.site.register(Lesson)
admin.site.register(StudentEnrollment)
admin.site.register(CourseRating)
admin.site.register(CourseWishlist)
admin.site.register(CourseAnnouncement)
admin.site.register(Quiz)
admin.site.register(QuizQuestion)
admin.site.register(QuizAttempt)
admin.site.register(QuizQuestionResponse)