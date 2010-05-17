#!/usr/bin/env python
# -*- coding: utf-8 -*-


VERSION = '0.9.16'
URL = 'http://www.feedjack.org/'
USER_AGENT = 'Feedjack {0} - {1}'.format(VERSION, URL)
SLOWFEED_WARNING = 10
ENTRY_NEW, ENTRY_UPDATED, ENTRY_SAME, ENTRY_ERR = xrange(4)
FEED_OK, FEED_SAME, FEED_ERRPARSE, FEED_ERRHTTP, FEED_ERREXC = xrange(5)


import os, sys, traceback
import time, datetime
import socket

import feedparser

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

def mtime(ttime):
	""" datetime auxiliar function.
	"""
	return datetime.datetime.fromtimestamp(time.mktime(ttime))

class ProcessEntry:
	def __init__(self, feed, options, entry, postdict, fpf):
		self.feed = feed
		self.options = options
		self.entry = entry
		self.postdict = postdict
		self.fpf = fpf

	def get_tags(self):
		""" Returns a list of tag objects from an entry.
		"""
		from feedjack import models

		fcat = []
		if self.entry.has_key('tags'):
			for tcat in self.entry.tags:
				if tcat.label != None:
					term = tcat.label
				else:
					term = tcat.term
				qcat = term.strip()
				if ',' in qcat or '/' in qcat:
					qcat = qcat.replace(',', '/').split('/')
				else:
					qcat = [qcat]
				for zcat in qcat:
					tagname = zcat.lower()
					while '  ' in tagname:
						tagname = tagname.replace('  ', ' ')
					tagname = tagname.strip()
					if not tagname or tagname == ' ':
						continue
					if not models.Tag.objects.filter(name=tagname):
						cobj = models.Tag(name=tagname)
						cobj.save()
					fcat.append(models.Tag.objects.get(name=tagname))
		return fcat

	def get_entry_data(self):
		""" Retrieves data from a post and returns it in a tuple.
		"""
		try:
			link = self.entry.link
		except AttributeError:
			link = self.feed.link
		try:
			title = self.entry.title
		except AttributeError:
			title = link
		guid = self.entry.get('id', title)

		if self.entry.has_key('author_detail'):
			author = self.entry.author_detail.get('name', '')
			author_email = self.entry.author_detail.get('email', '')
		else:
			author, author_email = '', ''

		if not author:
			author = self.entry.get('author', self.entry.get('creator', ''))
		if not author_email:
			# this should be optional~
			author_email = 'nospam@nospam.com'

		try:
			content = self.entry.content[0].value
		except:
			content = self.entry.get('summary',
									 self.entry.get('description', ''))

		if self.entry.has_key('modified_parsed'):
			date_modified = mtime(self.entry.modified_parsed)
		else:
			date_modified = None

		fcat = self.get_tags()
		comments = self.entry.get('comments', '')

		return (link, title, guid, author, author_email, content,
				date_modified, fcat, comments)

	def process(self):
		""" Process a post in a feed and saves it in the DB if necessary.
		"""
		from feedjack import models

		(link, title, guid, author, author_email, content, date_modified,
			fcat, comments) = self.get_entry_data() # TODO: refactory as an entry-object or namedtuple

		tags = u' '.join(it.imap(op.attrgetter('name'), fcat))
		log.debug(u'[{0}] Entry\n{1}'.format(self.feed.id, u'\n'.join(
			u'  {0}: {1}'.format(key, locals[key]) for key in
			['title', 'link', 'guid', 'author', 'author_email', 'tags'] )))

		if guid in self.postdict:
			tobj = self.postdict[guid]
			if tobj.content != content\
					or (date_modified and tobj.date_modified != date_modified):
				retval = ENTRY_UPDATED
				log.extra('[{0}] Updating existing post: {1}'.format(self.feed.id, link))
				if not date_modified:
					# damn non-standard feeds
					date_modified = tobj.date_modified
				tobj.title = title
				tobj.link = link
				tobj.content = content
				tobj.guid = guid
				tobj.date_modified = date_modified
				tobj.author = author
				tobj.author_email = author_email
				tobj.comments = comments
				tobj.tags.clear()
				[tobj.tags.add(tcat) for tcat in fcat]
				tobj.save()
			else:
				retval = ENTRY_SAME
				log.extra('[{0}] Post has not changed: {1}'.format(self.feed.id, link))
		else:
			retval = ENTRY_NEW
			log.extra('[{0}] Saving new post: {1}'.format(self.feed.id, link))
			if not date_modified and self.fpf:
				# if the feed has no date_modified info, we use the feed
				# mtime or the current time
				if self.fpf.feed.has_key('modified_parsed'):
					date_modified = mtime(self.fpf.feed.modified_parsed)
				elif self.fpf.has_key('modified'):
					date_modified = mtime(self.fpf.modified)
			if not date_modified:
				date_modified = datetime.datetime.now()
			tobj = models.Post(feed=self.feed, title=title, link=link,
				content=content, guid=guid, date_modified=date_modified,
				author=author, author_email=author_email,
				comments=comments)
			tobj.save()
			[tobj.tags.add(tcat) for tcat in fcat]
		return retval


class ProcessFeed:
	def __init__(self, feed, options):
		self.feed = feed
		self.options = options
		self.fpf = None

	def process_entry(self, entry, postdict):
		""" wrapper for ProcessEntry
		"""
		entry = ProcessEntry(self.feed, self.options, entry, postdict,
							 self.fpf)
		ret_entry = entry.process()
		del entry
		return ret_entry

	def process(self):
		""" Downloads and parses a feed.
		"""
		from feedjack import models

		ret_values = {
			ENTRY_NEW:0,
			ENTRY_UPDATED:0,
			ENTRY_SAME:0,
			ENTRY_ERR:0}

		log.info(u'[{0}] Processing feed {1}'.format(self.feed.id, self.feed.feed_url))

		# we check the etag and the modified time to save bandwith and
		# avoid bans
		try:
			self.fpf = feedparser.parse(self.feed.feed_url,
										agent=USER_AGENT,
										etag=self.feed.etag)
		except:
			log.error( u'Feed cannot be parsed: {0} (#{1})'\
				.format(self.feed.feed_url, self.feed.id) )
			return FEED_ERRPARSE, ret_values

		if hasattr(self.fpf, 'status'):
			log.extra(u'[{0}] HTTP status {1}: {2}'.format(
				self.feed.id, self.fpf.status, self.feed.feed_url ))
			if self.fpf.status == 304:
				# this means the feed has not changed
				log.extra(( '[{0}] Feed has not changed since '
					'last check: {1}' ).format(self.feed.id, self.feed.feed_url))
				return FEED_SAME, ret_values

			if self.fpf.status >= 400:
				# http error, ignore
				log.warn('[{0}] HTTP_ERROR {1}: {2}'.format(
					self.feed.id, self.fpf.status, self.feed.feed_url ))
				return FEED_ERRHTTP, ret_values

		if hasattr(self.fpf, 'bozo') and self.fpf.bozo:
			log.error( '[{0}] BOZO! Feed is not well formed: {1}'\
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
		self.feed.last_checked = datetime.datetime.now()

		log.debug('[{0}] Feed info for: {1}\n{2}'.format(
			self.feed.id, self.feed.feed_url, u'\n'.join(
			u'  {0}: {1}'.format(key, getattr(self.feed, key))
			for key in ['title', 'tagline', 'link', 'last_checked'] )))

		guids = list()
		for entry in self.fpf.entries:
			if entry.get('id', ''): guids.append(entry.get('id', ''))
			elif entry.title: guids.append(entry.title)
			elif entry.link: guids.append(entry.link)
		self.feed.save()
		if guids:
			postdict = dict( (post.guid, post)
				for post in models.Post.objects.filter(
					feed=self.feed.id ).filter(guid__in=guids) )
		else: postdict = dict()

		for entry in self.fpf.entries:
			try: ret_entry = self.process_entry(entry, postdict)
			except:
				(etype, eobj, etb) = sys.exc_info()
				print '[{0}] ! -------------------------'.format(self.feed.id)
				print traceback.format_exception(etype, eobj, etb)
				traceback.print_exception(etype, eobj, etb)
				print '[{0}] ! -------------------------'.foramt(self.feed.id)
				ret_entry = ENTRY_ERR
			ret_values[ret_entry] += 1

		self.feed.save()

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

		self.time_start = datetime.datetime.now()


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
		""" wrapper for ProcessFeed
		"""
		start_time = datetime.datetime.now()
		try:
			pfeed = ProcessFeed(feed, self.options)
			ret_feed, ret_entries = pfeed.process()
			del pfeed
		except:
			(etype, eobj, etb) = sys.exc_info()
			print '[{0}] ! -------------------------'.format(feed.id,)
			print traceback.format_exception(etype, eobj, etb)
			traceback.print_exception(etype, eobj, etb)
			print '[{0}] ! -------------------------'.format(feed.id,)
			ret_feed = FEED_ERREXC
			ret_entries = dict()

		delta = datetime.datetime.now() - start_time
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
				time.sleep(0.2)
				self.tpool.poll()
			except KeyboardInterrupt:
				log.error(u'Cancelled by user')
				break
			except threadpool.NoResultsPending:
				log.info(u'* DONE in {0}\n* Feeds: {1}\n* Entries: {2}'.format(
					unicode(datetime.datetime.now() - self.time_start),
					u' '.join(u'{0}={1}'.format( self.feed_trans[key],
						self.feed_stats[key] ) for key in self.feed_keys),
					u' '.join(u'{0}={1}'.format( self.entry_trans[key],
							self.entry_stats[key] ) for key in self.entry_keys) ))
				break


def main():
	""" Main function. Nothing to see here. Move along.
	"""

	import optparse
	parser = optparse.OptionParser(usage='%prog [options]', version=USER_AGENT)

	parser.add_option('--settings',
		help='Python path to settings module. If this isn\'t provided, '
			'the DJANGO_SETTINGS_MODULE enviroment variable will be used.')

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

	options = parser.parse_args()[0]
	if options.settings:
		os.environ["DJANGO_SETTINGS_MODULE"] = options.settings


	if options.debug: logging.basicConfig(level=logging.DEBUG)
	elif options.verbose: logging.basicConfig(level=logging.EXTRA)
	elif options.quiet: logging.basicConfig(level=logging.ERROR)
	else: logging.basicConfig(level=logging.INFO)


	from feedjack import models, fjcache

	# settting socket timeout (default= 10 seconds)
	socket.setdefaulttimeout(options.timeout)

	# our job dispatcher
	disp = Dispatcher(options, options.workerthreads)

	log.info('* BEGIN: {0}'.format(unicode(datetime.datetime.now())))

	if options.feed:
		feeds = models.Feed.objects.filter(id__in=options.feed)
		known_ids = list()
		for feed in feeds:
			known_ids.append(feed.id)
			disp.add_job(feed)
		for feed in options.feed:
			if feed not in known_ids: log.warn('Unknown feed id: {0}'.format(feed))
	elif options.site:
		try: site = models.Site.objects.get(pk=int(options.site))
		except models.Site.DoesNotExist:
			site = None
			log.warn('Unknown site id: {0}'.format(options.site))
		if site:
			feeds = [sub.feed for sub in site.subscriber_set.all()]
			for feed in feeds: disp.add_job(feed)
	else:
		for feed in models.Feed.objects.filter(is_active=True): disp.add_job(feed)

	disp.poll()

	# removing the cached data in all sites, this will only work with the
	# memcached, db and file backends
	[fjcache.cache_delsite(site.id) for site in models.Site.objects.all()]

	log.info('* END: {0} ({1})'.format( unicode(datetime.datetime.now()),
		u'{0} threads'.format(options.workerthreads) if threadpool
			else u'no threadpool module available, no parallel fetching' ))


if __name__ == '__main__': main()
