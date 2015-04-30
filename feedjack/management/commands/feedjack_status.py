# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from django.core.management.base import BaseCommand, CommandError
from django.utils import encoding

from feedjack import models, utils

import itertools as it, operator as op, functools as ft


class Command(BaseCommand):

	help = ( 'Show registered sites, feeds and their update status.\n'
		'Increase --verbosity value to get more details for each individual feed.' )

	def add_arguments(self, parser):
		parser.add_argument('-s', '--site',
			action='append', metavar='site-spec',
			help='Display feeds for the specified site(s) only.'
				' Should be either numeric site_id or exact (and unique)'
					' part of the site name/title or "none" to show feeds without subscribers.'
				' Can be specified multiple times, all specified sites will be used.')
		parser.add_argument('-f', '--feed',
			action='append', metavar='feed-spec',
			help='Only display status for specified feeds. Either id ot exact/unique name part.'
				' Can be specified multiple times, info for all specified feeds will be displayed.')

	def p(self, fmt, *args, **kws):
		msg = fmt.format(*args, **kws)
		try: return self.stdout.write(msg)
		except UnicodeEncodeError:
			return self.stdout.write(encoding.smart_bytes(msg))

	def dump(self, data, header=None, indent=''):
		from pprint import pformat
		data = pformat(data)
		indent_line = indent + ('  ' if header else '')
		if indent_line: data = ''.join((indent_line + line) for line in data.splitlines())
		if header: self.p(indent + header)
		return self.p(data)

	def handle(self, **opts):
		opts = type(b'Opts', (object,), dict((k.replace('-', '_'), v) for k,v in opts.viewitems()))

		sites = list()
		if opts.site:
			site_names = set(opts.site)
			try: site_names.remove('none')
			except KeyError: pass
			else: sites.append(None)
			try: sites.extend(models.Site.objects.get_by_string(name) for name in site_names)
			except (models.ObjectDoesNotExist, models.MultipleObjectsReturned) as err:
				raise CommandError(err.args[0])
		else: sites.extend(models.Site.objects.all())

		def display_feed_status(feed):
			status = list()
			if not feed.is_active: status.append('disabled')
			elif feed.subscriber_set.count()\
					and feed.subscriber_set.filter(site_id=site.id, is_active=False):
				status.append('subscriber disabled')

			self.p( '  {} [{}] {}', ' '.join(it.imap( '({0})'.format,
				status )) if int(opts.verbosity) <= 1 else '', feed.id, feed )

			if int(opts.verbosity) > 1:
				self.p(
					'    Status: {}. Last check: {} ({}).', ', '.join(status) or 'active',
					feed.last_checked, utils.naturaltime_diff(feed.last_checked, ext='ago') )
			if int(opts.verbosity) > 2:
				filters = list(feed.filters.all())
				if filters: self.dump(filters, header='Filters:', indent=' '*4)

		if not opts.site: sites.append(None)

		for site in sites:
			feeds = models.Feed.objects\
				.order_by('-is_active', 'name', '-subscriber__is_active')
			if opts.feed: feeds = feeds.filter(id__in=opts.feed)
			if site:
				feeds = feeds.filter(subscriber__site_id=site.id)
				if not feeds.count(): continue
				self.p('Site: {} (id: {}, feeds: {})', site, site.id, feeds.count())
			else:
				feeds = list(f for f in feeds if f.subscriber_set.count() == 0)
				if not feeds: continue
				self.p('Not subscribed to by any site')

			for feed in feeds: display_feed_status(feed)
