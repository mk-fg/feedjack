# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Post.date_modified'
        db.alter_column(u'feedjack_post', 'date_modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 8, 12, 0, 0)))

    def backwards(self, orm):

        # Changing field 'Post.date_modified'
        db.alter_column(u'feedjack_post', 'date_modified', self.gf('django.db.models.fields.DateTimeField')(null=True))

    models = {
        u'feedjack.feed': {
            'Meta': {'ordering': "('name', 'feed_url')", 'object_name': 'Feed'},
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'feed_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200'}),
            'filters': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'feeds'", 'blank': 'True', 'to': u"orm['feedjack.Filter']"}),
            'filters_logic': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'immutable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_checked': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'link': ('django.db.models.fields.URLField', [], {'max_length': '511', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'shortname': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'skip_errors': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'tagline': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        },
        u'feedjack.filter': {
            'Meta': {'object_name': 'Filter'},
            'base': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'filters'", 'to': u"orm['feedjack.FilterBase']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parameter': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'})
        },
        u'feedjack.filterbase': {
            'Meta': {'object_name': 'FilterBase'},
            'crossref': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'crossref_rebuild': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'crossref_span': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'crossref_timeline': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'handler_name': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'})
        },
        u'feedjack.filterresult': {
            'Meta': {'object_name': 'FilterResult'},
            'filter': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['feedjack.Filter']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'filtering_results'", 'to': u"orm['feedjack.Post']"}),
            'result': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'feedjack.link': {
            'Meta': {'object_name': 'Link'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        u'feedjack.post': {
            'Meta': {'ordering': "('-date_modified',)", 'unique_together': "(('feed', 'guid'),)", 'object_name': 'Post'},
            '_enclosures': ('django.db.models.fields.TextField', [], {'db_column': "'enclosures'", 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'author_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'comments': ('django.db.models.fields.URLField', [], {'max_length': '511', 'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {}),
            'date_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': u"orm['feedjack.Feed']"}),
            'filtering_result': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'guid': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.URLField', [], {'max_length': '2047'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['feedjack.Tag']", 'symmetrical': 'False', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '2047'})
        },
        u'feedjack.site': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Site'},
            'cache_duration': ('django.db.models.fields.PositiveIntegerField', [], {'default': '86400'}),
            'default_site': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'greets': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'links': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['feedjack.Link']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'order_posts_by': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1'}),
            'posts_per_page': ('django.db.models.fields.PositiveIntegerField', [], {'default': '20'}),
            'show_tagcloud': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'tagcloud_levels': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5'}),
            'template': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'url': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'use_internal_cache': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'welcome': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'feedjack.subscriber': {
            'Meta': {'ordering': "('site', 'name', 'feed')", 'unique_together': "(('site', 'feed'),)", 'object_name': 'Subscriber'},
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['feedjack.Feed']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'shortname': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['feedjack.Site']"})
        },
        u'feedjack.tag': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Tag'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['feedjack']