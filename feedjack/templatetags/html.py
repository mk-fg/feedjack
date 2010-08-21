from __future__ import unicode_literals
import itertools as it, operator as op, functools as ft

from django import template
register = template.Library()


from django.utils.encoding import smart_unicode
from django.utils.safestring import mark_safe
from BeautifulSoup import BeautifulSoup, Tag

def soupify(soup):
	return soup if isinstance(soup, (BeautifulSoup, Tag))\
		else BeautifulSoup(soup)

def desoupify(soup): return mark_safe(smart_unicode(soup))


@register.filter
def tag_pick_text(soup, sep=' '):
	return sep.join(soupify(soup).findAll(text=True))

@register.filter
def tag_pick(soup, tag):
	return mark_safe(soupify(soup).find(tag))

@register.filter
def tag_attr_add(soup, attrspec):
	if not soup: return ''
	soup = soupify(soup)
	for attr in attrspec.split('|'):
		var, val = attr.split('=', 1)
		soup[var] = val
	return mark_safe(soup)
