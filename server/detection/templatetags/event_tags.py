from django import template

register = template.Library()

# Splits string into a list
@register.filter(name='split')
def split(value, key):
    return str(value).split(key)