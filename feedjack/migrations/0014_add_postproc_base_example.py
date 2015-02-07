# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from django.db import models, migrations, transaction
from django.core import serializers

from os.path import join, dirname
import os, sys


def initial_data_import(apps, schema_editor):
	fj_app = apps.get_app_config('feedjack')
	data_path = 'fixtures', 'migration_data_0014.json'
	if fj_app.path: data_path = join(fj_app.path, *data_path)
	else:
		import feedjack
		data_path = join(dirname(feedjack.__file__), *data_path)

	with open(data_path, 'rb') as data, transaction.atomic():
		data = serializers.deserialize('json', data)
		for obj_wrapper in data:
			obj = obj_wrapper.object
			model = type(obj)
			try: model.objects.get(pk=obj.pk)
			except model.DoesNotExist: pass
			else: break # not overwriting any existing objects (likely same anyway)
		else: # no conflicting pk's present - save all objects
			for obj_wrapper in data: obj_wrapper.save()


class Migration(migrations.Migration):

	dependencies = [('feedjack', '0013_auto_20150208_0138')]
	operations = [migrations.RunPython(initial_data_import)]
