# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'FilterBase.crossref_rebuild'
        db.add_column('feedjack_filterbase', 'crossref_rebuild',
                      self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=0),
                      keep_default=False)

        # Adding field 'FilterBase.crossref_timeline'
        db.add_column('feedjack_filterbase', 'crossref_timeline',
                      self.gf('django.db.models.fields.PositiveSmallIntegerField')(default=0),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'FilterBase.crossref_rebuild'
        db.delete_column('feedjack_filterbase', 'crossref_rebuild')

        # Deleting field 'FilterBase.crossref_timeline'
        db.delete_column('feedjack_filterbase', 'crossref_timeline')


    models = {
        'feedjack.feed': {
            'Meta': {'ordering': "('name', 'feed_url')", 'object_name': 'Feed'},
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'feed_url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '200'}),
            'filters': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'feeds'", 'blank': 'True', 'to': "orm['feedjack.Filter']"}),
            'filters_logic': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'immutable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_checked': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'link': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'shortname': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'tagline': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'})
        },
        'feedjack.filter': {
            'Meta': {'object_name': 'Filter'},
            'base': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'filters'", 'to': "orm['feedjack.FilterBase']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parameter': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'})
        },
        'feedjack.filterbase': {
            'Meta': {'object_name': 'FilterBase'},
            'crossref': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'crossref_rebuild': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'crossref_span': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'crossref_timeline': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            'handler_name': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'})
        },
        'feedjack.filterresult': {
            'Meta': {'object_name': 'FilterResult'},
            'filter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['feedjack.Filter']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'filtering_results'", 'to': "orm['feedjack.Post']"}),
            'result': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'feedjack.link': {
            'Meta': {'object_name': 'Link'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'feedjack.post': {
            'Meta': {'ordering': "('-date_modified',)", 'unique_together': "(('feed', 'guid'),)", 'object_name': 'Post'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'author_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'comments': ('django.db.models.fields.URLField', [], {'max_length': '511', 'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['feedjack.Feed']"}),
            'filtering_result': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'guid': ('django.db.models.fields.CharField', [], {'max_length': '511', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.URLField', [], {'max_length': '511'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['feedjack.Tag']", 'symmetrical': 'False'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '511'})
        },
        'feedjack.site': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Site'},
            'cache_duration': ('django.db.models.fields.PositiveIntegerField', [], {'default': '86400'}),
            'default_site': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'greets': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'links': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['feedjack.Link']", 'null': 'True', 'blank': 'True'}),
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
        'feedjack.subscriber': {
            'Meta': {'ordering': "('site', 'name', 'feed')", 'unique_together': "(('site', 'feed'),)", 'object_name': 'Subscriber'},
            'feed': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['feedjack.Feed']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'shortname': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['feedjack.Site']"})
        },
        'feedjack.tag': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '127'})
        }
    }

    complete_apps = ['feedjack']