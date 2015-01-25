# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import itertools as it, operator as op, functools as ft
from optparse import make_option, OptionParser
from pprint import pformat

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.management.base import NoArgsCommand, CommandError
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.conf import settings

from feedjack import models


class Command(NoArgsCommand):
	help = 'Show registered sites, feeds and their update status.\n'\
		'Increase --verbosity value to get more details for each individual feed.'
	option_list = NoArgsCommand.option_list + (
		make_option('-s', '--site', action='append', default=list(),
			help='Display feeds for the specified site only.'
				' Should be either numeric site_id or exact (and unique)'
				' part of the site name/title or "none" to show feeds without subscribers.'),
		make_option('-f', '--feed', action='append', type='int', default=list(),
			help='Only display status for specified feeds.'),
	)

	def p(self, *argz, **kwz):
		kwz.setdefault('file', self.stdout)
		try: return print(*argz, **kwz)
		except UnicodeEncodeError:
			return print(*(( arg.encode(settings.DEFAULT_CHARSET)
				if isinstance(arg, unicode) else arg ) for arg in argz), **kwz)

	def dump(self, data, header=None, indent=''):
		data = pformat(data)
		indent_line = indent + ('  ' if header else '')
		if indent_line: data = ''.join((indent_line + line) for line in data.splitlines())
		if header: self.p(indent + header)
		return self.p(data)

	def handle_noargs(self, **optz):
		sites = list()
		if optz.get('site'):
			site_names = set(optz['site'])
			try: site_names.remove('none')
			except KeyError: pass
			else: sites.append(None)
			try: sites.extend(models.Site.get_by_string(name) for name in site_names)
			except (ObjectDoesNotExist, MultipleObjectsReturned) as err:
				raise CommandError(err.args[0])
		else: sites.extend(models.Site.objects.all())

		def display_feed_status(feed):
			status = list()
			if not feed.is_active: status.append('disabled')
			elif feed.subscriber_set.count()\
					and feed.subscriber_set.filter(site_id=site.id, is_active=False):
				status.append('subscriber disabled')

			self.p('  {0} [{1}] {2}'.format(' '.join(it.imap( '({0})'.format,
				status )) if int(optz['verbosity']) <= 1 else '', feed.id, feed))

			if int(optz['verbosity']) > 1:
				self.p('    Status: {0}. Last check: {1} ({2}).'.format(
					', '.join(status) or 'active',
					feed.last_checked, naturaltime(feed.last_checked) ))
			if int(optz['verbosity']) > 2:
				self.dump(list(feed.filters.all()), header='Filters:', indent=' '*4)

		if not optz.get('site'): sites.append(None)

		for site in sites:
			feeds = models.Feed.objects\
				.order_by('-is_active', 'name', '-subscriber__is_active')
			if optz.get('feed'): feeds = feeds.filter(id__in=optz['feed'])
			if site:
				feeds = feeds.filter(subscriber__site_id=site.id)
				if not feeds.count(): continue
				self.p('Site: {0} (id: {1}, feeds: {2})'.format(site, site.id, feeds.count()))
			else:
				feeds = list(f for f in feeds if f.subscriber_set.count() == 0)
				if not feeds: continue
				self.p('Not subscribed to by any site')

			for feed in feeds: display_feed_status(feed)
			self.p()
