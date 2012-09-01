# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import itertools as it, operator as op, functools as ft

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction

from optparse import make_option, OptionParser
from feedjack import fjupdate, models
import feedparser


class Command(BaseCommand):
	help = 'Add feed to feedjack.'
	args = 'FEED_URL'
	option_list = BaseCommand.option_list + (
		make_option('-n', '--name',
			help='Name for the feed (default: fetch from feed).'),
		make_option('-c', '--shortname',
			help='Feed shortname (default: same as --name).'),
		make_option('-s', '--subscribe',
			action='append', metavar='SITE', default=list(),
			help='Either numeric site_id or exact (and unique)'
					' part of the site name or title to subscribe to the added feed.'
				' Can be specified multiple times.'),

		make_option('-f', '--initial-fetch',
			action='store_true', help='Do the initial fetch of the feed.'),
		make_option('-x', '--fetch-hidden', action='store_true',
			help='Mark initially fetched posts as "hidden",'
				' so they wont appear in syndication. Only used with --initial-fetch.'),
	)

	def handle(self, url, **optz):
		# Check if subscriber site can be found
		if optz.get('subscribe'):
			try:
				subscribe = list(
					models.Site.get_by_string(name) for name in optz['subscribe'] )
			except (ObjectDoesNotExist, MultipleObjectsReturned) as err:
				raise CommandError(err.args[0])
		else: subscribe = None

		# Fill in missing feed name fields
		if not optz.get('name'):
			fpf = feedparser.parse(url, agent=fjupdate.USER_AGENT)
			optz['name'] = fpf.feed.get('title', '')[:200]
			if not optz['name']:
				raise CommandError('Failed to acquire name from the feed ({})'.format(url))
		if not optz.get('shortname'):
			optz['shortname'] = optz['name'][:50]

		# Add Feed / Subscriber objects
		with transaction.commit_on_success():
			feed = models.Feed( feed_url=url,
				name=optz['name'], shortname=optz['shortname'] )
			feed.save()
			if subscribe:
				for site in subscribe:
					models.Subscriber.objects.create(feed=feed, site=site)

		# Perform the initial fetch, if requested
		if optz.get('initial_fetch'):
			fetch_optz, fetch_argz = OptionParser(
				option_list=fjupdate.make_cli_option_list() ).parse_args(list())
			fetch_optz.feed = [feed.id]
			fetch_optz.hidden = optz.get('fetch_hidden', False)
			fjupdate.main(fetch_optz)
