from __future__ import unicode_literals
import itertools as it, operator as op, functools as ft

from django import template
register = template.Library()


from django.utils.encoding import smart_unicode
from django.utils.safestring import mark_safe

@register.filter
def fold_check(item, request):
	try: folds = request.session['feedjack.folds']
	except KeyError: return ''
	if item.date_modified < folds[site.id].get(None, 0): return 'true' # fold-all
	ts_day = item.date_modified.strftime('%Y-%m-%d')
	return '' if item.date_modified > folds[site.id].get(ts_day, 0) else 'true' # fold-day
