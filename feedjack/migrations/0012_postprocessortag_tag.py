# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feedjack', '0011_auto_20150208_0053'),
    ]

    operations = [
        migrations.AddField(
            model_name='postprocessortag',
            name='tag',
            field=models.CharField(help_text=b'Can be used to pick specific processor in the templates.', max_length=128, blank=True),
            preserve_default=True,
        ),
    ]
