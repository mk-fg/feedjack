# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import itertools as it, operator as op, functools as ft

from django import template
register = template.Library()


@register.filter
def site_ordering_date(item, site):
	return item.date_on_site(site)
