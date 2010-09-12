import itertools as it, operator as op, functools as ft



### Simple regex-based filters
import re
def _regex_search(post, parameter, dissector):
	return bool(re.search(parameter, dissector(post).strip()))

regex_in_title = ft.partial(_regex_search, dissector=op.attrgetter('title'))
regex_in_title.__doc__ = 'Match only posts with RegEx'\
	' found in title. Parameter: RegEx (python style, mandatory).'
regex_in_content = ft.partial(_regex_search, dissector=op.attrgetter('content'))
regex_in_content.__doc__ = 'Match only posts with RegEx'\
	' found in content. Parameter: RegEx (python style, mandatory).'



### Similarity cross-referencing filters
DEFAULT_SIMILARITY_THRESHOLD = 0.85
DEFAULT_SIMILARITY_TIMESPAN = 7 * 24 * 3600

from datetime import datetime, timedelta
import types

def same_guid(post, parameter=DEFAULT_SIMILARITY_TIMESPAN):
	'''Skip posts with exactly same GUID.
		Parameter: comparison timespan, seconds (int, 0 = inf).'''
	from feedjack.models import Post
	if isinstance(parameter, types.StringTypes): parameter = int(parameter.strip())
	similar = Post.objects.filtered().exclude(id=post.id).filter(guid=post.guid)
	if parameter:
		similar = similar.filter(date_updated__gt=datetime.now() - timedelta(seconds=parameter))
	return not bool(similar.exists())

def similar_title(post, parameter=None):
	'''Skip posts with fuzzy-matched (threshold = levenshtein distance / length) title.
		Parameters (comma-delimited):
			minimal threshold, at which values are considired similar (float, 0 < x < 1);
			comparison timespan, seconds (int, 0 = inf).'''
	from feedjack.models import Post
	threshold, timespan = DEFAULT_SIMILARITY_THRESHOLD, DEFAULT_SIMILARITY_TIMESPAN
	if parameter:
		parameter = map(op.methodcaller('strip'), parameter.split(',', 1))
		threshold = parameter.pop()
		try: threshold, timespan = parameter.pop(), threshold
		except IndexError: pass
		threshold, timespan = float(threshold), int(timespan)
	similar = Post.objects.filtered().exclude(id=post.id).similar(threshold, title=post.title)
	if timespan:
		similar = similar.filter(date_updated__gt=datetime.now() - timedelta(seconds=timespan))
	return not bool(similar.exists())
