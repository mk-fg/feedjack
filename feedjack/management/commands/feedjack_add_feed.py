# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction

from feedjack import fjupdate, models

import itertools as it, operator as op, functools as ft
import feedparser


class Command(BaseCommand):

	help = 'Add new feed.'

	def add_arguments(self, parser):
		parser.add_argument('feed_url', help='URL of the feed to add.')

		parser.add_argument('-n', '--name', metavar='text',
			help='Name for the feed (default: fetch from feed).')
		parser.add_argument('-c', '--shortname', metavar='text',
			help='Feed shortname (default: same as --name).')
		parser.add_argument('-d', '--field-data', metavar='yaml-data',
			help='YAML (falling back to built-in JSON,'
					' if unavailable) dict of arbitrary data to apply to feed model.'
				' Example (YAML): "immutable: true".')

		parser.add_argument('-s', '--subscribe',
			action='append', metavar='site-spec', default=list(),
			help='Either numeric site_id or exact (and unique)'
					' part of the site name or title to subscribe to the added feed.'
				' Can be specified multiple times.')
		parser.add_argument('-e', '--filter',
			action='append', type=int, metavar='filter-id', default=list(),
			help='Numeric filter_id to attach to a feed. Can be specified multiple times.')

		parser.add_argument('-f', '--initial-fetch',
			action='store_true', help='Do the initial fetch of the feed.')
		parser.add_argument('-x', '--fetch-hidden', action='store_true',
			help='Mark initially fetched posts as "hidden",'
				' so they wont appear in syndication. Only used with --initial-fetch.')

	def handle(self, **opts):
		opts = type(b'Opts', (object,), dict((k.replace('-', '_'), v) for k,v in opts.viewitems()))

		# Check if subscriber sites and filters can be found
		if opts.subscribe:
			try:
				subscribe = list(
					models.Site.objects.get_by_string(name) for name in opts.subscribe )
			except (ObjectDoesNotExist, MultipleObjectsReturned) as err:
				raise CommandError(unicode(err))
		else: subscribe = list()
		if opts.filter:
			try: filters = list(models.Filter.objects.get(id=fid) for fid in opts.filter)
			except ObjectDoesNotExist as err:
				raise CommandError(unicode(err))
		else: filters = list()

		# Fill in missing feed name fields
		if not opts.name:
			fpf = feedparser.parse(opts.feed_url, agent=fjupdate.USER_AGENT)
			opts.name = fpf.feed.get('title', '')[:200]
			if not opts.name:
				raise CommandError('Failed to acquire name from the feed ({0})'.format(opts.feed_url))
		if not opts.shortname: opts.shortname = opts.name[:50]

		# Add Feed / Subscriber objects
		with transaction.atomic():
			feed = models.Feed( feed_url=opts.feed_url,
				name=opts.name, shortname=opts.shortname )
			if opts.field_data:
				try: import yaml as s
				except ImportError: import json as s
				import io
				for k, v in s.load(io.BytesIO(opts.field_data)).iteritems(): setattr(feed, k, v)
			feed.save()
			for f in filters: feed.filters.add(f)
			for site in subscribe:
				models.Subscriber.objects.create(feed=feed, site=site)

		# Perform the initial fetch, if requested
		if opts.initial_fetch:
			fetch_opts = fjupdate.argparse_get_parser().parse_args(list())
			for k, v in [('feed', [feed.id]), ('hidden', opts.fetch_hidden)]:
				assert hasattr(fetch_opts, k), fetch_opts
				setattr(fetch_opts, k, v)
			fetch_opts.verbosity = opts.verbosity
			fjupdate.main(fetch_opts, log_stream=self.stdout)
