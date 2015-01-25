from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from feedjack.models import Feed, Post
from datetime import datetime, timedelta
import pytz


class Command(BaseCommand):
	'Purges some or all of the RSS feed content.'

	option_list = BaseCommand.option_list + (
		make_option('-l', '--list', action='store_true',
			dest='list', default=False, help='List available feeds'),
		make_option('-d', '--delta', dest='delta',
			type='int', default=14, help='The age in days to purge the entries (%default)'),
		make_option('--full', action='store_true',
			dest='full', default=False, help='Purge feeds completely'),
	)
	usage = lambda foo, bar: ( '%prog [feedname1]'
		' [feedname2] [options]\n' + Command.__doc__.rstrip() )

	def handle(self, *feeds, **options):
		list_opt = options.get('list')
		delta = options.get('delta')
		verbosity = options.get('verbosity', 1)

		# Build a list of feeds to purge.
		available = [f.shortname for f in Feed.objects.all()]

		if list_opt:
			self.stdout.write('Feeds are: ' + ', '.join(available) + '\n')
		else:
			if feeds:
				# Ensure specified feeds are defined.
				not_defined = set(feeds) - set(available)
				if not_defined:
					raise CommandError('Specified feeds not defined: ' + ', '.join(not_defined))
			else:
				# No feeds specified - default to all in feedjack
				feeds = available

			for feed in feeds:
				if options.get('full', 0):
					expired = (datetime.now(pytz.utc) + timedelta(1))
					if verbosity >= 2:
						self.stdout.write('Purging %s completely\n' % (feed,))
				else:
					expired = (datetime.now(pytz.utc) - timedelta(delta))
					if verbosity >= 2:
						self.stdout.write('Purging %s for %d days\n' % (feed, delta))
				# feedjack post content
				Post.objects.filter(feed__shortname=feed).filter(date_created__lte=expired).delete()
			if verbosity >= 1:
				self.stdout.write('Purged %d feed(s)\n' % (len(feeds),))
