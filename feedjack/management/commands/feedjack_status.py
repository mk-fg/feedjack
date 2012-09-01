# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import itertools as it, operator as op, functools as ft
from optparse import make_option, OptionParser

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.management.base import NoArgsCommand, CommandError
from django.contrib.humanize.templatetags.humanize import naturaltime

from feedjack import models


class Command(NoArgsCommand):
	help = 'Show registered sites, feeds and their update status.'
	option_list = NoArgsCommand.option_list + (
		make_option('-s', '--site', action='append', default=list(),
			help='Display feeds for the specified site only.'
				' Should be either numeric site_id or exact (and unique)'
				' part of the site name or title to subscribe to the added feed.'),
	)

	def p(self, *argz, **kwz):
		kwz['file'] = self.stdout
		return print(*argz, **kwz)

	def handle_noargs(self, **optz):
		if optz.get('site'):
			try: sites = list(models.Site.get_by_string(name) for name in optz['site'])
			except (ObjectDoesNotExist, MultipleObjectsReturned) as err:
				raise CommandError(err.args[0])
		else: sites = models.Site.objects.all()

		for site in sites:
			self.p('Site: {} (id: {})'.format(site, site.id))
			for feed in models.Feed.objects\
					.filter(subscriber__site_id=site.id)\
					.order_by('-is_active', 'name', '-subscriber__is_active'):
				status = list()
				if not feed.is_active: status.append('disabled')
				elif feed.subscriber_set.filter(site_id=site.id, is_active=False):
					status.append('subscriber disabled')

				self.p('  {} [{}] {}'.format(' '.join(it.imap( '({})'.format,
					status )) if int(optz['verbosity']) <= 1 else '', feed.id, feed))

				if int(optz['verbosity']) > 1:
					self.p('    Status: {}. Last check: {} ({}).'.format(
						', '.join(status) or 'active',
						feed.last_checked, naturaltime(feed.last_checked) ))

			self.p()
