# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import itertools as it, operator as op, functools as ft
import re, types



### Simple regex-based filters

def _regex_search(post, parameter, dissector, invert=False):
	return invert ^ bool(re.search(parameter, dissector(post).strip()))

regex_in_title = ft.partial(_regex_search, dissector=op.attrgetter('title'))
regex_in_title.__doc__ = 'Match only posts with RegEx'\
	' found in title. Parameter: RegEx (python style, mandatory).'
regex_in_content = ft.partial(_regex_search, dissector=op.attrgetter('content'))
regex_in_content.__doc__ = 'Match only posts with RegEx'\
	' found in content. Parameter: RegEx (python style, mandatory).'

regex_not_in_title = ft.partial(
	_regex_search, dissector=op.attrgetter('title'), invert=True )
regex_not_in_title.__doc__ = 'Match only posts with RegEx'\
	' NOT found in title. Parameter: RegEx (python style, mandatory).'
regex_not_in_content = ft.partial(
	_regex_search, dissector=op.attrgetter('content'), invert=True )
regex_not_in_content.__doc__ = 'Match only posts with RegEx'\
	' NOT found in content. Parameter: RegEx (python style, mandatory).'



### Similarity cross-referencing filters
from datetime import timedelta
from django.utils import timezone

DEFAULT_SIMILARITY_THRESHOLD = 0.85
DEFAULT_SIMILARITY_TIMESPAN = 7 * 24 * 3600

default_span_hr = unicode(timedelta(
	seconds=DEFAULT_SIMILARITY_TIMESPAN )).rsplit(', 0:00:00', 1)[0]


def same_guid(post, parameter=DEFAULT_SIMILARITY_TIMESPAN):
	'''Skip posts with exactly same GUID.
		Parameter: comparison timespan, seconds (int, 0 = inf, default: {0}).'''
	from feedjack.models import Post
	if isinstance(parameter, types.StringTypes): parameter = int(parameter.strip())
	similar = Post.objects.filtered(for_display=False)\
		.exclude(id=post.id).filter(guid=post.guid)
	if parameter:
		similar = similar.filter(date_updated__gt=timezone.now() - timedelta(seconds=parameter))
	return not bool(similar.exists())

same_guid.__doc__ = same_guid.__doc__.format(default_span_hr)


def similar_title(post, parameter=None):
	'''Skip posts with fuzzy-matched (threshold = levenshtein distance / length) title.
		Parameters (comma-delimited):
			minimal threshold, at which values are considired similar (float, 0 < x < 1, default: {0});
			comparison timespan, seconds (int, 0 = inf, default: {1}).'''
	from feedjack.models import Post
	threshold, timespan = DEFAULT_SIMILARITY_THRESHOLD, DEFAULT_SIMILARITY_TIMESPAN
	if parameter:
		parameter = map(op.methodcaller('strip'), parameter.split(',', 1))
		threshold = parameter.pop()
		try: threshold, timespan = parameter.pop(), threshold
		except IndexError: pass
		threshold, timespan = float(threshold), int(timespan)
	similar = Post.objects.filtered(for_display=False)\
		.exclude(id=post.id).similar(threshold, title=post.title)
	if timespan:
		similar = similar.filter(date_updated__gt=timezone.now() - timedelta(seconds=timespan))
	return not bool(similar.exists())

similar_title.__doc__ = similar_title.__doc__.format(
	DEFAULT_SIMILARITY_THRESHOLD, default_span_hr )



### Content processors

def pick_enclosure_link(post, parameter=''):
	'''Override URL of the Post to point to url of the first enclosure with
			href attribute non-empty and type matching specified regexp parameter (empty=any).
		Missing "type" attribute for enclosure will be matched as an empty string.
		If none of the enclosures match, link won't be updated.'''
	for e in (post.enclosures or list()):
		href = e.get('href')
		if not href: continue
		if parameter and not re.search(parameter, e.get('type', '')): continue
		return dict(link=href)
