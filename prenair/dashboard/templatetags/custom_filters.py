from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    """ Add CSS class to form fields """
    return field.as_widget(attrs={"class": css_class})


@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value  # Return the original value if conversion fails
