from django import template
register = template.Library()

@register.filter
def dict_get(d, key):
    if isinstance(d, dict):
        return d.get(key, '🌿')
    return '🌿'

@register.filter
def split(value, delimiter=','):
    return [v.strip() for v in value.split(delimiter)]
