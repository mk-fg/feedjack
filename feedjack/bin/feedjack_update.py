#!/usr/bin/env python
# -*- coding: utf-8 -*-


VERSION = '0.9.16-fg2'
URL = 'http://www.feedjack.org/'
USER_AGENT = 'Feedjack {0} - {1}'.format(VERSION, URL)
SLOWFEED_WARNING = 10
ENTRY_NEW, ENTRY_UPDATED, ENTRY_SAME, ENTRY_ERR = xrange(4)
FEED_OK, FEED_SAME, FEED_ERRPARSE, FEED_ERRHTTP, FEED_ERREXC = xrange(5)


import itertools as it, operator as op, functools as ft
from datetime import datetime
from time import sleep
import os, sys

import feedparser
from feedjack.fjlib import transaction_wrapper, transaction

try: import threadpool
except ImportError: threadpool = None

import codecs
codec = codecs.getwriter('utf-8')
sys.stdout = codec(sys.stdout)
sys.stderr = codec(sys.stderr)

import logging, functools as ft
logging.EXTRA = (logging.DEBUG + logging.INFO) // 2
log = logging.getLogger(os.path.basename(__file__))
log.extra = ft.partial(log.log, logging.EXTRA)
# TODO: special formatter to insert feed_id to the prefix


mtime = lambda ttime: datetime(*ttime[:6])

_exc_frame = '[{0}] ! ' + '-'*25
def print_exc():
	print _exc_frame.format(self.feed.id)
	traceback.print_exc()
	print _exc_frame.format(self.feed.id)



class ProcessFeed:

	def __init__(self, feed, options):
		self.feed = feed
		self.options = options
		self.fpf = None


	def process_entry(self, entry):
		'Construct a Post from a feedparser entry and save/update it in db'

		from feedjack.models import Post, Tag

		## Construct a Post object from feedparser entry (FeedParserDict)
		post = Post(feed=self.feed)
		post.link = entry.get('link', self.feed.link)
		post.title = entry.get('title', post.link)
		post.guid = entry.get('id', post.title)

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
				qcat = (tcat.label if tcat.label is not None else tcat.term).strip()
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

		log.debug(u'[{0}] Entry\n{1}'.format(self.feed.id, u'\n'.join(
			[u'  {0}: {1}'.format(key, getattr(post, key)) for key in post_base_fields]
			+ [u'tags: {0}'.format(u' '.join(it.imap(op.attrgetter('name'), fcat)))] )))

		## Store / update a post
		if post.guid in self.postdict: # post exists, update if it was modified (and feed is mutable)
			post_old = self.postdict[post.guid]
			changed = post_old.content != post.content or (
				post.date_modified and post_old.date_modified != post.date_modified )

			if not self.feed.immutable and changed:
				retval = ENTRY_UPDATED
				log.extra(u'[{0}] Updating existing post: {1}'.format(self.feed.id, post.link))
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
				log.extra( ( u'[{0}] Post has not changed: {1}' if not changed else
					u'[{0}] Post changed, but feed is marked as immutable: {1}' )\
						.format(self.feed.id, post.link) )

		else: # new post, store it into database
			retval = ENTRY_NEW
			log.extra(u'[{0}] Saving new post: {1}'.format(self.feed.id, post.link))
			# Try hard to set date_modified: feed.modified, http.modified and now() as a last resort
			if not post.date_modified and self.fpf:
				if self.fpf.feed.get('modified_parsed'):
					post.date_modified = mtime(self.fpf.feed.modified_parsed)
				elif self.fpf.get('modified'): post.date_modified = mtime(self.fpf.modified)
			if not post.date_modified: post.date_modified = datetime.now()
			post.save()
			for tcat in fcat: post.tags.add(tcat)
			self.postdict[post.guid] = post

		return retval


	def process(self):
		'Downloads and parses a feed.'

		ret_values = {
			ENTRY_NEW:0,
			ENTRY_UPDATED:0,
			ENTRY_SAME:0,
			ENTRY_ERR:0}

		log.info(u'[{0}] Processing feed {1}'.format(self.feed.id, self.feed.feed_url))

		# we check the etag and the modified time to save bandwith and
		# avoid bans
		try:
			self.fpf = feedparser.parse(
				self.feed.feed_url, agent=USER_AGENT, etag=self.feed.etag )
		except:
			log.error( u'Feed cannot be parsed: {0} (#{1})'\
				.format(self.feed.feed_url, self.feed.id) )
			return FEED_ERRPARSE, ret_values

		if hasattr(self.fpf, 'status'):
			log.extra(u'[{0}] HTTP status {1}: {2}'.format(
				self.feed.id, self.fpf.status, self.feed.feed_url ))
			if self.fpf.status == 304:
				# this means the feed has not changed
				log.extra(( u'[{0}] Feed has not changed since '
					'last check: {1}' ).format(self.feed.id, self.feed.feed_url))
				return FEED_SAME, ret_values

			if self.fpf.status >= 400:
				# http error, ignore
				log.warn(u'[{0}] HTTP_ERROR {1}: {2}'.format(
					self.feed.id, self.fpf.status, self.feed.feed_url ))
				return FEED_ERRHTTP, ret_values

		if hasattr(self.fpf, 'bozo') and self.fpf.bozo:
			log.error( u'[{0}] BOZO! Feed is not well formed: {1}'\
				.format(self.feed.id, self.feed.feed_url) )

		# the feed has changed (or it is the first time we parse it)
		# saving the etag and last_modified fields
		self.feed.etag = self.fpf.get('etag', '')
		# some times this is None (it never should) *sigh*
		if self.feed.etag is None: self.feed.etag = ''

		try: self.feed.last_modified = mtime(self.fpf.modified)
		except: pass

		self.feed.title = self.fpf.feed.get('title', '')[0:254]
		self.feed.tagline = self.fpf.feed.get('tagline', '')
		self.feed.link = self.fpf.feed.get('link', '')
		self.feed.last_checked = datetime.now()

		log.debug(u'[{0}] Feed info for: {1}\n{2}'.format(
			self.feed.id, self.feed.feed_url, u'\n'.join(
			u'  {0}: {1}'.format(key, getattr(self.feed, key))
			for key in ['title', 'tagline', 'link', 'last_checked'] )))

		guids = list()
		for entry in self.fpf.entries:
			if entry.get('id', ''): guids.append(entry.get('id', ''))
			elif entry.title: guids.append(entry.title)
			elif entry.link: guids.append(entry.link)

		self.feed.save() # rollback here should be handled on a higher level

		if guids:
			from feedjack.models import Post
			self.postdict = dict( (post.guid, post)
				for post in Post.objects.filter(
					feed=self.feed.id ).filter(guid__in=guids) )
		else: self.postdict = dict()

		for entry in self.fpf.entries:
			tsp = transaction.savepoint()
			try: ret_entry = self.process_entry(entry)
			except:
				print_exc()
				ret_entry = ENTRY_ERR
				transaction.savepoint_rollback(tsp)
			else:
				transaction.savepoint_commit(tsp)
			ret_values[ret_entry] += 1

		return FEED_OK, ret_values



class Dispatcher:

	def __init__(self, options, num_threads):
		self.options = options
		self.entry_stats = {
			ENTRY_NEW:0,
			ENTRY_UPDATED:0,
			ENTRY_SAME:0,
			ENTRY_ERR:0}
		self.feed_stats = {
			FEED_OK:0,
			FEED_SAME:0,
			FEED_ERRPARSE:0,
			FEED_ERRHTTP:0,
			FEED_ERREXC:0}
		self.entry_trans = {
			ENTRY_NEW:'new',
			ENTRY_UPDATED:'updated',
			ENTRY_SAME:'same',
			ENTRY_ERR:'error'}
		self.feed_trans = {
			FEED_OK:'ok',
			FEED_SAME:'unchanged',
			FEED_ERRPARSE:'cant_parse',
			FEED_ERRHTTP:'http_error',
			FEED_ERREXC:'exception'}
		self.entry_keys = sorted(self.entry_trans.keys())
		self.feed_keys = sorted(self.feed_trans.keys())

		if threadpool: self.tpool = threadpool.ThreadPool(num_threads)
		else: self.tpool = None

		self.time_start = datetime.now()


	def add_job(self, feed):
		""" adds a feed processing job to the pool
		"""
		if self.tpool:
			req = threadpool.WorkRequest(self.process_feed_wrapper, (feed,))
			self.tpool.putRequest(req)
		else:
			# no threadpool module, just run the job
			self.process_feed_wrapper(feed)


	def process_feed_wrapper(self, feed):
		start_time = datetime.now()

		tsp = transaction.savepoint()
		try:
			# TODO: get rid of this pseudo-oop as well
			pfeed = ProcessFeed(feed, self.options)
			ret_feed, ret_entries = pfeed.process()
			del pfeed
		except:
			print_exc()
			ret_feed = FEED_ERREXC
			ret_entries = dict()
			transaction.savepoint_rollback(tsp)
		else:
			transaction.savepoint_commit(tsp)

		delta = datetime.now() - start_time
		log.info(u'[{0}] Processed {1} in {2} [{3}] [{4}]{5}'.format(
			feed.id, feed.feed_url, unicode(delta), self.feed_trans[ret_feed],
			u' '.join(u'{0}={1}'.format( self.entry_trans[key],
				ret_entries[key] ) for key in self.entry_keys),
			u' (SLOW FEED!)' if delta.seconds > SLOWFEED_WARNING else u'' ))

		self.feed_stats[ret_feed] += 1
		for key, val in ret_entries.items(): self.entry_stats[key] += val

		return ret_feed, ret_entries


	def poll(self):
		""" polls the active threads
		"""
		if not self.tpool:
			# no thread pool, nothing to poll
			return
		while True:
			try:
				# TODO: py sleep/poll loop is obviously wrong, there should be blocking alternative
				#  like select or join, otherwise what's the point of this "threadpool" module?
				# TODO: are django transactions threadsafe, anyway? I strongly suspect they are not
				sleep(0.2)
				self.tpool.poll()
			except KeyboardInterrupt:
				log.error(u'Cancelled by user')
				break
			except threadpool.NoResultsPending:
				log.info(u'* DONE in {0}\n* Feeds: {1}\n* Entries: {2}'.format(
					unicode(datetime.now() - self.time_start),
					u' '.join(u'{0}={1}'.format( self.feed_trans[key],
						self.feed_stats[key] ) for key in self.feed_keys),
					u' '.join(u'{0}={1}'.format( self.entry_trans[key],
							self.entry_stats[key] ) for key in self.entry_keys) ))
				break



@transaction_wrapper(logging)
def main(optz):
	import socket
	socket.setdefaulttimeout(optz.timeout)

	disp = Dispatcher(optz, optz.workerthreads)
	log.info(u'* BEGIN: {0}'.format(unicode(datetime.now())))

	from feedjack.models import Feed, Site

	if optz.feed:
		feeds = Feed.objects.filter(id__in=optz.feed)
		known_ids = set()
		for feed in feeds:
			known_ids.add(feed.id)
			disp.add_job(feed)
		for feed in optz.feed:
			if feed not in known_ids: log.warn(u'Unknown feed id: {0}'.format(feed))
	elif optz.site:
		try: site = Site.objects.get(pk=int(optz.site))
		except Site.DoesNotExist:
			site = None
			log.warn(u'Unknown site id: {0}'.format(optz.site))
		if site:
			feeds = [sub.feed for sub in site.subscriber_set.all()]
			for feed in feeds: disp.add_job(feed)
	else:
		for feed in Feed.objects.filter(is_active=True): disp.add_job(feed)

	disp.poll()
	transaction.commit()

	log.info(u'* END: {0} ({1})'.format( unicode(datetime.now()),
		u'{0} threads'.format(optz.workerthreads) if threadpool
			else u'no threadpool module available, no parallel fetching' ))

	# Removing the cached data in all sites,
	#  this will only work with the memcached, db and file backends
	# TODO: make it work by "magic" through model signals
	from feedjack import fjcache
	for site in Site.objects.all(): fjcache.cache_delsite(site.id)




if __name__ == '__main__':
	import optparse
	parser = optparse.OptionParser(usage='%prog [options]', version=USER_AGENT)

	parser.add_option('-f', '--feed', action='append', type='int',
		help='A feed id to be updated. This option can be given multiple '
			'times to update several feeds at the same time (-f 1 -f 4 -f 7).')
	parser.add_option('-s', '--site', type='int', help='A site id to update.')

	parser.add_option('-t', '--timeout', type='int', default=10,
		help='Wait timeout in seconds when connecting to feeds.')
	parser.add_option('-w', '--workerthreads', type='int', default=10,
		help='Worker threads that will fetch feeds in parallel.')

	parser.add_option('-q', '--quiet', action='store_true',
		dest='quiet', help='Report only severe errors, no info or warnings.')
	parser.add_option('-v', '--verbose', action='store_true',
		dest='verbose', help='Verbose output.')
	parser.add_option('--debug', action='store_true',
		dest='debug', help='Even more verbose output.')

	optz,argz = parser.parse_args()
	if argz: parser.error('This command takes no arguments')

	if optz.debug: logging.basicConfig(level=logging.DEBUG)
	elif optz.verbose: logging.basicConfig(level=logging.EXTRA)
	elif optz.quiet: logging.basicConfig(level=logging.WARNING)
	else: logging.basicConfig(level=logging.INFO)

	main(optz)
