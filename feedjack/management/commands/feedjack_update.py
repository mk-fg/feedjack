# -*- coding: utf-8 -*-

'''
Management command to update feeds
	(avoids problems with Django not finding settings.py).

@author: chrisv <me@cv.gd>
'''

from django.core.management.base import NoArgsCommand, CommandError
from django.conf import settings

from feedjack import fjupdate

class Command(NoArgsCommand):
	help = 'Updates active feeds to cache.'
	option_list = NoArgsCommand.option_list\
		+ tuple(fjupdate.make_cli_option_list())

	def handle_noargs(self, **optz):
		fjupdate.main(optz)
