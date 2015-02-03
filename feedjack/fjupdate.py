# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.utils import timezone, encoding

import feedparser, feedjack
from feedjack.models import (
	transaction_wrapper, transaction, IntegrityError,
	transaction_signaled_commit, transaction_signaled_rollback )

import itertools as it, operator as op, functools as ft
from datetime import datetime, timedelta
from time import struct_time, sleep
from collections import defaultdict
from hashlib import sha256
import os, sys, types, hmac


USER_AGENT = 'Feedjack {0} - {1}'.format(feedjack.__version__, feedjack.__url__)
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


def feedparser_ts(time_tuple):
	# feedparser always returns time_tuple in UTC
	return datetime(*time_tuple[:6] + (0, timezone.utc))

def get_modified_date(parsed, raw):
	'Return best possible guess to post modification timestamp.'
	if parsed: return feedparser_ts(parsed)
	if not raw: return None

	# Parse weird timestamps that feedparser can't handle, e.g.: July 30, 2013
	ts, val = None, raw.replace('_', ' ')
	if not ts:
		# coreutils' "date" parses virtually everything, but is more expensive to use
		from subprocess import Popen, PIPE
		with open(os.devnull, 'w') as devnull:
			proc = Popen(['date', '+%s', '-d', val], stdout=PIPE, stderr=devnull)
			val = proc.stdout.read()
			if not proc.wait():
				ts = datetime.fromtimestamp(int(val.strip()), tz=timezone.utc)
	if ts: return ts
	raise ValueError('Unrecognized raw value format: {0!r}'.format(val))


_exc_feed_id = None # to be available on any print_exc call
def print_exc(feed_id=None, _exc_frame='[{0}] ! ' + '-'*25 + '\n'):
	import traceback
	if not feed_id: feed_id = _exc_feed_id
	sys.stderr.write(_exc_frame.format(feed_id))
	traceback.print_exc()
	sys.stderr.write(_exc_frame.format(feed_id))

def guid_hash(guid, nid='feedjack:guid'):
	return 'urn:{0}:{1}'.format( nid,
		hmac.new( encoding.force_bytes(nid),
			msg=encoding.force_bytes(guid), digestmod=sha256 ).hexdigest() )


class FeedProcessor(object):

	post_timestamp_keys = 'modified', 'published', 'created'

	def __init__(self, feed, options):
		self.feed, self.options = feed, options
		self.fpf = None

	def _get_guid(self, fp_entry):
		# Should probably include feed-id to be a proper *g*uid,
		#  but current unique-index is on feed+guid, so it's not necessary.
		# Changing algorithm here will make all posts on all feeds "new".
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

		# Try to get the post date from "updated" then "published" then "created"
		ts_parsed = ts_raw = None
		for k in self.post_timestamp_keys:
			try:
				post.date_modified = get_modified_date(
					entry.get('{0}_parsed'.format(k)), entry.get(k) )
			except ValueError as err:
				log.warn( 'Failed to process post timestamp:'
					' {0} (feed_id: {1}, post_guid: {2})'.format(err, self.feed.id, post.guid) )
			if post.date_modified: break

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
			log.extra( '[{0}] Saving new post: {1} (timestamp: {2})'\
				.format(self.feed.id, post.guid, post.date_modified) )

			# Try hard to set date_modified: feed.modified, http.modified and now() as a last resort
			if not post.date_modified and self.fpf:
				try:
					post.date_modified = get_modified_date(
						self.fpf.feed.get('modified_parsed') or self.fpf.get('modified_parsed'),
						self.fpf.feed.get('modified') or self.fpf.get('modified') )
				except ValueError as err:
					log.warn(( 'Failed to process feed/http timestamp: {0} (feed_id: {1},'
						' post_guid: {2}), falling back to "now"' ).format(err, self.feed.id, post.guid))
				if not post.date_modified:
					post.date_modified = timezone.now()
					log.debug(( '[{0}] Using current time for post'
						' ({1}) timestamp' ).format(self.feed.id, post.guid))
				else:
					log.debug(
						'[{0}] Using timestamp from feed/http for post ({1}): {2}'\
						.format(self.feed.id, post.guid, post.date_modified) )

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
			if ret_feed not in [FEED_OK, FEED_SAME]:
				raise FeedValidationError()
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
		report_errors = not self.options.report_after\
			or not self.feed.last_checked\
			or (self.feed.last_checked + self.options.report_after < timezone.now())

		feedparser_kws = dict()
		if sys.hexversion >= 0x2070900 and not self.feed.verify_tls_certs:
			import urllib2, ssl
			ctx = ssl.create_default_context()
			ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
			feedparser_kws['handlers'] = [urllib2.HTTPSHandler(context=ctx)]

		try:
			self.fpf = feedparser.parse( self.feed.feed_url, agent=USER_AGENT,
				etag=self.feed.etag if not self.options.force else '', **feedparser_kws )
		except KeyboardInterrupt: raise
		except:
			if report_errors:
				log.error( 'Feed cannot be parsed: {0} (#{1})'\
					.format(self.feed.feed_url, self.feed.id) )
			return FEED_ERRPARSE, ret_values

		if hasattr(self.fpf, 'status'):
			log.extra('[{0}] HTTP status {1}: {2}'.format(
				self.feed.id, self.fpf.status, self.feed.feed_url ))
			if self.fpf.status == 304:
				log.extra(( '[{0}] Feed has not changed since '
					'last check: {1}' ).format(self.feed.id, self.feed.feed_url))
				# Fast-path: just update last_checked timestamp
				self.feed.last_checked = timezone.now()
				self.feed.save()
				return FEED_SAME, ret_values

			if self.fpf.status >= 400:
				if report_errors:
					log.warn('[{0}] HTTP error {1}: {2}'.format(
						self.feed.id, self.fpf.status, self.feed.feed_url ))
				return FEED_ERRFETCH, ret_values

		if self.fpf.bozo:
			bozo = getattr(self.fpf, 'bozo_exception', 'unknown error')
			if not self.feed.skip_errors:
				if report_errors:
					log.warn( '[{0}] Failed to fetch feed: {1} ({2})'\
						.format(self.feed.id, self.feed.feed_url, bozo) )
				return FEED_ERRFETCH, ret_values
			elif report_errors:
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
	Site.signal_updated.connect(
		lambda sender, instance, **kwz: fjcache.cache_delsite(instance.id) )

	def transaction_commit():
		log.debug('Comitting db transaction')
		transaction_signaled_commit()
		for feed in affected_feeds: feed.signal_updated_dispatch(sender=FeedProcessor)
		for site in Site.objects.filter(subscriber__feed__in=affected_feeds):
			site.signal_updated_dispatch(sender=FeedProcessor)
		transaction_signaled_commit() # in case of any immediate changes from signals


	if optz.feed:
		feeds = list(Feed.objects.filter(pk__in=optz.feed)) # no is_active check
		for feed_id in set(optz.feed).difference(it.imap(op.attrgetter('id'), feeds)):
			log.warn('Unknown feed id: {0}'.format(feed_id))

	if optz.site:
		sites = list(Site.get_by_string(unicode(name)) for name in optz.site)
		feeds = Feed.objects.filter( is_active=True,
			subscriber__site__pk__in=map(op.attrgetter('id'), sites) )

	if not optz.feed and not optz.site: # fetches even unbound feeds
		feeds = Feed.objects.filter(is_active=True)


	feeds = list(feeds)
	time_delta_global = time_delta_commit = timezone.now()
	log.info( '* BEGIN: {0}, feeds to process: {1}'\
		.format(time_delta_global, len(feeds)) )

	feed_stats, entry_stats = defaultdict(int), defaultdict(int)
	for feed in feeds:
		_exc_feed_id = feed.id
		log.info('[{0}] Processing feed: {1}'.format(feed.id, feed.feed_url))

		# Check if feed has to be fetched
		if optz.adaptive_interval:
			check_optz = optz.interval_parameters.copy()
			check_clc = check_optz.pop('consider_last_check') or False
			if feed.last_checked:
				check_interval, check_interval_ts =\
					fjcache.feed_interval_get(feed.id, check_optz)
				if check_interval is None: # calculate and cache it
					check_interval = feed.calculate_check_interval(**check_optz)
					fjcache.feed_interval_set( feed.id,
						check_optz, check_interval, check_interval_ts )
				# With "consider_last_check", interval to feed.last_checked is added to average
				time_delta = timedelta( 0,
					feed.calculate_check_interval(
						ewma=check_interval, ewma_ts=check_interval_ts,
						add_partial=feed.last_checked, **check_optz )\
					if check_clc else check_interval )
				if not check_interval_ts:
					# Cache miss, legacy case or first post on the feed
					# Normally, it should be set after any feed update
					check_interval_ts = feed.last_checked
				time_delta_chk = (timezone.now() - time_delta) - check_interval_ts
				if time_delta_chk < timedelta(0):
					log.extra(
						( '[{0}] Skipping check for feed (url: {1}) due to adaptive interval setting.'
							' Minimal time until next check {2} (calculated min interval: {3}).' )\
						.format(feed.id, feed.feed_url, abs(time_delta_chk), abs(time_delta)) )
					continue
			else: check_interval, check_interval_ts = 0, None

		# Fetch new/updated stuff from the feed to db
		time_delta = timezone.now()
		if not optz.dry_run:
			ret_feed, ret_entries = FeedProcessor(feed, optz).process()
		else:
			log.debug('[{0}] Not fetching feed, because dry-run flag is set'.format(feed.id))
			ret_feed, ret_entries = FEED_SAME, dict()
		time_delta = timezone.now() - time_delta
		# FEED_SAME or errors don't invalidate cache or generate "updated" signals
		if ret_feed == FEED_OK: affected_feeds.add(feed)

		# Update check_interval ewma if feed had updates
		if optz.adaptive_interval and any(it.imap(
				ret_entries.get, [ENTRY_NEW, ENTRY_UPDATED, ENTRY_ERR] )):
			if not check_interval_ts:
				assert feed.last_checked
				check_interval_ts = feed.last_checked
			check_interval = feed.calculate_check_interval(
				ewma=check_interval, ewma_ts=check_interval_ts, **check_optz )
			fjcache.feed_interval_set(feed.id, check_optz, check_interval, check_interval_ts)

		# Feedback, stats, commit, delay
		log.info('[{0}] Processed {1} in {2}s [{3}] [{4}]{5}'.format(
			feed.id, feed.feed_url, time_delta, feed_keys_dict[ret_feed],
			' '.join('{0}={1}'.format( label,
				ret_entries.get(key, 0) ) for key,label in entry_keys),
			' (SLOW FEED!)' if time_delta.seconds > SLOWFEED_WARNING else '' ))

		feed_stats[ret_feed] += 1
		for k,v in ret_entries.iteritems(): entry_stats[k] += v

		if optz.commit_interval:
			if isinstance(optz.commit_interval, timedelta):
				ts = timezone.now()
				if ts - time_delta_commit > optz.commit_interval:
					transaction_commit()
					time_delta_commit = ts
			elif sum(feed_stats.itervalues()) % optz.commit_interval == 0: transaction_commit()

		if optz.delay:
			log.debug('Waiting for {0}s (delay option)'.format(optz.delay))
			sleep(optz.delay)

	_exc_feed_id = None

	time_delta_global = timezone.now() - time_delta_global
	log.info('* END: {0} (delta: {1}s), entries: {2}, feeds: {3}'.format(
		timezone.now(), time_delta_global,
		' '.join('{0}={1}'.format(label, entry_stats[key]) for key,label in entry_keys),
		' '.join('{0}={1}'.format(label, feed_stats[key]) for key,label in feed_keys) ))

	transaction_commit()

# Can't be specified in options because django doesn't interpret "%(default)s"
#  in option help strings, and interval_parameters can be partially overidden.
cli_defaults = dict( timeout=20, delay=0,
	interval_parameters=dict(
		ewma_factor=0.3, max_interval=0.5,
		max_days=14, max_updates=20, consider_last_check=True ) )

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
		optparse.make_option('-r', '--report-after', metavar='timespan', action='store',
			help="Report feed fetch errors only if it's unchecked for at least"
					' specified amount of time, i.e. to avoid extra noise on transient errors.'
				' Number (can be float) is interpreted as days, "s", "h" or "d" suffix can be used'
					' to explicitly indicate seconds, hours or days, respectively.'),

		optparse.make_option('-f', '--feed', action='append', type='int',
			help='A feed id to be updated. This option can be given multiple '
				'times to update several feeds at the same time (-f 1 -f 4 -f7).'),
		optparse.make_option('-s', '--site', action='append',
			help='A site id or name/title part to update. Can be specified multiple times.'),

		optparse.make_option('-a', '--adaptive-interval', action='store_true',
			help=( 'Skip fetching feeds, depending on adaptive'
					' per-feed update interval, depending on average update intervals.'
				' This means that rarely-updated feeds will be skipped,'
					' if time since last check is greater than average (ewma) interval between'
					' feed updates for some period (default: '
						'{0[max_days]} day(s) or {0[max_updates]} last updates),'
					' but lesser than defined maximum (default: {0[max_interval]}d).'
				' consider_last_check flag (default: {0[consider_last_check]}), if set,'
					' also adds interval between last seen post and last feed check to'
					' calculation, but only if its larger than average interval between posts'
					' (i.e. make checks less frequent with each subsequent "nothing new" result).' )\
				.format(cli_defaults['interval_parameters'])),
		optparse.make_option('-i', '--interval-parameters',
			metavar='k1=v1:k2=v2:...', default=cli_defaults['interval_parameters'],
			help=( 'Parameters for calculating per-feed update interval.'
					' Specified as "key=value" pairs, separated by colons.'
					' Accepted keys: {0}.'
					' Accepted values: bool ("true" or "false"), integers (days), floats (days);'
						' for timespan values "0" or "none" meaning "no limit",'
						' adding "h" suffix will interpret number before it as hours (instead of days),'
						' "s" suffix for seconds.'
					' Defaults: {1}' )\
				.format( ', '.join(cli_defaults['interval_parameters']),
					':'.join(it.starmap('{0}={1}'.format, cli_defaults['interval_parameters'].iteritems())) )),

		optparse.make_option('-t', '--timeout',
			metavar='seconds', type='int', default=cli_defaults['timeout'],
			help='Socket timeout (in seconds)'
				' for connections (default: {0}).'.format(cli_defaults['timeout'])),
		optparse.make_option('-d', '--delay',
			metavar='seconds', type='int', default=cli_defaults['delay'],
			help='Delay (in seconds) between'
				' fetching the feeds (default: {0}).'.format(cli_defaults['delay'])),
		optparse.make_option('-c', '--commit-interval',
			metavar='feed_count/<seconds>s',
			help='Interval between intermediate database transaction commits.'
				' Can be specified as feed_count (example: 5) to commit after each N processed feeds,'
					' or as a time interval in seconds (example: 600s).'
				' Default behavior is to make db commit only after all requested feeds/sites'
					' were processed (with savepoints after each individual feed,'
					' to rollback feed processing errors).'
				' Should only be useful for sufficiently large processing'
					' jobs, large --delay values or very slow feeds.'),

		optparse.make_option('-q', '--quiet', action='store_true',
			help='Report only severe errors, no info or warnings.'),
		optparse.make_option('--dry-run', action='store_true',
			help='Dont do the actual fetching, reporting feeds as unchanged.'),
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

	# Process --interval-parameters, --commit-interval
	try:
		if isinstance(optz.interval_parameters, types.StringTypes):
			params = cli_defaults['interval_parameters'].copy()
			for v in optz.interval_parameters.split(':'):
				k, vs = v.split('=')
				if k not in params:
					raise CommandError('Unrecognized interval parameter: {0}'.format(k))
				if vs.lower() == 'true': v = True
				elif vs.lower() == 'false': v = False
				elif vs.lower() == 'none': v = 0
				else:
					try: v = float(vs.rstrip('sdh'))
					except ValueError:
						raise CommandError('Unrecognized interval parameter value: {0}'.format(vs))
				if vs.endswith('h'): v /= float(24)
				elif vs.endswith('s'): v /= float(3600 * 24)
				params[k] = v
			optz.interval_parameters = params
		if optz.commit_interval:
			if optz.commit_interval.isdigit():
				optz.commit_interval = int(optz.commit_interval)
			elif optz.commit_interval.endswith('s'):
				optz.commit_interval = timedelta(0, int(optz.commit_interval[:-1]))
			else:
				raise CommandError( 'Invalid'
					' interval value: {0}'.format(optz.commit_interval) )
		if optz.report_after:
			try: v = float(optz.report_after.rstrip('sdh'))
			except ValueError:
				raise CommandError('Unrecognized timespan value: {0}'.format(optz.report_after))
			if optz.report_after.endswith('h'): v /= float(24)
			elif optz.report_after.endswith('s'): v /= float(3600 * 24)
			optz.report_after = timedelta(v)
	except CommandError as err:
		if not parser: raise
		parser.error(*err.args)

	# Make sure logging won't choke on encoding
	import codecs
	codec = codecs.getwriter('utf-8')
	sys.stdout = codec(sys.stdout)
	sys.stderr = codec(sys.stderr)

	bulk_update(optz)

if __name__ == '__main__': main()
