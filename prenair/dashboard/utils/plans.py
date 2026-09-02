from home.models import UserPlan


def get_active_plan_name(user):
    try:
        active_plan = UserPlan.objects.filter(user=user, is_active=True).latest('start_date')
        return active_plan.plan.title if active_plan else None
    except UserPlan.DoesNotExist:
        return None
    

