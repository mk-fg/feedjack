# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feedjack', '0009_auto_20150207_2251'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='processing_tags',
            field=models.CharField(help_text='Comma-separated list of tags for Feeds post-processing on this Site, if defined.<br> Used to pick which Post Processor objects added to feeds (with specified priority/tag) to apply to Posts displayed on this Site.<br> With this empty, or if none of the tags here match, attached processors are picked in lowest-first priority order, if any.<br> Special value "none" can be specified to completely disable such processing on this site.', max_length=256, verbose_name='processing tags', blank=True),
            preserve_default=True,
        ),
    ]
