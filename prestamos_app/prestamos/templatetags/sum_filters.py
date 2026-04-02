from django import template

register = template.Library()

@register.filter
def sum_attr(queryset, attr_name):
    """Suma un atributo de todos los objetos en un queryset"""
    return sum(getattr(obj, attr_name, 0) or 0 for obj in queryset)