# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils import timezone

import feedparser, feedjack
from feedjack.models import transaction_wrapper, transaction, IntegrityError,\
	transaction_signaled_commit, transaction_signaled_rollback

import itertools as it, operator as op, functools as ft
from datetime import datetime, timedelta
from time import struct_time, sleep
from collections import defaultdict
from hashlib import sha256
import os, sys, types, hmac


USER_AGENT = 'Feedjack {} - {}'.format(feedjack.__version__, feedjack.__url__)
SLOWFEED_WARNING = 10

import logging
logging.EXTRA = (logging.DEBUG + logging.INFO) // 2
logging.addLevelName(logging.EXTRA, 'EXTRA')
log = logging.getLogger(os.path.basename(__file__))
log.extra = ft.partial(log.log, logging.EXTRA) # should only be used here


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


feedparser_ts = lambda ts: datetime(*ts[:6] + (0, timezone.utc))

_exc_feed_id = None # to be available on any print_exc call
def print_exc(feed_id=None, _exc_frame='[{0}] ! ' + '-'*25 + '\n'):
	import traceback
	if not feed_id: feed_id = _exc_feed_id
	sys.stderr.write(_exc_frame.format(feed_id))
	traceback.print_exc()
	sys.stderr.write(_exc_frame.format(feed_id))

def guid_hash(guid, nid='feedjack:guid'):
	return 'urn:{}:{}'.format( nid,
		hmac.new(nid, msg=guid, digestmod=sha256).hexdigest() )


class FeedProcessor(object):

	def __init__(self, feed, options):
		self.feed, self.options = feed, options
		self.fpf = None

	def _get_guid(self, fp_entry, nid='feedjack:guid'):
		guid = fp_entry.get('id', '') or fp_entry.get('title', '') or fp_entry.get('link', '')
		# Hashing fallback is necessary due to mysql field length limitations
		return guid if len(guid) <= 255 else guid_hash(guid)

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

		post.date_modified = entry.get('modified_parsed')
		if post.date_modified: post.date_modified = feedparser_ts(post.date_modified)
		elif entry.get('modified'):
			log.warn(
				'Failed to parse post timestamp: {!r} (feed_id: {}, post_guid: {})'\
				.format(entry.modified, self.feed.id, post.guid) )

		post.comments = entry.get('comments', '')
		post.enclosures = entry.get('enclosures')

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
					tagname = ' '.join(zcat.lower().split()).strip()[:255]
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
				ts = self.fpf.feed.get('modified_parsed') or self.fpf.get('modified_parsed')
				if ts: post.date_modified = feedparser_ts(ts)
				else:
					ts = self.fpf.feed.get('modified') or self.fpf.get('modified')
					if ts:
						log.warn( 'Failed to parse feed/http'
							' timestamp: {!r} (feed_id: {})'.format(ts, self.feed.id) )
			if not post.date_modified: post.date_modified = timezone.now()
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

		self.feed.title = self.fpf.feed.get('title', '')[:200]
		self.feed.tagline = self.fpf.feed.get('tagline', '')
		self.feed.link = self.fpf.feed.get('link', '')
		self.feed.last_checked = timezone.now()

		log.debug('[{0}] Feed info for: {1}\n{2}'.format(
			self.feed.id, self.feed.feed_url, '\n'.join(
			'  {0}: {1}'.format(key, getattr(self.feed, key))
			for key in ['title', 'tagline', 'link', 'last_checked'] )))

		guids = filter(None, it.imap(self._get_guid, self.fpf.entries))
		if guids:
			from feedjack.models import Post
			self.postdict = dict( (post.guid, post)
				for post in Post.objects.filter(
					feed=self.feed.id, guid__in=guids ) )
			if self.options.max_diff:
				# Do not calculate diff for empty (probably just-added) feeds
				if not self.postdict and Post.objects.filter(feed=self.feed.id).count() == 0: diff = 0
				else: diff = op.truediv(len(guids) - len(self.postdict), len(guids)) * 100
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
			try: self.feed.last_modified = feedparser_ts(self.fpf.modified_parsed)
			except AttributeError: pass
			self.feed.save()

		return FEED_OK if ret_values[ENTRY_NEW]\
			or ret_values[ENTRY_UPDATED] else FEED_SAME, ret_values



@transaction_wrapper(logging, print_exc=print_exc)
def bulk_update(optz):
	global _exc_feed_id # updated to be available on uncaught errors

	from feedjack.models import Feed, Site
	from feedjack import fjcache

	import socket
	socket.setdefaulttimeout(optz.timeout)

	affected_feeds = set() # for post-transaction signals

	if optz.feed:
		feeds = list(Feed.objects.filter(pk__in=optz.feed)) # no is_active check
		for feed_id in set(optz.feed).difference(it.imap(op.attrgetter('id'), feeds)):
			log.warn('Unknown feed id: {0}'.format(feed_id))

	if optz.site:
		feeds = Feed.objects.filter( is_active=True,
			subscriber__site__pk__in=optz.site )
		sites = Site.objects.filter(pk__in=optz.site)
		for site_id in set(optz.site).difference(sites.values_list('id', flat=True)):
			log.warn('Unknown site id: {0}'.format(site_id))

	if not optz.feed and not optz.site: # fetches even unbound feeds
		feeds = Feed.objects.filter(is_active=True)


	feeds, time_delta_global = list(feeds), timezone.now()
	log.info( '* BEGIN: {0}, feeds to process: {1}'\
		.format(time_delta_global, len(feeds)) )

	feed_stats, entry_stats = defaultdict(int), defaultdict(int)
	for feed in feeds:
		_exc_feed_id = feed.id
		log.info('[{}] Processing feed: {}'.format(feed.id, feed.feed_url))

		# Check if feed has to be fetched
		if optz.adaptive_interval:
			if feed.last_checked:
				check_interval = fjcache.feed_interval_get(feed.id, optz.interval_parameters)
				if check_interval is None: # calculate and cache it
					check_interval = feed.calculate_check_interval(**optz.interval_parameters)
					fjcache.feed_interval_set(feed.id, optz.interval_parameters, check_interval)
				check_interval_ts = feed.last_checked
				time_delta = timedelta(0, check_interval)
				time_delta_chk = (timezone.now() - time_delta) - check_interval_ts
				if time_delta_chk < timedelta(0):
					log.extra(
						( '[{}] Skipping check for feed (url: {}) due to adaptive interval setting.'
							' Minimal time until next check {} (calculated min interval: {}).' )\
						.format(feed.id, feed.feed_url, abs(time_delta_chk), abs(time_delta)) )
					continue
			else: check_interval, check_interval_ts = 0, None

		# Fetch new/updated stuff from the feed to db
		time_delta = timezone.now()
		ret_feed, ret_entries = FeedProcessor(feed, optz).process()
		time_delta = timezone.now() - time_delta
		# FEED_SAME or errors don't invalidate cache or generate "updated" signals
		if ret_feed == FEED_OK: affected_feeds.add(feed)

		# Update check_interval ewma if feed had updates
		if optz.adaptive_interval and any(it.imap(
				ret_entries.get, [ENTRY_NEW, ENTRY_UPDATED, ENTRY_ERR] )):
			check_interval = feed.calculate_check_interval(
				ewma=check_interval, ewma_ts=check_interval_ts, **optz.interval_parameters )
			fjcache.feed_interval_set(feed.id, optz.interval_parameters, check_interval)

		# Feedback, stats, delay
		log.info('[{0}] Processed {1} in {2}s [{3}] [{4}]{5}'.format(
			feed.id, feed.feed_url, time_delta, feed_keys_dict[ret_feed],
			' '.join('{0}={1}'.format( label,
				ret_entries.get(key, 0) ) for key,label in entry_keys),
			' (SLOW FEED!)' if time_delta.seconds > SLOWFEED_WARNING else '' ))

		feed_stats[ret_feed] += 1
		for k,v in ret_entries.iteritems(): entry_stats[k] += v

		if optz.delay: sleep(optz.delay)

	_exc_feed_id = None

	time_delta_global = timezone.now() - time_delta_global
	log.info('* END: {0} (delta: {1}s), entries: {2}, feeds: {3}'.format(
		timezone.now(), time_delta_global,
		' '.join('{0}={1}'.format(label, entry_stats[key]) for key,label in entry_keys),
		' '.join('{0}={1}'.format(label, feed_stats[key]) for key,label in feed_keys) ))

	transaction_signaled_commit()

	# Removing the cached data in all sites,
	#  this will only work with the memcached, db and file backends
	Site.signal_updated.connect(lambda sender, instance, **kwz: fjcache.cache_delsite(instance.id))
	for feed in affected_feeds: feed.signal_updated_dispatch(sender=FeedProcessor)
	for site in Site.objects.filter(subscriber__feed__in=affected_feeds):
		site.signal_updated_dispatch(sender=FeedProcessor)

	transaction_signaled_commit() # in case of any immediate changes from signals


# Can't be specified in options because django doesn't interpret "%(default)s"
#  in option help strings, and interval_parameters can be partially overidden.
cli_defaults = dict( timeout=20, delay=0,
	interval_parameters=dict(
		ewma_factor=0.3, max_interval=0.5,
		max_days=14, max_updates=20 ) )

def make_cli_option_list():
	import optparse
	return [
		optparse.make_option('--force', action='store_true',
			help='Do not use stored modification time or etag when fetching feed updates.'),
		optparse.make_option('--hidden', action='store_true',
			help='Mark all fetched (new) posts as "hidden". Intended'
				' usage is initial fetching of large (number of) feeds.'),

		optparse.make_option('--max-feed-difference', action='store', dest='max_diff', type='int',
			help='Maximum percent of new posts to consider feed valid.'
				' Intended for broken feeds, which sometimes return seemingly-random content.'),

		optparse.make_option('-f', '--feed', action='append', type='int',
			help='A feed id to be updated. This option can be given multiple '
				'times to update several feeds at the same time (-f 1 -f 4 -f 7).'),
		optparse.make_option('-s', '--site', action='append', type='int',
			help='A site id (or several of them) to update.'),

		optparse.make_option('-a', '--adaptive-interval', action='store_true',
			help=( 'Skip fetching feeds, depending on adaptive'
					' per-feed update interval, depending on average update intervals.'
				' This means that rarely-updated feeds will be skipped,'
					' if time since last check is greater than average (ewma) interval between'
					' feed updates for some period (default: '
						'{0[max_days]} day(s) or {0[max_updates]} last updates),'
					' but lesser than defined maximum (default: {0[max_interval]}d).' )\
				.format(cli_defaults['interval_parameters'])),
		optparse.make_option('-i', '--interval-parameters',
			metavar='k1=v1:k2=v2:...', default=cli_defaults['interval_parameters'],
			help=( 'Parameters for calculating per-feed update interval.'
					' Specified as "key=value" pairs, separated by colons.'
					' Accepted keys: {}.'
					' Accepted values: integers (days), floats (days),'
						' "0" or "none" meaning "no limit", adding "h" suffix means'
						' that value will be interpreted as hours (instead of days),'
						' "s" suffix for seconds.'
					' Defaults: {}' )\
				.format( ', '.join(cli_defaults['interval_parameters']),
					':'.join(it.starmap('{}={}'.format, cli_defaults['interval_parameters'].viewitems())) )),

		optparse.make_option('-t', '--timeout',
			metavar='seconds', type='int', default=cli_defaults['timeout'],
			help='Socket timeout (in seconds)'
				' for connections (default: {}).'.format(cli_defaults['timeout'])),
		optparse.make_option('-d', '--delay',
			metavar='seconds', type='int', default=cli_defaults['delay'],
			help='Delay (in seconds) between'
				' fetching the feeds (default: {}).'.format(cli_defaults['delay'])),

		optparse.make_option('-q', '--quiet', action='store_true',
			help='Report only severe errors, no info or warnings.'),
		optparse.make_option('--verbose', action='store_true', help='Verbose output.'),
		optparse.make_option('--debug', action='store_true', help='Even more verbose output.') ]


def main(optz=None):
	from django.core.management.base import CommandError
	import optparse

	if optz is None:
		parser = optparse.OptionParser(
			usage='%prog [options]', version=USER_AGENT,
			option_list=make_cli_option_list() )
		optz, argz = parser.parse_args()
		if argz: parser.error('This command takes no arguments')

	else:
		parser = None # to check and re-raise django CommandError
		if not isinstance(optz, optparse.Values):
			optz, optz_dict = optparse.Values(), optz
			optz._update(optz_dict, 'loose')

	# Set console logging level
	verbosity = int(vars(optz).get('verbosity', 1)) # from django-admin
	if optz.debug or verbosity >= 3: logging.basicConfig(level=logging.DEBUG)
	elif optz.verbose or verbosity >= 2: logging.basicConfig(level=logging.EXTRA)
	elif optz.quiet or verbosity < 1: logging.basicConfig(level=logging.WARNING)
	else: logging.basicConfig(level=logging.INFO)

	# Process --interval-parameters
	try:
		if isinstance(optz.interval_parameters, types.StringTypes):
			params = cli_defaults['interval_parameters'].copy()
			for v in optz.interval_parameters.split(':'):
				k, vs = v.split('=')
				if k not in params:
					raise CommandError('Unrecognized interval parameter: {}'.format(k))
				if vs in ['none', 'None']: v = 0
				else:
					try: v = float(vs.rstrip('sdh'))
					except ValueError:
						raise CommandError('Unrecognized interval parameter value: {}'.format(vs))
				if vs.endswith('h'): v = v / float(24)
				elif vs.endswith('s'): v = v / float(3600 * 24)
				params[k] = v
			optz.interval_parameters = params
	except CommandError as err:
		if not parser: raise
		parser.error(*err.args)

	# Make sure logging won't choke on encoding
	import codecs
	codec = codecs.getwriter('utf-8')
	sys.stdout = codec(sys.stdout)
	sys.stderr = codec(sys.stderr)

	bulk_update(optz)

if __name__ == '__main__':
	main()
