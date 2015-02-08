# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import itertools as it, operator as op, functools as ft
from hashlib import sha256 as hash_func

from django.template.defaultfilters import stringfilter
from django.utils.safestring import SafeData, mark_safe

from django import template
register = template.Library()


from feedjack.fjlib import html_cleaner
from django.utils.html import escape

@register.filter
@stringfilter
def prettyhtml(value, autoescape=None):
	'Clean (and optionally escape) passed html of unsafe tags and attributes.'
	value = html_cleaner(value)
	return escape(value) if autoescape\
		and not isinstance(value, SafeData) else mark_safe(value)

@register.filter
@stringfilter
def hash(value, chars=None):
	'Get N chars (default: all) of secure hash hexdigest of value.'
	value = hash_func(value).hexdigest()
	if chars: value = value[:chars]
	return mark_safe(value)


# lxml is hard-dep in fern style only, at least initially
try: from feedjack.fjlib import lxml_soup, lxml_tostring
except ImportError: pass
else:
	@register.filter
	@stringfilter
	def tag_pick_text(soup):
		'Strip all tags from passed html fragment, returning only text they contain.'
		return lxml_soup(soup).text_content()

	@register.filter
	@stringfilter
	def tag_pick(soup, xpaths):
		'Pick subset from passed html fragment by xpath.'
		for xpath in xpaths.split(u'||'):
			match = lxml_soup(soup).xpath(xpath)
			if match: return lxml_tostring(match[0])
		else: return soup

	@register.filter
	@stringfilter
	def tag_attr_add(soup, attrspec):
		'''Add html attribute(s) to a root tag of a passed html fragment.
			Attributes should be specified in "{k1}={v1}|{k2}={v2}|..." form.
			Example: "class=pull-right clear|title=Some floater element"'''
		if not soup: return ''
		soup = lxml_soup(soup)
		for attr in attrspec.split('|'):
			var, val = attr.split('=', 1)
			soup.attrib[var] = val
		return mark_safe(lxml_tostring(soup))

	# List of attributes that don't affect style of elements.
	#  http://www.w3.org/TR/html4/index/attributes.html
	#  http://packages.python.org/feedparser/html-sanitization.html
	nostyle_allowed_attrs = frozenset([
		'abbr', 'accesskey', 'alt', 'axis', 'char', 'charoff', 'charset', 'checked', 'cite',
		'clear', 'cols', 'colspan', 'compact', 'coords', 'datetime', 'dir', 'disabled',
		'for', 'frame', 'headers', 'href', 'hreflang', 'ismap', 'label', 'lang', 'longdesc',
		'maxlength', 'media', 'multiple', 'nohref', 'noshade', 'nowrap', 'prompt',
		'readonly', 'rel', 'rev', 'rows', 'rowspan', 'rules', 'scope', 'selected', 'shape',
		'span', 'src', 'start', 'summary', 'tabindex', 'title', 'type', 'usemap', 'value' ])

	@register.filter
	@stringfilter
	def prettyhtml_nostyle(soup, autoescape=None):
		'''Cleans up html fragment, just like "prettyhtml" does,
			but also strips all style-affecting attributes (classes, width, size, etc) from it.'''
		if not soup: return ''
		soup = lxml_soup(soup)
		for e in soup.iter():
			attrs = e.attrib
			for name in attrs.keys():
				if name not in nostyle_allowed_attrs: del attrs[name]
		soup = lxml_tostring(soup)
		return escape(soup) if autoescape\
			and not isinstance(soup, SafeData) else mark_safe(soup)
