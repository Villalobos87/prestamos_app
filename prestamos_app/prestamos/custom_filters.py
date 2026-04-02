from django import template
from functools import reduce
import operator

register = template.Library()

@register.filter
def sum_list(value):
    """Suma todos los elementos de una lista."""
    if not value:
        return 0
    return reduce(operator.add, value)