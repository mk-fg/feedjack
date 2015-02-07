# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feedjack', '0008_auto_20150207_2112'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='processing_tags',
            field=models.TextField(help_text='Comma-separated list of tags for Feeds post-processing on this Site, if defined.<br> Used to pick which Post Processor objects added to feeds (with specified priority/tag) to apply to Posts displayed on this Site. With this empty, or if none of the tags here match, attached processors are picked in lowest-first priority order, if any.', verbose_name='processing_tags', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='filter',
            name='parameter',
            field=models.CharField(help_text=b'Parameter keyword to pass to a processing function.<br>Allows to define generic processing alghorithms in code (like "regex_filter") and actual filters/processors in db itself (specifying regex to filter/process by).<br>Empty value would mean that "parameter" keyword wont be passed to handler at all. See selected base for handler description.', max_length=512, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='filterbase',
            name='crossref',
            field=models.BooleanField(default=False, help_text=b'Indicates whether filtering results depend on other posts (and possibly their filtering results) or not.<br> Note that ordering in which these filters are applied to a posts, as well as "update condition" should match for any cross-referenced feeds. This restriction might go away in the future.', verbose_name=b'Cross-referencing'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='filterbase',
            name='handler_name',
            field=models.CharField(help_text=b'Processing function as and import-name, like "myapp.filters.some_filter" or just a name if its a built-in filter (contained in feedjack.filters), latter is implied if this field is omitted.<br> Should accept Post object and optional (or not) parameter (derived from actual Filter field) and return boolean value, indicating whether post should be displayed or not.', max_length=256, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='postprocessor',
            name='parameter',
            field=models.CharField(help_text=b'Parameter keyword to pass to a processing function.<br>Allows to define generic processing alghorithms in code (like "regex_filter") and actual filters/processors in db itself (specifying regex to filter/process by).<br>Empty value would mean that "parameter" keyword wont be passed to handler at all. See selected base for handler description.', max_length=512, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='postprocessorbase',
            name='handler_name',
            field=models.CharField(help_text=b'Processing function as and import-name, like "myapp.filters.some_filter" or just a name if its a built-in processor (contained in feedjack.filters), latter is implied if this field is omitted.<br> Should accept Post object and optional (or not) parameter (derived from actual PostProcessor field) and return a dict of fields of Post object to override or None.', max_length=256, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='postprocessorresult',
            name='processor',
            field=models.ForeignKey(related_name='results', to='feedjack.PostProcessor'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='postprocessortag',
            name='feed',
            field=models.ForeignKey(related_name='post_processor_tags', to='feedjack.Feed'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='postprocessortag',
            name='processor',
            field=models.ForeignKey(related_name='feed_tags', to='feedjack.PostProcessor'),
            preserve_default=True,
        ),
    ]
