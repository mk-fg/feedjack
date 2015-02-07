# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feedjack', '0006_auto_20150207_1955'),
    ]

    operations = [
        migrations.AlterField(
            model_name='filter',
            name='parameter',
            field=models.CharField(help_text=b'Parameter keyword to pass to a processing function.<br />Allows to define generic processing alghorithms in code (like "regex_filter") and actual filters/processors in db itself (specifying regex to filter/process by).<br />Empty value would mean that "parameter" keyword wont be passed to handler at all. See selected base for handler description.', max_length=512, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='postprocessor',
            name='parameter',
            field=models.CharField(help_text=b'Parameter keyword to pass to a processing function.<br />Allows to define generic processing alghorithms in code (like "regex_filter") and actual filters/processors in db itself (specifying regex to filter/process by).<br />Empty value would mean that "parameter" keyword wont be passed to handler at all. See selected base for handler description.', max_length=512, null=True, blank=True),
            preserve_default=True,
        ),
    ]
