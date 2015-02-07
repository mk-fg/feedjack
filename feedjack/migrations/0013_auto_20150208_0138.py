# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feedjack', '0012_postprocessortag_tag'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='postprocessorresult',
            name='overlay',
        ),
        migrations.AddField(
            model_name='postprocessorresult',
            name='_overlay',
            field=models.TextField(null=True, editable=False, db_column=b'overlay', blank=True),
            preserve_default=True,
        ),
    ]
