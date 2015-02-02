# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Feed',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('feed_url', models.URLField(unique=True, verbose_name='feed url')),
                ('name', models.CharField(max_length=100, verbose_name='name')),
                ('shortname', models.CharField(max_length=50, verbose_name='shortname')),
                ('immutable', models.BooleanField(default=False, help_text='Do not update posts that were already fetched.', verbose_name='immutable')),
                ('skip_errors', models.BooleanField(default=False, help_text='Try to be as tolerant as possible during update.', verbose_name='skip non-critical errors')),
                ('is_active', models.BooleanField(default=True, help_text='If disabled, this feed will not be further updated.', verbose_name='is active')),
                ('title', models.CharField(max_length=200, verbose_name='title', blank=True)),
                ('tagline', models.TextField(verbose_name='tagline', blank=True)),
                ('link', models.URLField(max_length=511, verbose_name='link', blank=True)),
                ('filters_logic', models.PositiveSmallIntegerField(default=0, verbose_name=b'Composition', choices=[(0, b'Should pass ALL filters (AND logic)'), (1, b'Should pass ANY of the filters (OR logic)')])),
                ('etag', models.CharField(max_length=127, verbose_name='etag', blank=True)),
                ('last_modified', models.DateTimeField(null=True, verbose_name='last modified', blank=True)),
                ('last_checked', models.DateTimeField(null=True, verbose_name='last checked', blank=True)),
            ],
            options={
                'ordering': ('name', 'feed_url'),
                'verbose_name': 'feed',
                'verbose_name_plural': 'feeds',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Filter',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('parameter', models.CharField(help_text=b'Parameter keyword to pass to a filter function.<br />Allows to define generic filtering alghorithms in code (like "regex_filter") and actual filters in db itself (specifying regex to filter by).<br />Null value would mean that "parameter" keyword wont be passed to handler at all. See selected filter base for handler description.', max_length=512, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FilterBase',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=64)),
                ('handler_name', models.CharField(help_text=b'Processing function as and import-name, like "myapp.filters.some_filter" or just a name if its a built-in filter (contained in feedjack.filters), latter is implied if this field is omitted.<br /> Should accept Post object and optional (or not) parameter (derived from actual Filter field) and return boolean value, indicating whether post should be displayed or not.', max_length=256, blank=True)),
                ('crossref', models.BooleanField(help_text=b'Indicates whether filtering results depend on other posts (and possibly their filtering results) or not.<br /> Note that ordering in which these filters are applied to a posts, as well as "update condition" should match for any cross-referenced feeds. This restriction might go away in the future.', verbose_name=b'Cross-referencing')),
                ('crossref_rebuild', models.PositiveSmallIntegerField(default=0, help_text=b"Neighbor posts' filtering results update condition.", choices=[(0, b'Rebuild newer results, starting from the changed point, but not older than crossref_span'), (1, b'Rebuild last results on any changes to the last posts inside crossref_span')])),
                ('crossref_timeline', models.PositiveSmallIntegerField(default=0, help_text=b'Which time to use for timespan calculations on rebuild.', choices=[(0, b'Time the post was first fetched'), (1, b'Time of last modification to the post, according to the source')])),
                ('crossref_span', models.PositiveSmallIntegerField(help_text=b'How many days of history should be re-referenced on post changes to keep this results conclusive. Performance-quality knob, since ideally this should be an infinity (indicated by NULL value).', null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FilterResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('result', models.BooleanField()),
                ('timestamp', models.DateTimeField(auto_now=True)),
                ('filter', models.ForeignKey(to='feedjack.Filter')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='name')),
                ('link', models.URLField(verbose_name='link')),
            ],
            options={
                'verbose_name': 'link',
                'verbose_name_plural': 'links',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=2047, verbose_name='title')),
                ('link', models.URLField(max_length=2047, verbose_name='link')),
                ('content', models.TextField(verbose_name='content', blank=True)),
                ('date_modified', models.DateTimeField(verbose_name='date modified')),
                ('guid', models.CharField(max_length=255, verbose_name='guid', db_index=True)),
                ('author', models.CharField(max_length=255, verbose_name='author', blank=True)),
                ('author_email', models.EmailField(max_length=75, verbose_name='author email', blank=True)),
                ('comments', models.URLField(max_length=511, verbose_name='comments', blank=True)),
                ('hidden', models.BooleanField(default=False, help_text=b'Manual switch to completely hide the Post, although it will be present for internal checks, like filters.')),
                ('_enclosures', models.TextField(editable=False, db_column=b'enclosures', blank=True)),
                ('date_created', models.DateTimeField(auto_now_add=True, verbose_name='date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='date updated')),
                ('filtering_result', models.NullBooleanField()),
                ('feed', models.ForeignKey(related_name='posts', verbose_name='feed', to='feedjack.Feed')),
            ],
            options={
                'ordering': ('-date_modified',),
                'verbose_name': 'post',
                'verbose_name_plural': 'posts',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Site',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='name')),
                ('url', models.CharField(help_text='Example: http://www.planetexample.com, http://www.planetexample.com:8000/foo', unique=True, max_length=100, verbose_name='url')),
                ('title', models.CharField(max_length=200, verbose_name='title')),
                ('description', models.TextField(verbose_name='description', blank=True)),
                ('welcome', models.TextField(null=True, verbose_name='welcome', blank=True)),
                ('greets', models.TextField(null=True, verbose_name='greets', blank=True)),
                ('default_site', models.BooleanField(default=False, verbose_name='default site')),
                ('posts_per_page', models.PositiveIntegerField(default=20, verbose_name='posts per page')),
                ('order_posts_by', models.PositiveSmallIntegerField(default=1, verbose_name='order posts by', choices=[(1, 'Time the post was published.'), (2, 'Time the post was first obtained.'), (3, 'Day the post was first obtained (for nicer per-feed grouping).')])),
                ('tagcloud_levels', models.PositiveIntegerField(default=5, verbose_name='tagcloud level')),
                ('show_tagcloud', models.BooleanField(default=True, verbose_name='show tagcloud')),
                ('use_internal_cache', models.BooleanField(default=True, verbose_name='use internal cache')),
                ('cache_duration', models.PositiveIntegerField(default=86400, help_text='Duration in seconds of the cached pages and data.', verbose_name='cache duration')),
                ('template', models.CharField(help_text='This template must be a directory in your feedjack templates directory. Leave blank to use the default template.', max_length=100, null=True, verbose_name='template', blank=True)),
                ('links', models.ManyToManyField(to='feedjack.Link', null=True, verbose_name='links', blank=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'site',
                'verbose_name_plural': 'sites',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Subscriber',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text="Keep blank to use the Feed's original name.", max_length=100, null=True, verbose_name='name', blank=True)),
                ('shortname', models.CharField(help_text="Keep blank to use the Feed's original shortname.", max_length=50, null=True, verbose_name='shortname', blank=True)),
                ('is_active', models.BooleanField(default=True, help_text="If disabled, this subscriber will not appear in the site or in the site's feed.", verbose_name='is active')),
                ('feed', models.ForeignKey(verbose_name='feed', to='feedjack.Feed')),
                ('site', models.ForeignKey(verbose_name='site', to='feedjack.Site')),
            ],
            options={
                'ordering': ('site', 'name', 'feed'),
                'verbose_name': 'subscriber',
                'verbose_name_plural': 'subscribers',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255, verbose_name='name')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'tag',
                'verbose_name_plural': 'tags',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='subscriber',
            unique_together=set([('site', 'feed')]),
        ),
        migrations.AddField(
            model_name='post',
            name='tags',
            field=models.ManyToManyField(to='feedjack.Tag', verbose_name='tags', blank=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='post',
            unique_together=set([('feed', 'guid')]),
        ),
        migrations.AddField(
            model_name='filterresult',
            name='post',
            field=models.ForeignKey(related_name='filtering_results', to='feedjack.Post'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='filter',
            name='base',
            field=models.ForeignKey(related_name='filters', to='feedjack.FilterBase'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='feed',
            name='filters',
            field=models.ManyToManyField(related_name='feeds', to='feedjack.Filter', blank=True),
            preserve_default=True,
        ),
    ]
