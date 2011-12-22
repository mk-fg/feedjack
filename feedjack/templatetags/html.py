from __future__ import unicode_literals
import itertools as it, operator as op, functools as ft

from django.template.defaultfilters import stringfilter
from django.utils.safestring import SafeData, mark_safe
from feedjack.fjlib import html_cleaner

from django import template
register = template.Library()


from django.utils.html import escape

@register.filter
@stringfilter
def prettyhtml(value, autoescape=None):
	value = html_cleaner(value)
	return escape(value) if autoescape\
		and not isinstance(value, SafeData) else mark_safe(value)


# lxml is hard-dep in fern style only, at least initially
try: from feedjack.fjlib import lxml_soup, lxml_tostring
except ImportError: pass
else:
	@register.filter
	@stringfilter
	def tag_pick_text(soup):
		return mark_safe(lxml_soup(soup).text_content())

	@register.filter
	@stringfilter
	def tag_pick(soup, xpaths):
		for xpath in xpaths.split(u'||'):
			match = lxml_soup(soup).xpath(xpath)
			if match: return lxml_tostring(match[0])
		else: return soup

	@register.filter
	@stringfilter
	def tag_attr_add(soup, attrspec):
		if not soup: return ''
		soup = lxml_soup(soup)
		for attr in attrspec.split('|'):
			var, val = attr.split('=', 1)
			soup.attrib[var] = val
		return mark_safe(lxml_tostring(soup))
