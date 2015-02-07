# -*- coding: utf-8 -*-


from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from feedjack import models


class SiteAdmin(admin.ModelAdmin):
	list_display = 'url', 'name'
	filter_vertical = 'links',
admin.site.register(models.Site, SiteAdmin)


class PostProcessorTagInline(admin.TabularInline):
	model = models.PostProcessorTag
	extra = 1

class FeedAdmin(admin.ModelAdmin):
	list_display = 'name', 'feed_url',\
		'title', 'last_modified', 'immutable', 'is_active'
	filter_horizontal = 'filters', 'post_processors'
	fieldsets = (
		(None,
			{'fields': ('feed_url', 'name', 'shortname',
				'immutable', 'skip_errors', 'is_active')}),
		('Filtering',
			{'classes':('collapse',), 'fields': ('filters_logic', 'filters')}),
		(_('Fields updated automatically by Feedjack'),
			{'classes':('collapse',), 'fields':
				('title', 'tagline', 'link', 'etag', 'last_modified', 'last_checked') }) )
	inlines = (PostProcessorTagInline,) # always at the end in stock admin templates
	search_fields = 'feed_url', 'name', 'title'
	list_filter= 'last_modified',
	date_hierarchy = 'last_modified'
	prepopulated_fields = {"shortname": ("name",)}
admin.site.register(models.Feed, FeedAdmin)


class PostAdmin(admin.ModelAdmin):
	list_display = 'title', 'link', 'filtering_result', 'date_created'
	search_fields = 'link', 'title'
	date_hierarchy = 'date_created'
	filter_vertical = 'tags',
	list_filter = 'feed',
admin.site.register(models.Post, PostAdmin)


class SubscriberAdmin(admin.ModelAdmin):
	list_display = 'name', 'site', 'feed'
	search_fields = 'name',
	list_filter = 'site',
admin.site.register(models.Subscriber, SubscriberAdmin)


class FilterBaseAdmin(admin.ModelAdmin):
	list_display = 'name', 'handler_name',\
		'crossref', 'crossref_span', 'handler_description'
	ordering = 'name',
admin.site.register(models.FilterBase, FilterBaseAdmin)


class FilterAdmin(admin.ModelAdmin):
	list_display = '__unicode__', 'parameter'
admin.site.register(models.Filter, FilterAdmin)


class PostProcessorBaseAdmin(admin.ModelAdmin):
	list_display = 'name', 'handler_name'
	ordering = 'name',
admin.site.register(models.PostProcessorBase, PostProcessorBaseAdmin)


class PostProcessorAdmin(admin.ModelAdmin):
	list_display = '__unicode__', 'parameter'
admin.site.register(models.PostProcessor, PostProcessorAdmin)


admin.site.register(models.Link)
