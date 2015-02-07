# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feedjack', '0005_initial_data_migration'),
    ]

    operations = [
        migrations.CreateModel(
            name='PostProcessor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('parameter', models.CharField(help_text=b'Parameter keyword to pass to a processing function.<br />Allows to define generic processing alghorithms in code (like "regex_filter") and actual filters in db itself (specifying regex to filter by).<br />Empty value would mean that "parameter" keyword wont be passed to handler at all. See selected base for handler description.', max_length=512, null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PostProcessorBase',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=64)),
                ('handler_name', models.CharField(help_text=b'Processing function as and import-name, like "myapp.filters.some_filter" or just a name if its a built-in processor (contained in feedjack.filters), latter is implied if this field is omitted.<br /> Should accept Post object and optional (or not) parameter (derived from actual PostProcessor field) and return a dict of fields of Post object to override.', max_length=256, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PostProcessorResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('overlay', models.TextField(null=True, editable=False, blank=True)),
                ('timestamp', models.DateTimeField(auto_now=True)),
                ('post', models.ForeignKey(related_name='processing_results', to='feedjack.Post')),
                ('processor', models.ForeignKey(to='feedjack.PostProcessor')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PostProcessorTag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('tag', models.PositiveSmallIntegerField(help_text=b'Can be used to pick specific processor in the templates.')),
                ('priority', models.PositiveSmallIntegerField(help_text=b'Lowest-first logic. Affects which of the attached processing hooks will be picked by default in the template, unless some specific one is specified (and exists).')),
                ('feed', models.ForeignKey(to='feedjack.Feed')),
                ('processor', models.ForeignKey(to='feedjack.PostProcessor')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='postprocessor',
            name='base',
            field=models.ForeignKey(related_name='postprocessors', to='feedjack.PostProcessorBase'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='feed',
            name='post_processors',
            field=models.ManyToManyField(related_name='feeds', through='feedjack.PostProcessorTag', to='feedjack.PostProcessor', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='feed',
            name='filters_logic',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='composition', choices=[(0, b'Should pass ALL filters (AND logic)'), (1, b'Should pass ANY of the filters (OR logic)')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='filter',
            name='parameter',
            field=models.CharField(help_text=b'Parameter keyword to pass to a processing function.<br />Allows to define generic processing alghorithms in code (like "regex_filter") and actual filters in db itself (specifying regex to filter by).<br />Empty value would mean that "parameter" keyword wont be passed to handler at all. See selected base for handler description.', max_length=512, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='filterbase',
            name='crossref_span',
            field=models.PositiveSmallIntegerField(help_text=b'How many days of history should be re-referenced on post changes to keep this results conclusive. Performance-quality knob, since ideally this should be an infinity (indicated by empty value).', null=True, blank=True),
            preserve_default=True,
        ),
    ]
