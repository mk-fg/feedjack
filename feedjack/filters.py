import itertools as it, operator as op, functools as ft


import re
def _regex_search(post, parameter, dissector):
	return bool(re.search(parameter, dissector(post).strip()))

# Simple regex-based filters
regex_search_title = ft.partial(_regex_search, dissector=op.attrgetter('title'))
regex_search_content = ft.partial(_regex_search, dissector=op.attrgetter('content'))


DEFAULT_SIMILARITY_THRESHOLD = 0.85
DEFAULT_SIMILARITY_TIMESPAN = 7 * 24 * 3600

# from datetime import datetime, timedelta

# def title_similarity(post, parameter=None):
# 	from feedjack.models import Post
# 	if parameter:
# 		parameter = map(op.methodcaller('strip'), parameter.split(',', 1))
# 		threshold = parameter.pop()
# 		try: threshold, timespan = parameter.pop(), threshold
# 		except IndexError: timespan = DEFAULT_SIMILARITY_TIMESPAN
# 		threshold, timespan = float(threshold), int(timespan)
# 	else:
# 		threshold, timespan = DEFAULT_SIMILARITY_THRESHOLD, DEFAULT_SIMILARITY_TIMESPAN
# 	similar = Post.objects.filtered().similar(threshold, title=post.title)\
# 		.filter(date_updated__gt=datetime.now() - timedelta(seconds=timespan)
# 	similar = similar.filter(
# 	return not bool(Post.objects.filtered().similar(threshold, title=post.title)\
# 		)[:1])
