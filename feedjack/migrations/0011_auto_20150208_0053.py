# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feedjack', '0010_auto_20150207_2304'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='postprocessortag',
            name='tag',
        ),
        migrations.AlterField(
            model_name='postprocessortag',
            name='priority',
            field=models.PositiveSmallIntegerField(default=100, help_text=b'Lowest-first logic. Affects which of the attached processing hooks will be picked by default in the template, unless some specific one is specified (and exists).'),
            preserve_default=True,
        ),
    ]
