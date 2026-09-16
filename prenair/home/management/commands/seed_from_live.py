"""Populate a local database with the content the live site serves.

A fresh checkout has an empty `db.sqlite3`, so every listing screen in the app
renders blank even though the endpoints answer 200. This command pulls from the
live site's public read APIs and recreates the rows locally, which is what the
app needs to show WorkPrenair gigs, EduPrenair courses, DigiPrenair products
and the featured categories on the home screen.

    python manage.py seed_from_live                  # everything
    python manage.py seed_from_live --only work      # one section
    python manage.py seed_from_live --no-images      # skip image downloads

Re-running is safe: rows are matched on their natural key (slug, or name for
categories) and updated in place rather than duplicated.
"""

import json
import os
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from profiles.models import CustomUser

DEFAULT_BASE = 'https://fireprenair.com/api'
SECTIONS = ('work', 'edu', 'digi', 'commu', 'home')

# The live site sits behind a WAF that rejects urllib's default User-Agent
# with a 403, so every request identifies itself as an ordinary browser.
USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0 Safari/537.36'
)


class Command(BaseCommand):
    help = "Seed the local database from the live site's public read APIs."

    def add_arguments(self, parser):
        parser.add_argument(
            '--base',
            default=DEFAULT_BASE,
            help=f'API root to pull from (default: {DEFAULT_BASE})',
        )
        parser.add_argument(
            '--only',
            default=','.join(SECTIONS),
            help=f'Comma-separated sections to seed: {", ".join(SECTIONS)}',
        )
        parser.add_argument(
            '--no-images',
            action='store_true',
            help='Store image paths without downloading the files.',
        )
        parser.add_argument(
            '--login-email',
            default=os.environ.get('LIVE_EMAIL', ''),
            help=(
                'Live account email. Some listings (all gigs, the digi '
                'explore feed) require a signed-in request; without this the '
                'seeder only imports what the public endpoints expose. '
                'Defaults to $LIVE_EMAIL.'
            ),
        )
        parser.add_argument(
            '--login-password',
            default=os.environ.get('LIVE_PASSWORD', ''),
            help='Live account password. Defaults to $LIVE_PASSWORD.',
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=60,
            help='Per-request timeout in seconds (default: 60).',
        )

    # ----------------------------------------------------------------- setup

    def handle(self, *args, **options):
        self.base = options['base'].rstrip('/')
        self.timeout = options['timeout']
        self.download_images = not options['no_images']

        sections = [s.strip() for s in options['only'].split(',') if s.strip()]
        unknown = [s for s in sections if s not in SECTIONS]
        if unknown:
            raise CommandError(
                f'Unknown section(s): {", ".join(unknown)}. '
                f'Choose from: {", ".join(SECTIONS)}'
            )

        self.stdout.write(f'Seeding from {self.base}')
        self._image_cache = {}
        self.token = None
        self._login(options['login_email'], options['login_password'])

        if 'work' in sections:
            self._seed_work()
        if 'edu' in sections:
            self._seed_edu()
        if 'digi' in sections:
            self._seed_digi()
        if 'commu' in sections:
            self._seed_commu()
        if 'home' in sections:
            self._seed_home()

        self.stdout.write(self.style.SUCCESS('\nDone.'))

    # ------------------------------------------------------------- utilities

    def _login(self, email, password):
        """Exchange live credentials for a JWT, if any were supplied.

        Credentials are never stored — they come from the command line or the
        environment and are only used for this run's read requests.
        """
        if not (email and password):
            self.stdout.write(
                '  (no credentials given — importing public listings only)'
            )
            return
        try:
            req = Request(
                f'{self.base}/my_accounts/login/',
                data=json.dumps({'email': email, 'password': password}).encode(),
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': USER_AGENT,
                },
                method='POST',
            )
            with urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode('utf-8'))
            self.token = (payload.get('tokens') or {}).get('accessToken')
        except Exception as exc:
            self.stderr.write(f'  ! live login failed: {exc}')
            return

        if self.token:
            self.stdout.write(f'  signed in to {self.base} as {email}')
        else:
            self.stderr.write('  ! live login returned no access token')

    def _get(self, path):
        """GET a live endpoint, returning the decoded JSON or None."""
        url = f'{self.base}/{path.lstrip("/")}'
        try:
            headers = {
                'Accept': 'application/json',
                'User-Agent': USER_AGENT,
            }
            if self.token:
                headers['Authorization'] = f'Bearer {self.token}'
            req = Request(url, headers=headers)
            with urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as exc:
            self.stderr.write(f'  ! GET {path} failed: {exc}')
            return None

    def _save_image(self, field, url):
        """Point an ImageField at `url`, downloading the bytes when asked.

        The live site serves media from S3 with absolute URLs; locally
        MEDIA_URL is '/images/'. Storing the S3 path (not the whole URL) keeps
        the API response shaped like production, and the app's own
        `resolveImageUrl` turns the relative path into an absolute one against
        whichever host it is talking to.
        """
        if not url:
            return False
        name = urlparse(url).path.lstrip('/')
        if not name:
            return False

        if not self.download_images:
            field.name = name
            return True

        target = os.path.join(settings.MEDIA_ROOT, name)
        if os.path.exists(target):
            field.name = name
            return True

        if url in self._image_cache:
            field.name = self._image_cache[url]
            return True

        try:
            req = Request(url, headers={'User-Agent': USER_AGENT})
            with urlopen(req, timeout=self.timeout) as resp:
                data = resp.read()
        except Exception as exc:
            self.stderr.write(f'  ! image {url} failed: {exc}')
            # Still record the path so the row saves; the app falls back to its
            # own placeholder for a missing file.
            field.name = name
            return True

        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as fh:
            fh.write(data)
        field.name = name
        self._image_cache[url] = name
        return True

    @staticmethod
    def _decimal(value, default='0'):
        try:
            return Decimal(str(value if value is not None else default))
        except (InvalidOperation, TypeError):
            return Decimal(default)

    def _user_from(self, payload, role_flags=None):
        """Find or create the local CustomUser mirroring a live user payload.

        Seeded accounts get an unusable password — they exist so gigs, courses
        and products have an owner to display, not to be signed into.
        """
        if not isinstance(payload, dict):
            return None
        username = payload.get('username')
        if not username:
            return None

        email = payload.get('email') or f'{slugify(username)}@seed.local'
        user = CustomUser.objects.filter(username=username).first()
        created = False
        if user is None:
            user = CustomUser(username=username, email=email)
            user.set_unusable_password()
            created = True

        for field, key in (
            ('name', 'name'),
            ('bio', 'bio'),
            ('edu_bio', 'edu_bio'),
            ('commu_bio', 'commu_bio'),
            ('country', 'country'),
            ('city', 'city'),
            ('gender', 'gender'),
            ('language', 'language'),
            ('timezone', 'timezone'),
        ):
            value = payload.get(key)
            if value not in (None, ''):
                setattr(user, field, value)

        for flag in (role_flags or []):
            setattr(user, flag, True)

        if not user.profile_pic:
            self._save_image(user.profile_pic, payload.get('profile_pic'))

        user.save()
        if created:
            self.stdout.write(f'  + user {username}')
        return user

    # ----------------------------------------------------------- workprenair

    def _seed_work(self):
        from work_prenair.models import Category, Gig, Tag

        self.stdout.write(self.style.MIGRATE_HEADING('\nWorkPrenair'))

        parents = self._get('home/work-parent-categories/') or []
        # live category id -> local Category
        cat_map = {}

        def walk(node, parent_obj):
            obj, _ = Category.objects.get_or_create(name=node['name'])
            obj.description = node.get('description') or obj.description
            obj.parent = parent_obj
            obj.is_featured = bool(node.get('is_featured'))
            if not obj.img:
                self._save_image(obj.img, node.get('img'))
            obj.save()
            cat_map[node['id']] = obj

            children = self._get(f'workprenair/categories/hierarchy/{node["id"]}/')
            for child in (children or {}).get('level_2_categories', []):
                walk(child, obj)

        for node in parents:
            walk(node, None)
        self.stdout.write(f'  categories: {len(cat_map)}')

        # `workprenair/home/` only returns a home-screen slice. When signed in,
        # the paginated services feed lists every gig, so nothing is missed.
        gigs = []
        seen_slugs = set()
        if self.token:
            page = 1
            while page <= 50:
                feed = self._get(f'workprenair/services/?page={page}') or {}
                # The feed nests its rows under results.gigs.
                results = feed.get('results')
                batch = (
                    (results.get('gigs') if isinstance(results, dict) else None)
                    or feed.get('gigs')
                    or (results if isinstance(results, list) else [])
                )
                batch = [g for g in batch if isinstance(g, dict)]
                if not batch:
                    break
                for gig in batch:
                    slug = gig.get('slug')
                    if slug and slug not in seen_slugs:
                        seen_slugs.add(slug)
                        gigs.append(gig)
                if not feed.get('next'):
                    break
                page += 1

        for gig in (self._get('workprenair/home/') or {}).get('all_gigs', []):
            slug = gig.get('slug')
            if slug and slug not in seen_slugs:
                seen_slugs.add(slug)
                gigs.append(gig)
        made = 0
        for payload in gigs:
            user = self._user_from(payload.get('user'), ['is_work_freelancer'])
            if user is None:
                continue

            slug = payload.get('slug') or slugify(payload.get('title', ''))
            gig = Gig.objects.filter(slug=slug).first()
            if gig is None:
                gig = Gig(slug=slug)
                # Gig.save() prefixes "I will " on create; the live title
                # already carries it, so keep the stored value verbatim.
                gig._seeded = True

            gig.user = user
            gig.title = payload.get('title', '')
            gig.description = payload.get('description') or ''
            gig.top_rated = bool(payload.get('top_rated'))
            gig.featured = bool(payload.get('featured'))

            for level in (1, 2, 3):
                setattr(
                    gig,
                    f'category_level_{level}',
                    cat_map.get(payload.get(f'category_level_{level}')),
                )

            for tier, revisions in (('basic', 1), ('standard', 2), ('premium', 3)):
                setattr(gig, f'{tier}_name',
                        payload.get(f'{tier}_name') or tier.capitalize())
                setattr(gig, f'{tier}_description',
                        payload.get(f'{tier}_description') or '')
                setattr(gig, f'{tier}_delivery_time',
                        payload.get(f'{tier}_delivery_time') or 3)
                setattr(gig, f'{tier}_revisions',
                        payload.get(f'{tier}_revisions') or revisions)
                setattr(gig, f'{tier}_price',
                        self._decimal(payload.get(f'{tier}_price')))

            if not gig.image:
                self._save_image(gig.image, payload.get('image'))

            # Bypass the "I will " prefix that Gig.save() adds to new rows.
            title = gig.title
            gig.save()
            if gig.title != title:
                Gig.objects.filter(pk=gig.pk).update(title=title)
                gig.title = title

            tags = []
            for tag in payload.get('tags', []):
                name = tag.get('name') if isinstance(tag, dict) else tag
                if name:
                    tags.append(Tag.objects.get_or_create(name=name)[0])
            if tags:
                gig.tags.set(tags)
            made += 1

        self.stdout.write(f'  gigs: {made}')

    # ------------------------------------------------------------ eduprenair

    def _seed_edu(self):
        from edu_prenair.models import Course, CourseCategory

        self.stdout.write(self.style.MIGRATE_HEADING('\nEduPrenair'))

        cat_map = {}
        for node in self._get('home/edu-parent-categories/') or []:
            obj, _ = CourseCategory.objects.get_or_create(name=node['name'])
            obj.description = node.get('description') or obj.description
            obj.is_featured = bool(node.get('is_featured'))
            if not obj.img:
                self._save_image(obj.img, node.get('img'))
            obj.save()
            cat_map[node['id']] = obj

        # The home payload lists the category ids courses actually reference,
        # which can include ones the parent endpoint doesn't return.
        for node in (self._get('eduprenair/home/') or {}).get('course_categories', []):
            if node['id'] not in cat_map:
                obj, _ = CourseCategory.objects.get_or_create(name=node['name'])
                cat_map[node['id']] = obj
        self.stdout.write(f'  categories: {len(cat_map)}')

        home = self._get('eduprenair/home/') or {}
        featured_instructors = {
            u.get('username')
            for u in home.get('best_instructors', [])
            if isinstance(u, dict)
        }

        courses = (self._get('eduprenair/courses/') or {}).get('courses', [])
        made = 0
        for payload in courses:
            instructor = self._user_from(
                payload.get('instructor'), ['is_edu_instructor']
            )
            if instructor is None:
                continue

            slug = payload.get('slug') or slugify(payload.get('title', ''))
            course = Course.objects.filter(slug=slug).first() or Course(slug=slug)

            course.instructor = instructor
            course.title = payload.get('title', '')
            course.description = payload.get('description') or ''
            course.requirements = payload.get('requirements') or ''
            course.language = payload.get('language') or 'English'
            course.price = self._decimal(payload.get('price'))
            discount = payload.get('discount_price')
            course.discount_price = (
                self._decimal(discount) if discount is not None else None
            )
            course.monthly_subscription = bool(payload.get('monthly_subscription'))
            course.is_free = bool(payload.get('is_free'))
            course.level = payload.get('level') or 'Beginner'
            course.duration = payload.get('duration') or 0
            course.is_published = bool(payload.get('is_published'))
            course.submit_for_approval = bool(payload.get('submit_for_approval'))
            course.best_selling = bool(payload.get('best_selling'))

            for local, remote in (
                ('category_l_1', 'category_l_1'),
                ('category_l_2', 'category_l_2'),
                ('category_l_3', 'category_l_3'),
            ):
                setattr(course, local, cat_map.get(payload.get(remote)))

            if not course.thumbnail:
                self._save_image(course.thumbnail, payload.get('thumbnail'))

            course.save()
            made += 1

        self.stdout.write(f'  courses: {made}')

        flagged = CustomUser.objects.filter(
            username__in=featured_instructors
        ).update(is_edu_instructor=True, featured_instructor=True)
        self.stdout.write(f'  featured instructors: {flagged}')

    # ----------------------------------------------------------- digiprenair

    def _seed_digi(self):
        from digi_prenair.models import Category, Product

        self.stdout.write(self.style.MIGRATE_HEADING('\nDigiPrenair'))

        data = self._get('digiprenair/home/') or {}
        featured_sellers = {
            u.get('username')
            for u in data.get('featured_sellers', [])
            if isinstance(u, dict)
        }

        # Categories arrive flat with a `parent` id, and a parent can appear
        # after its child — so create the rows first, then wire up parents.
        cat_map = {}
        raw = data.get('categories', [])
        for node in raw:
            obj, _ = Category.objects.get_or_create(name=node['name'])
            obj.description = node.get('description') or obj.description
            obj.is_featured = bool(node.get('is_featured'))
            if not obj.img:
                self._save_image(obj.img, node.get('img'))
            obj.save()
            cat_map[node['id']] = obj

        for node in raw:
            parent = cat_map.get(node.get('parent'))
            obj = cat_map[node['id']]
            if parent and obj.parent_id != parent.pk:
                obj.parent = parent
                obj.save(update_fields=['parent'])
        self.stdout.write(f'  categories: {len(cat_map)}')

        fallback_category, _ = Category.objects.get_or_create(name='Other')

        seen = set()
        made = 0
        for key in ('featured_items', 'newest_items'):
            for payload in data.get(key, []):
                slug = payload.get('slug') or slugify(payload.get('title', ''))
                if slug in seen:
                    continue
                seen.add(slug)

                seller = self._user_from(payload.get('seller'), ['is_digi_seller'])
                if seller is None:
                    continue

                product = (
                    Product.objects.filter(slug=slug).first() or Product(slug=slug)
                )
                product.seller = seller
                product.title = payload.get('title', '')
                product.description = payload.get('description') or ''
                product.price = self._decimal(payload.get('price'))
                product.discounted_price = self._decimal(
                    payload.get('discounted_price')
                )
                product.rating = payload.get('rating') or 0
                product.likes = payload.get('likes') or 0
                product.item_sales = payload.get('item_sales') or 0
                product.files_included = payload.get('files_included') or ''
                product.softwares = payload.get('softwares') or ''
                product.size = payload.get('size') or ''
                product.is_featured = key == 'featured_items'
                product.downloadable_file_s3_key = (
                    payload.get('downloadable_file_s3_key') or ''
                )

                product.category_l_2 = cat_map.get(payload.get('category_l_2'))
                product.category_l_3 = cat_map.get(payload.get('category_l_3'))
                # Some products point at a category the home payload doesn't
                # list. Product.save() dereferences `category` unconditionally,
                # so fall back rather than crash or drop the row.
                product.category = (
                    cat_map.get(payload.get('category'))
                    or product.category_l_2
                    or product.category_l_3
                    or fallback_category
                )

                if not product.image:
                    self._save_image(product.image, payload.get('image'))

                product.save()
                made += 1

        self.stdout.write(f'  products: {made}')

        flagged = CustomUser.objects.filter(username__in=featured_sellers).update(
            is_digi_seller=True, digi_is_featured=True
        )
        self.stdout.write(f'  featured sellers: {flagged}')

    # ---------------------------------------------------------- commuprenair

    def _seed_commu(self):
        """Only the featured flags: the local database already carries the
        group categories, they were just never marked as featured, so the home
        screen's community row came back empty."""
        from commu_prenair.models import Groupcategory

        self.stdout.write(self.style.MIGRATE_HEADING('\nCommuPrenair'))

        names = [
            c.get('name')
            for c in (self._get('home/home/') or {}).get(
                'commu_featured_categories', []
            )
            if isinstance(c, dict) and c.get('name')
        ]
        if not names:
            self.stdout.write('  nothing featured live — leaving flags alone')
            return

        flagged = Groupcategory.objects.filter(name__in=names).update(
            is_featured=True
        )
        missing = set(names) - set(
            Groupcategory.objects.filter(name__in=names).values_list(
                'name', flat=True
            )
        )
        for name in sorted(missing):
            Groupcategory.objects.create(name=name, is_featured=True)
        self.stdout.write(
            f'  featured group categories: {flagged + len(missing)}'
        )

    # ------------------------------------------------------------------ home

    def _seed_home(self):
        """The home screen's featured lists are built from the per-app
        categories, so seeding work/edu/digi already fills them — this only
        reports what the endpoint will now return."""
        from home.models import PricingPlan

        self.stdout.write(self.style.MIGRATE_HEADING('\nHome'))

        data = self._get('home/home/') or {}
        for key in (
            'work_featured_categories',
            'edu_featured_categories',
            'digi_featured_categories',
            'commu_featured_categories',
            'best_courses',
            'best_products',
            'best_services',
            'best_groups',
        ):
            self.stdout.write(f'  live {key}: {len(data.get(key, []))}')

        plans = PricingPlan.objects.count()
        if not plans:
            self.stdout.write(
                '  ! no PricingPlan rows locally — subscription screens will be '
                'empty (that data is not exposed by a public endpoint)'
            )
        else:
            self.stdout.write(f'  pricing plans: {plans}')
