# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from feedjack import fjupdate


class Command(BaseCommand):
	help = fjupdate.argparse_get_description()

	def add_arguments(self, parser):
		return fjupdate.argparse_add_args(parser)

	def handle(self, **opts):
		return fjupdate.main(opts, log_stream=self.stdout)
