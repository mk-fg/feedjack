#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import itertools as it, operator as op, functools as ft
from datetime import datetime
from time import sleep
from collections import defaultdict
import os, sys

import feedparser, feedjack
from feedjack.models import transaction_wrapper, transaction, IntegrityError


USER_AGENT = 'Feedjack {} - {}'.format(feedjack.__version__, feedjack.__url__)
SLOWFEED_WARNING = 10

import codecs
codec = codecs.getwriter('utf-8')
sys.stdout = codec(sys.stdout)
sys.stderr = codec(sys.stderr)

import logging
logging.EXTRA = (logging.DEBUG + logging.INFO) // 2
log = logging.getLogger(os.path.basename(__file__))
log.extra = ft.partial(log.log, logging.EXTRA)
# TODO: special formatter to insert feed_id to the prefix


ENTRY_NEW, ENTRY_UPDATED,\
	ENTRY_SAME, ENTRY_ERR = xrange(4)

entry_keys = (
	(ENTRY_NEW, 'new'),
	(ENTRY_UPDATED, 'updated'),
	(ENTRY_SAME, 'same'),
	(ENTRY_ERR, 'error') )


FEED_OK, FEED_SAME, FEED_INVALID, FEED_ERRPARSE,\
	FEED_ERRFETCH, FEED_ERREXC = xrange(6)

feed_keys = (
	(FEED_OK, 'ok'),
	(FEED_SAME, 'unchanged'),
	(FEED_INVALID, 'validation_error'),
	(FEED_ERRPARSE, 'cant_parse'),
	(FEED_ERRFETCH, 'fetch_error'),
	(FEED_ERREXC, 'exception') )
feed_keys_dict = dict(feed_keys)

class FeedValidationError(Exception): pass


mtime = lambda ttime: datetime(*ttime[:6])

_exc_frame = '[{0}] ! ' + '-'*25 + '\n'
def print_exc(feed_id):
	import traceback
	sys.stderr.write(_exc_frame.format(feed_id))
	traceback.print_exc()
	sys.stderr.write(_exc_frame.format(feed_id))



class FeedProcessor(object):

	def __init__(self, feed, options):
		self.feed, self.options = feed, options
		self.fpf = None

	def _get_guid(self, fp_entry):
		return fp_entry.get('id', '') or fp_entry.get('title', '') or fp_entry.get('link', '')

	def process_entry(self, entry):
		'Construct a Post from a feedparser entry and save/update it in db'

		from feedjack.models import Post, Tag

		## Construct a Post object from feedparser entry (FeedParserDict)
		post = Post(feed=self.feed)
		post.link = entry.get('link', self.feed.link)
		post.title = entry.get('title', post.link)
		post.guid = self._get_guid(entry)

		if 'author_detail' in entry:
			post.author = entry.author_detail.get('name', '')
			post.author_email = entry.author_detail.get('email', '')
		if not post.author: post.author = entry.get('author', entry.get('creator', ''))
		if not post.author_email: post.author_email = 'nospam@nospam.com'

		try: post.content = entry.content[0].value
		except: post.content = entry.get('summary', entry.get('description', ''))

		post.date_modified = mtime(entry.modified_parsed)\
			if 'modified_parsed' in entry else None
		post.comments = entry.get('comments', '')

		## Get a list of tag objects from an entry
		# Note that these objects can't go into m2m field until properly saved
		fcat = list()
		if entry.has_key('tags'):
			for tcat in entry.tags:
				qcat = tcat.label if tcat.label is not None else tcat.term
				if not qcat: continue

				qcat = qcat.strip()
				if ',' in qcat or '/' in qcat: qcat = qcat.replace(',', '/').split('/')
				else: qcat = [qcat]

				for zcat in qcat:
					tagname = ' '.join(zcat.lower().split()).strip()
					if not tagname: continue
					if not Tag.objects.filter(name=tagname):
						cobj = Tag(name=tagname)
						cobj.save()
					fcat.append(Tag.objects.get(name=tagname))

		## Some feedback
		post_base_fields = 'title link guid author author_email'.split()

		log.debug('[{0}] Entry\n{1}'.format(self.feed.id, '\n'.join(
			['  {0}: {1}'.format(key, getattr(post, key)) for key in post_base_fields]
			+ ['tags: {0}'.format(' '.join(it.imap(op.attrgetter('name'), fcat)))] )))

		## Store / update a post
		if post.guid in self.postdict: # post exists, update if it was modified (and feed is mutable)
			post_old = self.postdict[post.guid]
			changed = post_old.content != post.content or (
				post.date_modified and post_old.date_modified != post.date_modified )

			if not self.feed.immutable and changed:
				retval = ENTRY_UPDATED
				log.extra('[{0}] Updating existing post: {1}'.format(self.feed.id, post.link))
				# Update fields
				for field in post_base_fields + ['content', 'comments']:
					setattr(post_old, field, getattr(post, field))
				post_old.date_modified = post.date_modified or post_old.date_modified
				# Update tags
				post_old.tags.clear()
				for tcat in fcat: post_old.tags.add(tcat)
				post_old.save()
			else:
				retval = ENTRY_SAME
				log.extra( ( '[{0}] Post has not changed: {1}' if not changed else
					'[{0}] Post changed, but feed is marked as immutable: {1}' )\
						.format(self.feed.id, post.link) )

		else: # new post, store it into database
			retval = ENTRY_NEW
			log.extra('[{0}] Saving new post: {1}'.format(self.feed.id, post.guid))
			# Try hard to set date_modified: feed.modified, http.modified and now() as a last resort
			if not post.date_modified and self.fpf:
				if self.fpf.feed.get('modified_parsed'):
					post.date_modified = mtime(self.fpf.feed.modified_parsed)
				elif self.fpf.get('modified'): post.date_modified = mtime(self.fpf.modified)
			if not post.date_modified: post.date_modified = datetime.now()
			if self.options.hidden: post.hidden = True
			try: post.save()
			except IntegrityError:
				log.error( 'IntegrityError while saving (supposedly) new'\
					' post with guid: {0.guid}, link: {0.link}, title: {0.title}'.format(post) )
				raise
			for tcat in fcat: post.tags.add(tcat)
			self.postdict[post.guid] = post

		return retval


	def process(self):
		tsp = transaction.savepoint()
		try:
			ret_feed, ret_entries = self._process()
			if ret_feed != FEED_OK: raise FeedValidationError()
		except FeedValidationError: # no extra noise necessary
			transaction.savepoint_rollback(tsp)
		except:
			print_exc(self.feed.id)
			ret_feed, ret_entries = FEED_ERREXC, dict()
			transaction.savepoint_rollback(tsp)
		else:
			transaction.savepoint_commit(tsp)
		return ret_feed, ret_entries


	def _process(self):
		'Downloads and parses a feed.'

		ret_values = {
			ENTRY_NEW: 0,
			ENTRY_UPDATED: 0,
			ENTRY_SAME: 0,
			ENTRY_ERR: 0 }

		log.info('[{0}] Processing feed {1}'.format(self.feed.id, self.feed.feed_url))

		try:
			self.fpf = feedparser.parse(
				self.feed.feed_url, agent=USER_AGENT,
				etag=self.feed.etag if not self.options.force else '' )
		except KeyboardInterrupt: raise
		except:
			log.error( 'Feed cannot be parsed: {0} (#{1})'\
				.format(self.feed.feed_url, self.feed.id) )
			return FEED_ERRPARSE, ret_values

		if hasattr(self.fpf, 'status'):
			log.extra('[{0}] HTTP status {1}: {2}'.format(
				self.feed.id, self.fpf.status, self.feed.feed_url ))
			if self.fpf.status == 304:
				log.extra(( '[{0}] Feed has not changed since '
					'last check: {1}' ).format(self.feed.id, self.feed.feed_url))
				return FEED_SAME, ret_values

			if self.fpf.status >= 400:
				log.warn('[{0}] HTTP error {1}: {2}'.format(
					self.feed.id, self.fpf.status, self.feed.feed_url ))
				return FEED_ERRFETCH, ret_values

		if self.fpf.bozo:
			bozo = getattr(self.fpf, 'bozo_exception', 'unknown error')
			if not self.feed.skip_errors:
				log.warn( '[{0}] Failed to fetch feed: {1} ({2})'\
					.format(self.feed.id, self.feed.feed_url, bozo) )
				return FEED_ERRFETCH, ret_values
			else:
				log.info( '[{0}] Skipped feed error: {1} ({2})'\
					.format(self.feed.id, self.feed.feed_url, bozo) )

		self.feed.title = self.fpf.feed.get('title', '')[0:254]
		self.feed.tagline = self.fpf.feed.get('tagline', '')
		self.feed.link = self.fpf.feed.get('link', '')
		self.feed.last_checked = datetime.now()

		log.debug('[{0}] Feed info for: {1}\n{2}'.format(
			self.feed.id, self.feed.feed_url, '\n'.join(
			'  {0}: {1}'.format(key, getattr(self.feed, key))
			for key in ['title', 'tagline', 'link', 'last_checked'] )))

		guids = filter(None, it.imap(self._get_guid, self.fpf.entries))
		if guids:
			from feedjack.models import Post
			self.postdict = dict( (post.guid, post)
				for post in Post.objects.filter(
					feed=self.feed.id ).filter(guid__in=guids) )
			if self.options.max_diff:
				diff = op.truediv(len(guids) - len(self.postdict), len(guids)) * 100
				if diff > self.options.max_diff:
					log.warn( '[{0}] Feed validation failed: {1} (diff: {2}% > {3}%)'\
						.format(self.feed.id, self.feed.feed_url, round(diff, 1), self.options.max_diff) )
					return FEED_INVALID, ret_values
		else: self.postdict = dict()

		self.feed.save() # etag/mtime aren't updated yet

		for entry in self.fpf.entries:
			tsp = transaction.savepoint()
			try: ret_entry = self.process_entry(entry)
			except:
				print_exc(self.feed.id)
				ret_entry = ENTRY_ERR
				transaction.savepoint_rollback(tsp)
			else:
				transaction.savepoint_commit(tsp)
			ret_values[ret_entry] += 1

		if not ret_values[ENTRY_ERR]: # etag/mtime updated only if there's no errors
			self.feed.etag = self.fpf.get('etag') or ''
			try: self.feed.last_modified = mtime(self.fpf.modified)
			except AttributeError: pass
			self.feed.save()

		return FEED_OK, ret_values



@transaction_wrapper(logging)
def bulk_update(optz):
	import socket
	socket.setdefaulttimeout(optz.timeout)


	from feedjack.models import Feed, Site
	affected_sites = set() # to drop cache

	if optz.feed:
		feeds = list(Feed.objects.filter(pk__in=optz.feed)) # no is_active check
		for feed_id in set(optz.feed).difference(it.imap(op.attrgetter('id'), feeds)):
			log.warn('Unknown feed id: {0}'.format(feed_id))
		affected_sites.update(Site.objects.filter(
			subscriber__feed__in=feeds ).values_list('id', flat=True))

	if optz.site:
		feeds = Feed.objects.filter( is_active=True,
			subscriber__site__pk__in=optz.site )
		sites = Site.objects.filter(pk__in=optz.site).values_list('id', flat=True)
		for site_id in set(optz.site).difference(sites):
			log.warn('Unknown site id: {0}'.format(site_id))
		affected_sites.update(sites)

	if not optz.feed and not optz.site: # fetches even unbound feeds
		feeds = Feed.objects.filter(is_active=True)
		affected_sites = Site.objects.all().values_list('id', flat=True)


	feeds, time_delta_global = list(feeds), datetime.now()
	log.info( '* BEGIN: {0}, feeds to process: {1}'\
		.format(time_delta_global, len(feeds)) )

	feed_stats, entry_stats = defaultdict(int), defaultdict(int)
	for feed in feeds:
		time_delta = datetime.now()
		ret_feed, ret_entries = FeedProcessor(feed, optz).process()
		time_delta = datetime.now() - time_delta

		log.info('[{0}] Processed {1} in {2}s [{3}] [{4}]{5}'.format(
			feed.id, feed.feed_url, time_delta, feed_keys_dict[ret_feed],
			' '.join('{0}={1}'.format( label,
				ret_entries.get(key, 0) ) for key,label in entry_keys),
			' (SLOW FEED!)' if time_delta.seconds > SLOWFEED_WARNING else '' ))

		feed_stats[ret_feed] += 1
		for k,v in ret_entries.iteritems(): entry_stats[k] += v

		if optz.delay: sleep(optz.delay)

	transaction.commit()

	time_delta_global = datetime.now() - time_delta_global
	log.info('* END: {0} (delta: {1}s), entries: {2}, feeds: {3}'.format(
		datetime.now(), time_delta_global,
		' '.join('{0}={1}'.format(label, entry_stats[key]) for key,label in entry_keys),
		' '.join('{0}={1}'.format(label, feed_stats[key]) for key,label in feed_keys) ))

	# Removing the cached data in all sites,
	#  this will only work with the memcached, db and file backends
	# TODO: make it work by "magic" through model signals
	from feedjack import fjcache
	for site_id in affected_sites: fjcache.cache_delsite(site_id)




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
