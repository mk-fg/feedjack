# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import os, sys, logging


def command_logger_setup( logger, opts,
		stream=sys.stdout, verbose_level=logging.DEBUG ):
	if not isinstance(opts, dict): opts = vars(opts)

	if opts.get('django_logging'): return

	verbosity = int(getattr(opts, 'verbosity', 1)) # option from django-admin
	if opts.get('debug') or verbosity >= 3: verbosity = logging.DEBUG
	elif opts.get('verbose') or verbosity >= 2: verbosity = verbose_level
	elif opts.get('quiet') or verbosity < 1: verbosity = logging.WARNING
	else: verbosity = logging.INFO
	logging.basicConfig(stream=stream, level=verbosity)

	# Adjust logger for Django-standard "--verbosity" option, add console-output handler
	# This can unexpectedly clash with logging config in settings.py
	logger.setLevel(verbosity)
	log_handler = logging.StreamHandler(stream)
	log_handler.setFormatter(
		logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s') )
	logger.addHandler(log_handler)
