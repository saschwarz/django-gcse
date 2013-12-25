# from http://www.djangosnippets.org/snippets/67/
# Put settings values into template files

from django import template
from django.conf import settings
from django.contrib.sites.models import Site


register = template.Library()

def setting(name):
    return str(settings.__getattr__(name))
register.simple_tag(setting)


def site(name):
    return Site.objects.get_current().__getattribute__(name)
register.simple_tag(site)
