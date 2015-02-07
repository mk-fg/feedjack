# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feedjack', '0007_auto_20150207_2007'),
    ]

    operations = [
        migrations.AlterField(
            model_name='postprocessor',
            name='base',
            field=models.ForeignKey(related_name='post_processors', to='feedjack.PostProcessorBase'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='postprocessorbase',
            name='handler_name',
            field=models.CharField(help_text=b'Processing function as and import-name, like "myapp.filters.some_filter" or just a name if its a built-in processor (contained in feedjack.filters), latter is implied if this field is omitted.<br /> Should accept Post object and optional (or not) parameter (derived from actual PostProcessor field) and return a dict of fields of Post object to override or None.', max_length=256, blank=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='postprocessorresult',
            unique_together=set([('processor', 'post')]),
        ),
    ]
