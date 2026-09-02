from django import template
from ..models import Course

register = template.Library()

@register.filter
def in_wishlist(course, user):
    if course is not None and user.is_authenticated:
        return course.check_wishlist(user)
    return False



@register.filter
def is_user_enrolled(course, user):
    """Check if a user is enrolled in a specific course."""
    if course is not None and user.is_authenticated:
        return course.is_user_enrolled(user)
    return False


@register.filter
def is_liked(post, user):
    """Check if a user has liked a post."""
    if post is not None and user.is_authenticated:
        return post.like(user)
    return False

@register.filter
def is_member(group, user):
    """Check if a user is a member of group."""
    if group is not None and user.is_authenticated:
        return group.is_member(user)
    return False


@register.filter
def is_pending(group, user):
    """Check if a user has pending request to join group."""
    if group is not None and user.is_authenticated:
        return group.is_pending(user)
    return False


@register.filter
def is_admin(group, user):
    """Check if a user is an admin of group."""
    if group is not None and user.is_authenticated:
        return group.is_admin(user)
    return False


@register.filter
def mutual_connections(user, other_user):
    """return queryset of mutual connections between two users."""
    if user.is_authenticated:
        return user.mutual_connections(other_user)
    return False



@register.filter
def mutual_connections_count(user, other_user):
    """return count of mutual connections between two users."""
    if user.is_authenticated:
        return user.mutual_connections_count(other_user)
    return False


@register.filter
def is_friend_request_pending(user, other_user):
    """Check if a friend request is pending."""
    if user.is_authenticated:
        return user.is_friend_request_pending(other_user)
    return False


@register.filter
def is_friend_request_received(user, other_user):
    """Check if a friend request is received."""
    if user.is_authenticated:
        return user.is_friend_request_received(other_user)
    return False


@register.filter
def is_already_connected(user, other_user):
    """Check if two users are already connected."""
    if user.is_authenticated:
        return user.is_already_connected(other_user)
    return False


@register.filter
def get_package_attribute(gig, attr_name):
    """
    Retrieve a package attribute dynamically for a given gig.
    Example: {{ gig|get_package_attribute:"basic_name" }}
    """
    return getattr(gig, attr_name, "")


@register.filter
def startswith(value, arg):
    """Check if a string starts with a given substring."""
    return value.startswith(arg)


@register.filter
def index(indexable, i):
    try:
        return indexable[i]
    except (IndexError, TypeError):
        return None
    

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, key)