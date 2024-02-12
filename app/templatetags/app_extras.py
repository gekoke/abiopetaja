from django import template

register = template.Library()


@register.filter(name="zip")
def zip_template_filter(a, b):
    return zip(a, b)
