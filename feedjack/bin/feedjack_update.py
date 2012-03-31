#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

VERSION = '0.9.16-fg3'
URL = 'http://www.feedjack.org/'
USER_AGENT = 'Feedjack {0} - {1}'.format(VERSION, URL)

import logging
logging.EXTRA = (logging.DEBUG + logging.INFO) // 2

from feedjack.fjupdater import bulk_update

if __name__ == '__main__':
	import optparse
	parser = optparse.OptionParser(usage='%prog [options]', version=USER_AGENT)

	parser.add_option('--force', action='store_true',
		help='Do not use stored modification time or etag when fetching feed updates.')
	parser.add_option('--hidden', action='store_true',
		help='Mark all fetched (new) posts as "hidden". Intended'
			' usage is initial fetching of large (number of) feeds.')

	parser.add_option('--max-feed-difference', action='store', dest='max_diff', type='int',
		help='Maximum percent of new posts to consider feed valid.'
			' Intended for broken feeds, which sometimes return seemingly-random content.')

	parser.add_option('-f', '--feed', action='append', type='int',
		help='A feed id to be updated. This option can be given multiple '
			'times to update several feeds at the same time (-f 1 -f 4 -f 7).')
	parser.add_option('-s', '--site', action='append', type='int',
		help='A site id (or several of them) to update.')

	parser.add_option('-t', '--timeout', type='int', default=20,
		help='Socket timeout (in seconds) for connections (default: %(default)s).')
	parser.add_option('-d', '--delay', type='int', default=0,
		help='Delay between fetching the feeds (default: none).')

	parser.add_option('-q', '--quiet', action='store_true',
		help='Report only severe errors, no info or warnings.')
	parser.add_option('-v', '--verbose', action='store_true', help='Verbose output.')
	parser.add_option('--debug', action='store_true', help='Even more verbose output.')

	optz,argz = parser.parse_args()
	if argz: parser.error('This command takes no arguments')

	if optz.debug: logging.basicConfig(level=logging.DEBUG)
	elif optz.verbose: logging.basicConfig(level=logging.EXTRA)
	elif optz.quiet: logging.basicConfig(level=logging.WARNING)
	else: logging.basicConfig(level=logging.INFO)

	bulk_update(optz)
