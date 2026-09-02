# Fireprenair — Run Doc

## How to Reproduce Artifacts

1. Convert `requirements.txt` from UTF-16 to UTF-8:
   ```bash
   cd prenair && iconv -f UTF-16 -t UTF-8 requirements.txt | sed 's/\r$//' > requirements_fixed.txt && mv requirements_fixed.txt requirements.txt
   ```

2. Copy `.env` from main checkout (or create `prenair/.env` with at minimum):
   ```
   DJANGO_SECRET_KEY=<any long random string>
   DJANGO_SETTINGS_MODULE=prenair.settings
   OPENAI_API_KEY=sk-dummy-key-for-dev-only
   GROQ_API=gsk_dummy_key_for-dev-only
   ```

3. Create venv with Python 3.12 (3.9 is too old for Django 5.1):
   ```bash
   cd prenair
   python3.12 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install docraptor elevenlabs
   ```

4. Generate and apply migrations:
   ```bash
   python manage.py makemigrations home profiles digi_prenair edu_prenair commu_prenair work_prenair dashboard core_api
   python manage.py migrate
   ```

5. Create superuser + SocialApp:
   ```bash
   DJANGO_SUPERUSER_PASSWORD=admin123 python manage.py createsuperuser --username admin --email admin@example.com --noinput
   python manage.py shell -c "
   from allauth.socialaccount.models import SocialApp
   from django.contrib.sites.models import Site
   site = Site.objects.get(pk=1)
   app, _ = SocialApp.objects.get_or_create(provider='google', defaults={'name':'Google','client_id':'dummy','secret':'dummy'})
   app.sites.add(site)
   "
   ```

## How to Run

```bash
cd prenair && source venv/bin/activate && python manage.py runserver 0.0.0.0:8000
```

Server: **http://127.0.0.1:8000** | Admin: **http://127.0.0.1:8000/admin/** (admin / admin123)

---

## Complete REST API Endpoint Reference

All endpoints under `/api/` prefix. JWT Bearer token required unless marked `[Public]`.

### Authentication & Profile
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/my_accounts/login/` | Public | Login (returns JWT + role flags) |
| POST | `/api/my_accounts/register/` | Public | Register (sends OTP email) |
| POST | `/api/my_accounts/verify-email/` | Public | Verify email OTP |
| POST | `/api/my_accounts/logout/` | Yes | Logout |
| POST | `/api/token/refresh/` | Public | Refresh JWT token |
| GET | `/api/my_accounts/change-language/` | Yes | Change language |
| GET/POST | `/api/my_accounts/checkout/<plan_id>/` | Yes | Stripe checkout |
| POST | `/api/my_accounts/webhook/` | Public | Stripe webhook |

### Home
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/home/home/` | Public | Homepage data |
| GET | `/api/home/leaderboard/` | Public | Leaderboard |
| POST | `/api/home/home_chatbot/` | Public | AI chatbot |
| POST | `/api/home/delete_thread/` | Yes | Delete chat thread |
| GET | `/api/home/work-parent-categories/` | Public | Work categories |
| GET | `/api/home/edu-parent-categories/` | Public | Edu categories |
| GET | `/api/home/digi-parent-categories/` | Public | Digi categories |
| GET | `/api/home/commu-parent-categories/` | Public | Commu categories |
| POST | `/api/home/blogs/` | Public | Blog list |
| GET | `/api/home/blogs/<slug>/` | Public | Blog detail |
| POST | `/api/home/corporate/check-email/` | Public | Check email |
| POST | `/api/home/corporate/login/` | Public | Corporate login |
| POST | `/api/home/corporate/verify-otp/` | Public | Corporate OTP |
| POST | `/api/home/corporate/submit-project/` | Yes | Submit project |
| GET | `/api/home/corporate-dashboard/` | Yes | Corporate dashboard |

### Dashboard
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/dashboard/home/` | Yes | Dashboard home |
| GET | `/api/dashboard/notifications/` | Yes | Notifications |
| DELETE | `/api/dashboard/notifications/delete/<id>/` | Yes | Delete notification |
| GET | `/api/dashboard/my_referrals/` | Yes | Referrals |
| GET | `/api/dashboard/my_access_token/` | Yes | Access token |
| POST | `/api/dashboard/access-token/verify/` | Yes | Verify token |
| POST | `/api/dashboard/edit_profile/` | Yes | Edit profile |
| POST | `/api/dashboard/change_password/` | Yes | Change password |
| GET/POST | `/api/dashboard/billing/` | Yes | Billing |
| POST | `/api/dashboard/request-payout/` | Yes | Request payout |
| GET/POST | `/api/dashboard/payout-settings/` | Yes | Payout settings |
| GET | `/api/dashboard/payment-history/` | Yes | Payment history |
| POST | `/api/dashboard/paypal-transfer/` | Yes | PayPal transfer |

### Dashboard - Admin
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/dashboard/admin/` | Admin | Admin dashboard |
| GET | `/api/dashboard/admin/online-users/` | Admin | Online users |
| GET | `/api/dashboard/admin/statistics/` | Admin | Statistics |
| GET | `/api/dashboard/admin/sales/digiprenair/` | Admin | Digi sales |
| GET | `/api/dashboard/admin/sales/workprenair/` | Admin | Work sales |
| GET | `/api/dashboard/admin/withdrawal_requests/` | Admin | Withdrawals |
| GET | `/api/dashboard/admin/withdrawal_requests/<id>/` | Admin | Withdrawal detail |
| GET | `/api/dashboard/admin/traffic-logs/` | Admin | Traffic logs |
| GET | `/api/dashboard/admin/traffic-insights-json/` | Admin | Traffic insights |

### Dashboard - Website Builder
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/dashboard/my_websites/` | Yes | List websites |
| POST | `/api/dashboard/create_website/` | Yes | Create website |
| GET | `/api/dashboard/get_template_categories/` | Yes | Template categories |
| GET | `/api/dashboard/select_template/` | Yes | Select template |
| GET | `/api/dashboard/get_user_website/<id>/` | Yes | Get website HTML |
| POST | `/api/dashboard/save_website/` | Yes | Save website |
| POST | `/api/dashboard/website/<id>/publish/` | Yes | Publish/unpublish |
| DELETE | `/api/dashboard/delete_website/<id>/` | Yes | Delete website |

### Dashboard - Funnel System
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/dashboard/funnels/` | Yes | List funnels |
| POST | `/api/dashboard/funnels/create/` | Yes | Create funnel |
| PUT | `/api/dashboard/funnels/<id>/edit/` | Yes | Edit funnel |
| DELETE | `/api/dashboard/funnels/delete/<id>/` | Yes | Delete funnel |
| POST | `/api/dashboard/funnels/<id>/publish/` | Yes | Publish funnel |
| GET | `/api/dashboard/funnels/emails-by-tag/` | Yes | Leads by tag |

### Dashboard - AI Generation
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/dashboard/image_generation/` | Yes | Leonardo AI image |
| POST | `/api/dashboard/logo_generation/` | Yes | Logo generation |
| POST | `/api/dashboard/video_generation/` | Yes | Video generation |
| POST | `/api/dashboard/ebook_generation/` | Yes | Ebook generation |
| POST | `/api/dashboard/generate_pdf/` | Yes | PDF generation |

### Dashboard - AI Descriptions
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/dashboard/generate-description-eduprenair/` | Yes | Edu description |
| POST | `/api/dashboard/generate-description-digiprenair/` | Yes | Digi description |
| POST | `/api/dashboard/generate-description-workprenair/` | Yes | Work description |

### Dashboard - DigiPrenair
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/dashboard/digiprenair/` | Yes | Digi dashboard |
| POST | `/api/dashboard/digiprenair/upload_item/` | Yes | Upload item |
| POST | `/api/dashboard/digiprenair/manage_item/` | Yes | Manage item |
| PUT | `/api/dashboard/digiprenair/edit_item_digiprenair/<slug>/` | Yes | Edit item |
| GET | `/api/dashboard/get-child-categories-digi/` | Yes | Child categories |
| GET | `/api/dashboard/digi-reviews/` | Yes | Digi reviews |

### Dashboard - EduPrenair
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/dashboard/eduprenair/` | Yes | Edu dashboard |
| GET | `/api/dashboard/eduprenair/manage_courses/` | Yes | Manage courses |
| POST | `/api/dashboard/eduprenair/course_create/` | Yes | Create course |
| POST | `/api/dashboard/eduprenair/course_submit/<slug>/` | Yes | Submit for approval |
| PUT | `/api/dashboard/eduprenair/course_edit/<slug>/` | Yes | Edit course |
| DELETE | `/api/dashboard/course/delete/<slug>/` | Yes | Delete course |
| POST | `/api/dashboard/eduprenair/course/<slug>/add-module/` | Yes | Add module |
| POST | `/api/dashboard/eduprenair/course/module/<id>/add-lesson/` | Yes | Add lesson |
| DELETE | `/api/dashboard/delete-lesson/<id>/` | Yes | Delete lesson |
| POST | `/api/dashboard/edit-lesson/<id>/` | Yes | Edit lesson |
| POST | `/api/dashboard/generate-module-lessons/<slug>/` | Yes | AI lesson generation |
| GET | `/api/dashboard/course/<slug>/stats/` | Yes | Course stats |
| POST | `/api/dashboard/analyze_student_progress/` | Yes | Analyze progress |

### Digiprenair (Marketplace)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/digiprenair/home/` | Public | Digi home |
| GET | `/api/digiprenair/explore/` | Public | Explore products |
| GET | `/api/digiprenair/product-search/` | Public | Search products |
| GET | `/api/digiprenair/sellers/` | Public | Sellers list |
| GET/POST | `/api/digiprenair/product/<slug>/` | Public/Yes | Product detail + review |
| GET | `/api/digiprenair/profile/<slug>/` | Public | Seller profile |
| GET | `/api/digiprenair/shoping_cart/` | Yes | Shopping cart |
| POST | `/api/digiprenair/add_to_cart/<slug>/` | Yes | Add to cart |
| DELETE | `/api/digiprenair/remove_from_cart/<slug>/` | Yes | Remove from cart |
| GET | `/api/digiprenair/notifications/` | Yes | Notifications |
| POST | `/api/digiprenair/notifications/read/<id>/` | Yes | Mark read |
| DELETE | `/api/digiprenair/notifications/delete/<id>/` | Yes | Delete notification |
| PATCH | `/api/digiprenair/notifications/mark-all-read/` | Yes | Mark all read |
| GET/PATCH | `/api/digiprenair/profile_info/` | Yes | Profile info |
| POST | `/api/digiprenair/profile_settings/` | Yes | Password change |
| GET | `/api/digiprenair/dashboard/` | Yes | Seller dashboard |
| POST | `/api/digiprenair/upload_item/` | Yes | Upload product |
| GET | `/api/digiprenair/manage_items/` | Yes | Manage items |
| PUT | `/api/digiprenair/edit-product/<slug>/` | Yes | Edit product |
| GET | `/api/digiprenair/purchases/` | Yes | Purchases |
| POST | `/api/digiprenair/become_seller/` | Yes | Become seller |
| GET | `/api/digiprenair/get-child-categories/<id>/` | Public | Subcategories |
| POST | `/api/digiprenair/digiprenair_chatbot/` | Public | Chatbot |
| POST | `/api/digiprenair/checkout/` | Yes | Stripe checkout |
| POST | `/api/digiprenair/webhook/` | Public | Stripe webhook |
| POST | `/api/digiprenair/paypal/checkout/` | Yes | PayPal checkout |
| POST | `/api/digiprenair/paypal/success/` | Public | PayPal success |
| POST | `/api/digiprenair/add-to-project/` | Yes | Add to project |
| GET | `/api/digiprenair/projects/` | Yes | List projects |
| GET | `/api/digiprenair/projects/<id>/` | Yes | Project detail |
| GET | `/api/digiprenair/download-product/<id>/` | Yes | Download product |
| POST | `/api/products/generate-upload-url/` | Yes | S3 presigned URL |

### EduPrenair (Courses)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/eduprenair/home/` | Public | Edu home |
| GET | `/api/eduprenair/profile/<slug>/` | Yes | Instructor profile |
| GET/POST | `/api/eduprenair/settings/` | Yes | Settings |
| GET | `/api/eduprenair/instructor/dashboard/` | Yes | Instructor dashboard |
| GET | `/api/eduprenair/instructors/` | Public | Instructors list |
| POST | `/api/eduprenair/instructor/add-course/` | Yes | Add course |
| GET | `/api/eduprenair/instructor/courses/` | Yes | My courses |
| POST | `/api/eduprenair/instructor/course/<slug>/submit/` | Yes | Submit for approval |
| GET/POST | `/api/eduprenair/instructor/course/<slug>/add-module/` | Yes | Add module |
| POST | `/api/eduprenair/instructor/course/module/<id>/add-lesson/` | Yes | Add lesson |
| DELETE | `/api/eduprenair/instructor/course/<slug>/delete/` | Yes | Delete course |
| POST | `/api/eduprenair/lesson-complete/<slug>/<slug>/` | Yes | Mark lesson done |
| GET | `/api/eduprenair/student/dashboard/` | Yes | Student dashboard |
| GET | `/api/eduprenair/student/courses/` | Yes | Student courses |
| GET | `/api/eduprenair/reviews/` | Yes | Reviews |
| GET | `/api/eduprenair/courses/` | Public | All courses |
| POST | `/api/eduprenair/course/analyze-review/` | Yes | AI review analysis |
| GET | `/api/eduprenair/course/<slug>/` | Public | Course detail |
| GET | `/api/eduprenair/course/<slug>/content/` | Yes | Course content |
| GET | `/api/eduprenair/course/view_lesson/<slug>/` | Yes | View lesson |
| POST | `/api/eduprenair/generate-quiz/<slug>/` | Yes | AI quiz generation |
| GET/POST | `/api/eduprenair/take-quiz/<id>/` | Yes | Take quiz |
| GET | `/api/eduprenair/quiz-results/<id>/` | Yes | Quiz results |
| GET | `/api/eduprenair/course/<slug>/get_certificate/` | Yes | Get certificate |
| POST | `/api/eduprenair/course/<slug>/post-review/` | Yes | Post review |
| POST | `/api/eduprenair/course/<slug>/add-to-wishlist/` | Yes | Add wishlist |
| DELETE | `/api/eduprenair/course/<slug>/remove-from-wishlist/` | Yes | Remove wishlist |
| GET | `/api/eduprenair/wishlist/` | Yes | Wishlist |
| GET | `/api/eduprenair/order-history/` | Yes | Order history |
| GET | `/api/eduprenair/announcements/` | Yes | Announcements |
| POST | `/api/eduprenair/announcements/add/` | Yes | Add announcement |
| DELETE | `/api/eduprenair/announcements/<id>/delete/` | Yes | Delete announcement |
| GET | `/api/eduprenair/earnings/` | Yes | Earnings |
| POST | `/api/eduprenair/course/<slug>/checkout/` | Yes | Course checkout |
| POST | `/api/eduprenair/course-webhook/stripe/` | Public | Course Stripe webhook |
| GET | `/api/eduprenair/get-child-categories/<id>/` | Public | Subcategories |
| POST | `/api/eduprenair/paypal-checkout/<slug>/` | Yes | PayPal checkout |
| POST | `/api/eduprenair/paypal-success/<slug>/` | Public | PayPal success |
| POST | `/api/eduprenair/eduprenair_chatbot/` | Public | Chatbot |
| POST | `/api/eduprenair/become-instructor/` | Yes | Become instructor |
| POST | `/api/eduprenair/course/lesson/generate_audio/` | Yes | TTS audio |

### WorkPrenair (Freelancing)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/workprenair/home/` | Public | Work home |
| GET | `/api/workprenair/buyer-dashboard/` | Yes | Buyer dashboard |
| GET | `/api/workprenair/seller-dashboard/` | Yes | Seller dashboard |
| GET | `/api/workprenair/my_orders/` | Yes | My orders |
| GET | `/api/workprenair/profile/<username>/` | Yes | User profile |
| POST | `/api/workprenair/profile/edit/` | Yes | Edit profile |
| GET | `/api/workprenair/messages/` | Yes | Chat list |
| GET | `/api/workprenair/message/<slug>/` | Yes | Chat messages |
| GET | `/api/workprenair/message/ai-suggestions/<slug>/` | Yes | AI chat suggestions |
| GET | `/api/workprenair/api/categories/<id>/` | Public | Categories |
| GET | `/api/workprenair/api/search_tags/` | Public | Search tags |
| GET | `/api/workprenair/api/gig-tags/<slug>/` | Yes | Gig tags |
| POST | `/api/workprenair/api/create_tag/` | Yes | Create tag |
| GET | `/api/workprenair/todos/` | Yes | Todo list |
| POST | `/api/workprenair/todos/create/` | Yes | Create todo |
| PUT | `/api/workprenair/todos/update/<id>/` | Yes | Update todo |
| DELETE | `/api/workprenair/todos/delete/<id>/` | Yes | Delete todo |
| GET | `/api/workprenair/services/` | Public | All gigs |
| GET | `/api/workprenair/gigs/` | Yes | My gigs |
| POST | `/api/workprenair/gig/create/` | Yes | Create gig |
| GET | `/api/workprenair/gig/<slug>` | Public | Gig detail |
| PUT | `/api/workprenair/gig/<slug>/edit/` | Yes | Edit gig |
| DELETE | `/api/workprenair/gig/<slug>/delete/` | Yes | Delete gig |
| POST | `/api/workprenair/gig/optimize/<slug>/` | Yes | AI optimize gig |
| POST | `/api/workprenair/gig/apply-suggestion/` | Yes | Apply AI suggestion |
| POST | `/api/workprenair/gigs/<slug>/suggest_pricing/` | Yes | AI pricing |
| GET | `/api/workprenair/order/<slug>/` | Yes | Order detail |
| POST | `/api/workprenair/order/submit_requirements/<id>/` | Yes | Submit requirements |
| POST | `/api/workprenair/order/<slug>/delivery/` | Yes | Deliver order |
| POST | `/api/workprenair/order/<slug>/revision/` | Yes | Request revision |
| POST | `/api/workprenair/order/<slug>/complete/` | Yes | Complete order |
| POST | `/api/workprenair/order/<slug>/review/` | Yes | Review order |
| GET | `/api/workprenair/offers/` | Yes | Custom offers |
| POST | `/api/workprenair/offer/create/` | Yes | Create offer |
| POST | `/api/workprenair/offer/generate_proposal/` | Yes | AI proposal |
| POST | `/api/workprenair/offer/decline/<id>/` | Yes | Decline offer |
| DELETE | `/api/workprenair/offer/delete/<id>/` | Yes | Delete offer |
| POST | `/api/workprenair/gig/<slug>/checkout/<pkg>/` | Yes | Gig checkout |
| POST | `/api/workprenair/custom-offer/checkout/<id>/` | Yes | Offer checkout |
| POST | `/api/workprenair/webhook/` | Public | Stripe webhook |
| POST | `/api/workprenair/paypal/checkout/<slug>/<pkg>/` | Yes | PayPal checkout |
| POST | `/api/workprenair/paypal/success/` | Public | PayPal success |
| POST | `/api/workprenair/paypal/cancel/` | Public | PayPal cancel |
| POST | `/api/workprenair/custom-offer/paypal-checkout/<id>/` | Yes | Offer PayPal |
| POST | `/api/workprenair/custom-offer/paypal-success/` | Public | Offer PayPal success |
| GET | `/api/workprenair/categories/top/` | Public | Top categories |
| GET | `/api/workprenair/categories/hierarchy/<id>/` | Public | Category hierarchy |
| POST | `/api/workprenair/workprenair_chatbot/` | Public | Chatbot |
| POST | `/api/workprenair/become-seller/` | Yes | Become seller |
| POST | `/api/workprenair/switch-profile/` | Yes | Toggle profile |
| GET | `/api/workprenair/workprenair_notifications/` | Yes | Notifications |

### CommuPrenair (Social/Community)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/commuprenair/home/` | Yes | Home feed |
| POST | `/api/commuprenair/make-post/` | Yes | Create post |
| GET | `/api/commuprenair/post/<slug>/` | Yes | Post detail |
| DELETE | `/api/commuprenair/delete_post/<slug>/` | Yes | Delete post |
| POST | `/api/commuprenair/post/<slug>/add_comment/` | Yes | Add comment |
| POST | `/api/commuprenair/add-reply/<id>/` | Yes | Add reply |
| POST | `/api/commuprenair/like/<slug>/` | Yes | Toggle like |
| GET | `/api/commuprenair/likes/<slug>/` | Yes | Get likes |
| GET | `/api/commuprenair/search/` | Yes | Search people |
| GET | `/api/commuprenair/profile/<slug>/` | Yes | Profile |
| POST | `/api/commuprenair/profile-settings/` | Yes | Profile settings |
| GET | `/api/commuprenair/about/<slug>/` | Yes | About |
| GET | `/api/commuprenair/get-child-categories/` | Public | Categories |
| GET | `/api/commuprenair/groups/` | Yes | Groups list |
| POST | `/api/commuprenair/groups/create/` | Yes | Create group |
| GET | `/api/commuprenair/group/<slug>/` | Yes | Group detail |
| POST | `/api/commuprenair/group/<slug>/manage/` | Yes | Manage group |
| POST | `/api/commuprenair/group/<slug>/join/` | Yes | Join group |
| POST | `/api/commuprenair/group/<slug>/leave/` | Yes | Leave group |
| POST | `/api/commuprenair/group/<slug>/post/` | Yes | Group post |
| GET | `/api/commuprenair/events/` | Yes | Events list |
| POST | `/api/commuprenair/events/create/` | Yes | Create event |
| POST | `/api/commuprenair/events/create/ai/` | Yes | AI event |
| GET | `/api/commuprenair/events/<slug>/` | Yes | Event detail |
| POST | `/api/commuprenair/events/join/<slug>/` | Yes | Join event |
| POST | `/api/commuprenair/events/leave/<slug>/` | Yes | Leave event |
| PUT | `/api/commuprenair/events/edit/<slug>/` | Yes | Edit event |
| GET | `/api/commuprenair/connection-requests/` | Yes | Connection requests |
| GET | `/api/commuprenair/connections/<slug>/` | Yes | Connections |
| POST | `/api/commuprenair/send-connection-request/<slug>/` | Yes | Send request |
| DELETE | `/api/commuprenair/withdraw-connection-request/<slug>/` | Yes | Withdraw request |
| POST | `/api/commuprenair/friend-request/<slug>/<action>/` | Yes | Accept/reject |
| DELETE | `/api/commuprenair/remove-connection/<slug>/` | Yes | Remove connection |
| GET | `/api/commuprenair/chat/` | Yes | Chat list |
| GET | `/api/commuprenair/chat/<slug>/` | Yes | Chat messages |
| POST | `/api/commuprenair/commuprenair_chatbot/` | Yes | Chatbot |
| POST | `/api/commuprenair/notifications/read/all/` | Yes | Mark all read |

### WebSocket Endpoints
| Protocol | URL | Description |
|----------|-----|-------------|
| WS | `ws/chat/<slug>/` | Real-time chat |
| WS | `ws/notifications/` | Real-time notifications |
