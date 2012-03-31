'''
management command to update feeds (avoids problems with Django not finding settings.py)

@author: chrisv <me@cv.gd>
'''

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from feedjack.fjupdater import bulk_update

import logging
logging.EXTRA = (logging.DEBUG + logging.INFO) // 2

class Command(BaseCommand):
    help = "updates active feeds to cache"
    
    option_list = BaseCommand.option_list + (
        make_option('--force', action='store_true',
                    help='Do not use stored modification time or etag when fetching feed updates.'),
        make_option('--hidden', action='store_true',
                    help='Mark all fetched (new) posts as "hidden". Intended'
                        ' usage is initial fetching of large (number of) feeds.'),
        make_option('--max-feed-difference', action='store', dest='max_diff', type='int',
                    help='Maximum percent of new posts to consider feed valid.'
                         ' Intended for broken feeds, which sometimes return seemingly-random content.'),
        make_option('-f', '--feed', action='append', type='int',
                    help='A feed id to be updated. This option can be given multiple '
                    'times to update several feeds at the same time (-f 1 -f 4 -f 7).'),
        make_option('-s', '--site', action='append', type='int',
                    help='A site id (or several of them) to update.'),
        make_option('-t', '--timeout', type='int', default=20,
                    help='Socket timeout (in seconds) for connections (default: %(default)s).'),
        make_option('-d', '--delay', type='int', default=0,
                    help='Delay between fetching the feeds (default: none).'),
        make_option('-q', '--quiet', action='store_true',
                    help='Report only severe errors, no info or warnings.'),
        #make_option('-v', '--verbose', action='store_true', help='Verbose output.'),
        make_option('--debug', action='store_true', help='Even more verbose output.')                                             
    )
    
    def handle(self, **options):
        class optz(object):
            def __init__(self, options):
                self.feed = options['feed']
                self.site = options['site']
                self.timeout = options['timeout']
                self.delay = options['delay']
                self.max_diff = options['max_diff']
                self.force = options['force']
                self.hidden = options['hidden']
        
        if options.get('debug'): logging.basicConfig(level=logging.DEBUG)
        #elif options.get('verbose'): logging.basicConfig(level=logging.EXTRA)
        elif options.get('quiet'): logging.basicConfig(level=logging.WARNING)
        else: logging.basicConfig(level=logging.INFO)

        bulk_update(optz(options))