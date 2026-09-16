"""Create the four subscription plans the live site sells.

`PricingPlan` has no public read endpoint, so `seed_from_live` can't import it
and a fresh database ends up with none — which makes the pricing screen empty
and `dashboard/billing/` answer 404 ("No PricingPlan matches the given
query"). The plan names, prices and per-plan feature matrix below are
transcribed from https://fireprenair.com/pricing/.

    python manage.py seed_pricing_plans

Re-running updates the existing rows in place instead of adding duplicates.
Stripe ids are left blank: those are environment-specific and checkout stays
unavailable locally until they're filled in.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from home.models import Feature, PlanFeature, PricingPlan

# `access_to_dept` is how many of the four departments (Work/Edu/Digi/Commu)
# the plan unlocks; every tier on the live site gets all four.
ALL_DEPARTMENTS = 4

# Flutter's ApiEndpoints.checkout() addresses plans by id 2/3/4, with the free
# tier as 1, so the ids are pinned rather than left to autoincrement.
PLANS = [
    {
        'pk': 1,
        # Three code paths look this plan up by the exact string 'FreeTier'
        # (home/views.py, dashboard/views_payouts.py, core_api/dashboard_views.py);
        # the templates render the spaced "Free Tier" for display.
        'title': 'FreeTier',
        'price_monthly': '0.00',
        'price_annual': '0.00',
        'description': 'Get started at no cost with limited products, '
                       'services and marketplace exposure.',
        'product_limit': 3,
        'service_limit': 3,
        'support_limit': 'Email Support',
        'ai_tools_limit': 'AI Chatbot for Business Support',
    },
    {
        'pk': 2,
        'title': 'StartPrenair',
        'price_monthly': '11.99',
        'price_annual': '119.88',
        'description': 'For new entrepreneurs: featured exposure, VIP '
                       'support and the core AI tools.',
        'product_limit': 25,
        'service_limit': 25,
        'support_limit': 'VIP Support',
        'ai_tools_limit': 'AI Chatbot, AI Support in Chat, AI Service '
                          'Optimization, AI SEO Optimization',
    },
    {
        'pk': 3,
        'title': 'BizPrenair',
        'price_monthly': '24.99',
        'price_annual': '350.99',
        'description': 'For growing businesses: advanced analytics, verified '
                       'badge, priority support and AI exams.',
        'product_limit': 500,
        'service_limit': 500,
        'support_limit': 'VIP Support',
        'ai_tools_limit': 'All StartPrenair AI tools plus AI Sentiment '
                          'Analysis and AI Exams',
    },
    {
        'pk': 4,
        'title': 'EntrePrenair',
        'price_monthly': '44.99',
        'price_annual': '479.88',
        'description': 'Everything unlimited, with VVIP support, advanced '
                       'security and early access to new features.',
        # `product_limit` / `service_limit` are integers, so "unlimited" is
        # represented by the sentinel the feature matrix spells out in words.
        'product_limit': 0,
        'service_limit': 0,
        'support_limit': 'VVIP Support',
        'ai_tools_limit': 'Every AI tool on the platform',
    },
]

# (name, data_type) in the order the live pricing table lists them.
FEATURES = [
    ('Products', 'string'),
    ('Services', 'string'),
    ('Marketplace Exposure', 'string'),
    ('Support', 'string'),
    ('Community Access', 'string'),
    ('Payout via Paypal & Payoneer', 'boolean'),
    ('AI Chatbot for Business Support', 'boolean'),
    ('Course Creation', 'boolean'),
    ('AI Support in Chat', 'boolean'),
    ('AI Service Optimization', 'boolean'),
    ('AI SEO Optimization', 'boolean'),
    ('AI Sentiment Analysis', 'boolean'),
    ('Advanced Analytics', 'boolean'),
    ('Verified Badge', 'boolean'),
    ('Priority Support', 'boolean'),
    ('AI Exams', 'boolean'),
    ('Advanced Security & Fraud Protection', 'boolean'),
    ('Early Access to New Features', 'boolean'),
]

# feature name -> value per plan title. 'no' marks the greyed-out rows.
MATRIX = {
    'Products': {
        'FreeTier': '3', 'StartPrenair': '25',
        'BizPrenair': '500', 'EntrePrenair': 'Unlimited',
    },
    'Services': {
        'FreeTier': '3', 'StartPrenair': '25',
        'BizPrenair': '500', 'EntrePrenair': 'Unlimited',
    },
    'Marketplace Exposure': {
        'FreeTier': 'Limited', 'StartPrenair': 'Featured',
        'BizPrenair': 'Featured', 'EntrePrenair': 'Featured',
    },
    'Support': {
        'FreeTier': 'Email', 'StartPrenair': 'VIP',
        'BizPrenair': 'VIP', 'EntrePrenair': 'VVIP',
    },
    'Community Access': {
        'FreeTier': 'Limited', 'StartPrenair': 'Featured',
        'BizPrenair': 'Featured', 'EntrePrenair': 'Featured',
    },
    'Payout via Paypal & Payoneer': {
        'FreeTier': 'yes', 'StartPrenair': 'yes',
        'BizPrenair': 'yes', 'EntrePrenair': 'yes',
    },
    'AI Chatbot for Business Support': {
        'FreeTier': 'yes', 'StartPrenair': 'yes',
        'BizPrenair': 'yes', 'EntrePrenair': 'yes',
    },
    'Course Creation': {
        'FreeTier': 'no', 'StartPrenair': 'yes',
        'BizPrenair': 'yes', 'EntrePrenair': 'yes',
    },
    'AI Support in Chat': {
        'FreeTier': 'no', 'StartPrenair': 'yes',
        'BizPrenair': 'yes', 'EntrePrenair': 'yes',
    },
    'AI Service Optimization': {
        'FreeTier': 'no', 'StartPrenair': 'yes',
        'BizPrenair': 'yes', 'EntrePrenair': 'yes',
    },
    'AI SEO Optimization': {
        'FreeTier': 'no', 'StartPrenair': 'yes',
        'BizPrenair': 'yes', 'EntrePrenair': 'yes',
    },
    'AI Sentiment Analysis': {
        'FreeTier': 'no', 'StartPrenair': 'no',
        'BizPrenair': 'yes', 'EntrePrenair': 'yes',
    },
    'Advanced Analytics': {
        'FreeTier': 'no', 'StartPrenair': 'no',
        'BizPrenair': 'yes', 'EntrePrenair': 'yes',
    },
    'Verified Badge': {
        'FreeTier': 'no', 'StartPrenair': 'no',
        'BizPrenair': 'yes', 'EntrePrenair': 'yes',
    },
    'Priority Support': {
        'FreeTier': 'no', 'StartPrenair': 'no',
        'BizPrenair': 'yes', 'EntrePrenair': 'yes',
    },
    'AI Exams': {
        'FreeTier': 'no', 'StartPrenair': 'no',
        'BizPrenair': 'yes', 'EntrePrenair': 'yes',
    },
    'Advanced Security & Fraud Protection': {
        'FreeTier': 'no', 'StartPrenair': 'no',
        'BizPrenair': 'no', 'EntrePrenair': 'yes',
    },
    'Early Access to New Features': {
        'FreeTier': 'no', 'StartPrenair': 'no',
        'BizPrenair': 'no', 'EntrePrenair': 'yes',
    },
}


class Command(BaseCommand):
    help = 'Create/refresh the four subscription plans and their feature matrix.'

    @transaction.atomic
    def handle(self, *args, **options):
        features = {}
        for order, (name, data_type) in enumerate(FEATURES, start=1):
            feature, _ = Feature.objects.get_or_create(
                name=name, defaults={'data_type': data_type, 'order': order}
            )
            if feature.data_type != data_type or feature.order != order:
                feature.data_type = data_type
                feature.order = order
                feature.save(update_fields=['data_type', 'order'])
            features[name] = feature
        self.stdout.write(f'features: {len(features)}')

        for spec in PLANS:
            plan, created = PricingPlan.objects.update_or_create(
                pk=spec['pk'],
                defaults={
                    'title': spec['title'],
                    'price_monthly': Decimal(spec['price_monthly']),
                    'price_annual': Decimal(spec['price_annual']),
                    'description': spec['description'],
                    'access_to_dept': ALL_DEPARTMENTS,
                    'product_limit': spec['product_limit'],
                    'service_limit': spec['service_limit'],
                    'support_limit': spec['support_limit'],
                    'ai_tools_limit': spec['ai_tools_limit'],
                },
            )
            for name, feature in features.items():
                value = MATRIX[name].get(spec['title'], 'no')
                PlanFeature.objects.update_or_create(
                    plan=plan, feature=feature, defaults={'value': value}
                )
            verb = 'created' if created else 'updated'
            self.stdout.write(
                f'  {verb}: {plan.title} '
                f'(${plan.price_monthly}/mo, ${plan.price_annual}/yr)'
            )

        missing_stripe = PricingPlan.objects.filter(
            stripe_price_id_monthly=''
        ).exclude(pk=1).count()
        if missing_stripe:
            self.stdout.write(
                self.style.WARNING(
                    f'  {missing_stripe} paid plan(s) have no Stripe price id — '
                    'checkout will not work until those are set.'
                )
            )
        self.stdout.write(self.style.SUCCESS('Done.'))
