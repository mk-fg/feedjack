import itertools as it, operator as op, functools as ft


import re
def _regex_search(post, parameter, dissector):
	return bool(re.search(parameter, dissector(post).strip()))

# Simple regex-based filters
regex_search_title = ft.partial(_regex_search, dissector=op.attrgetter('title'))
regex_search_content = ft.partial(_regex_search, dissector=op.attrgetter('content'))
