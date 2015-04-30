# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from feedjack import models
from feedjack.utils import command_logger_setup, naturaltime_diff

import itertools as it, operator as op, functools as ft
from datetime import datetime, timedelta
import os, sys, re, time, subprocess
import logging, argparse


_short_ts_days = dict(y=365.25, yr=365.25, mo=30.5, w=7, d=1)
_short_ts_s = dict(h=3600, hr=3600, m=60, min=60, s=1, sec=1)

def _short_ts_regexp():
	'''Generates regexp for parsing of
		shortened relative timestamps, as shown in the table.'''
	ts_re = ['^']
	for k in it.chain(_short_ts_days, _short_ts_s):
		ts_re.append(r'(?P<{0}>\d+{0}\s*)?'.format(k))
	return re.compile(''.join(ts_re), re.I | re.U)
_short_ts_regexp = _short_ts_regexp()

def parse_timestamp(ts_str):
	'''Match time either in human-readable format (as accepted by dateutil),
		or same time-offset format, as used in the table (e.g. "NdMh ago", or just "NdMh").'''
	assert isinstance(ts_str, bytes), [type(ts_str), repr(ts_str)]
	ts_str = ts_str.replace('_', ' ')

	# Try to parse time offset in short format
	match = _short_ts_regexp.search(ts_str)
	if match and any(match.groups()):
		delta = list()
		parse_int = lambda v: int(''.join(c for c in v if c.isdigit()))
		for units in [_short_ts_days, _short_ts_s]:
			val = 0
			for k, v in units.iteritems():
				try:
					if not match.group(k): continue
					n = parse_int(match.group(k))
				except IndexError: continue
				val += n * v
			delta.append(val)
		return timezone.localtime(timezone.now()) - timedelta(*delta)

	# Fallback to other generic formats
	ts = None
	if not ts:
		match = re.search( # common BE format
			r'^(?P<date>(?:\d{2}|(?P<Y>\d{4}))-\d{2}-\d{2})'
			r'(?:[ T](?P<time>\d{2}(?::\d{2}(?::\d{2})?)?)?)?$', ts_str )
		if match:
			tpl = 'y' if not match.group('Y') else 'Y'
			tpl, ts_str = '%{}-%m-%d'.format(tpl), match.group('date')
			if match.group('time'):
				tpl_time = ['%H', '%M', '%S']
				ts_str_time = match.group('time').split(':')
				ts_str += ' ' + ':'.join(ts_str_time)
				tpl += ' ' + ':'.join(tpl_time[:len(ts_str_time)])
			try: ts = timezone.make_aware(datetime.strptime(ts_str, tpl))
			except ValueError: pass
	if not ts:
		# coreutils' "date" parses virtually everything, but is more expensive to use
		with open(os.devnull, 'w') as devnull:
			proc = subprocess.Popen(
				['date', '+%s', '-d', ts_str],
				stdout=subprocess.PIPE, stderr=devnull, close_fds=True )
			val = proc.stdout.read()
			if not proc.wait():
				ts = timezone.make_aware(datetime.fromtimestamp(int(val.strip())))

	if ts: return ts
	raise ValueError('Unable to parse date/time string: {0}'.format(ts_str))


class Command(BaseCommand):
	help = 'Purge site/feed contents by specified criterias.'

	def add_arguments(self, parser):
		ts_types = ['created', 'modified', 'updated']

		parser.add_argument('-n', '--dry-run', action='store_true',
			help='Only show posts that will be affected, do not actually remove anything.')
		parser.add_argument('-q', '--quiet', action='store_true',
			help='Do not display info about affected entries.')
		parser.add_argument('--debug', action='store_true', help='Even more verbose output.')
		parser.add_argument('--django-logging', action='store_true',
			help='Do not touch logging settings, as they might be configured in Django settings.py.'
				' Default is to try overriding these to provide requested/expected console output.'
				' This flag overrides --quiet and django-admin --verbosity options.')

		parser.add_argument('-s', '--site',
			action='append', metavar='site-spec',
			help='Site to remove posts from. Either id ot exact/unique name part.'
				' Can be specified multiple times, all specified sites will be affected.')
		parser.add_argument('-f', '--feed',
			action='append', metavar='feed-spec',
			help='Feed to remove posts from. Either id ot exact/unique name part.'
				' Can be specified multiple times, all specified feeds will be affected.')

		subcmds = parser.add_subparsers(
			parser_class=argparse.ArgumentParser,
			dest='type', title='Cleanup types',
			description='Supported cleanup types (have their own suboptions as well)' )

		cmd = subcmds.add_parser('by-age',
			description='Remove posts with specific timestamps',
			epilog='"time-spec" can be parsed as a relative short-form'
				' times in the past (e.g. "30s", "10min", "1h 20m", etc), iso8601-ish'
				' times/dates or falls back to just using "date" binary (which parses a lot of stuff).')
		cmd.add_argument('time-spec',
			help='Absolute or relative time specification'
				' to remove posts after (or before, with --newer).')

		cmd.add_argument('-t', '--timestamp-type',
			metavar='type', default='modified', choices=ts_types,
			help='Timestamp type to use (default: %(default)s). Choices: {}'.format(', '.join(ts_types)))
		cmd.add_argument('--newer', action='store_true',
			help='Cleanup newest posts (newer than specified time) instead of oldest ones.')


	def handle(self, **opts):
		opts = type(b'Opts', (object,), dict((k.replace('-', '_'), v) for k,v in opts.viewitems()))
		log = logging.getLogger('feedjack.purge')
		command_logger_setup(log, opts, stream=self.stdout)

		if not opts.feed and not opts.site:
			feeds = set(models.Feed.all())
			log.info('All feeds will be affected (%s)', len(feeds))
		else:
			feeds = set()
			if opts.feed:
				try: feeds.update(models.Feed.objects.get_by_string(name) for name in opts.feed)
				except (models.ObjectDoesNotExist, models.MultipleObjectsReturned) as err:
					raise CommandError(unicode(err))
			if opts.site:
				try: sites = list(models.Site.objects.get_by_string(name) for name in opts.site)
				except (models.ObjectDoesNotExist, models.MultipleObjectsReturned) as err:
					raise CommandError(unicode(err))
				for site in sites: feeds.update(site.feeds)
			if log.isEnabledFor(logging.INFO):
				if log.isEnabledFor(logging.DEBUG):
					log.debug('List of affected feeds (%s):', len(feeds))
					for feed in sorted(feeds, key=op.attrgetter('pk')): log.debug(' - [%s] %s', feed.pk, feed)
				else:
					log.info('Number of affected feeds: %s (listed with more verbose logging)', len(feeds))

		if opts.type == 'by-age':
			ts0, ts = timezone.localtime(timezone.now()), parse_timestamp(opts.time_spec)
			log.info(
				'Parsed time spec %r as %s (delta: %s)',
				opts.time_spec, ts, naturaltime_diff(ts, ts0) )

			ts_field = 'date_{}'.format(opts.timestamp_type)
			ts_field_check = {'{}__{}'.format(ts_field, 'gt' if opts.newer else 'lt'): ts}
			log.debug('Timestamp field check: %s', ts_field_check)

			posts = models.Post.objects.filter(feed__in=feeds, **ts_field_check)

			if log.isEnabledFor(logging.INFO):
				if log.isEnabledFor(logging.DEBUG):
					log.debug('List of selected Posts (%s):', posts.count())
					for post in posts.order_by('pk'): log.debug(' - [%s] %s', post.pk, post)
				else:
					log.info( 'Selected %s Post object(s) for'
						' cleanup (listed with more verbose logging)', posts.count() )

			if not opts.dry_run:
				show_count = log.isEnabledFor(logging.INFO) and posts.count()
				if show_count:
					log.info('Removing %s entries', show_count)
					ts0 = time.time()
				posts.delete()
				if show_count:
					log.info('Finished removal of %s entries (time: %.2fs)', show_count, time.time() - ts0)

		else: raise ValueError(post.type)
