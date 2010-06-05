# -*- coding: utf-8 -*-

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_unicode

from feedjack import fjcache, filters

import itertools as it, operator as op, functools as ft


SITE_ORDERBY_CHOICES = (
	(1, _('Date published.')),
	(2, _('Date the post was first obtained.')) )



class Link(models.Model):
	name = models.CharField(_('name'), max_length=100, unique=True)
	link = models.URLField(_('link'), verify_exists=True)

	class Meta:
		verbose_name = _('link')
		verbose_name_plural = _('links')

	class Admin: pass

	def __unicode__(self): return u'%s (%s)' % (self.name, self.link)



class Site(models.Model):
	name = models.CharField(_('name'), max_length=100)
	url = models.CharField(_('url'),
	  max_length=100,
	  unique=True,
	  help_text=u'%s: %s, %s' % (smart_unicode(_('Example')),
		u'http://www.planetexample.com',
		u'http://www.planetexample.com:8000/foo'))
	title = models.CharField(_('title'), max_length=200)
	description = models.TextField(_('description'))
	welcome = models.TextField(_('welcome'), null=True, blank=True)
	greets = models.TextField(_('greets'), null=True, blank=True)

	default_site = models.BooleanField(_('default site'), default=False)
	posts_per_page = models.IntegerField(_('posts per page'), default=20)
	order_posts_by = models.IntegerField(_('order posts by'), default=1,
		choices=SITE_ORDERBY_CHOICES)
	tagcloud_levels = models.IntegerField(_('tagcloud level'), default=5)
	show_tagcloud = models.BooleanField(_('show tagcloud'), default=True)

	use_internal_cache = models.BooleanField(_('use internal cache'), default=True)
	cache_duration = models.IntegerField(_('cache duration'), default=60*60*24,
		help_text=_('Duration in seconds of the cached pages and data.') )

	links = models.ManyToManyField(Link, verbose_name=_('links'),
	  null=True, blank=True)
	template = models.CharField(_('template'), max_length=100, null=True,
	  blank=True,
	  help_text=_('This template must be a directory in your feedjack '
		'templates directory. Leave blank to use the default template.') )

	class Meta:
		verbose_name = _('site')
		verbose_name_plural = _('sites')
		ordering = ('name',)

	def __unicode__(self): return self.name

	def save(self):
		if not self.template:
			self.template = 'default'
		# there must be only ONE default site
		defs = Site.objects.filter(default_site=True)
		if not defs:
			self.default_site = True
		elif self.default_site:
			for tdef in defs:
				if tdef.id != self.id:
					tdef.default_site = False
					tdef.save()
		self.url = self.url.rstrip('/')
		fjcache.hostcache_set({})
		super(Site, self).save()



FILTERS_MODULE = 'feedjack.filters'

class FilterBase(models.Model): # I had to resist the urge to call it FilterClass or FilterModel

	name = models.CharField(max_length=64, unique=True)
	handler_name = models.CharField( max_length=256, blank=True,
		help_text=( 'Processing function as and import-name, like'
			' "myapp.filters.some_filter" or just a name if its a built-in filter'
			' (contained in {0}), latter is implied if this field is omitted.<br />'
			' Should accept Post object and optional (or not) parameter (derived from'
			' actual Filter field) and return boolean value, indicating whether post'
			' should be displayed or not.'.format(FILTERS_MODULE) ) )

	@property
	def handler(self):
		'Handler function'
		filter_func = getattr(filters, self.handler_name or self.name, None)
		if filter_func is None:
			if '.' not in self.handler_name:
				raise ImportError('Filter function not found: {0}'.format(self.handler_name))
			filter_module, filter_func = it.imap(str, self.handler_name.rsplit('.', 1))
			filter_func = getattr(__import__(filter_module, fromlist=[filter_func]), filter_func)
		return filter_func

	def __unicode__(self): return u'{0.name} ({0.handler_name})'.format(self)


class Filter(models.Model):
	base = models.ForeignKey('FilterBase', related_name='filters')
	# feeds (reverse m2m relation from Feed)
	parameter = models.CharField( max_length=512, blank=True, null=True,
		help_text='Parameter keyword to pass to a filter function.<br />Allows to define generic'
			' filtering alghorithms in code (like "regex_filter") and actual filters in db itself'
			' (specifying regex to filter by).<br />Null value would mean that "parameter" keyword'
			' wont be passed to handler at all.' )

	@property
	def handler(self):
		'Parametrized handler function'
		return ft.partial(self.base.handler, parameter=self.parameter)\
			if self.parameter is not None else self.base.handler

	@property
	def shortname(self):
		return u'{0.base.name}{1}'.format( self,
				u' ({0})'.format(self.parameter) if self.parameter else '' )
	def __unicode__(self):
		binding = u', '.join(it.imap(op.attrgetter('shortname'), self.feeds.all()))
		return u'{0} (used on {1})'.format(self.shortname, binding)\
			if binding else u'{0} (not used for any feed)'.format(self.shortname)


class FilterResult(models.Model):
	filter = models.ForeignKey('Filter')
	post = models.ForeignKey('Post', related_name='filtering_results')
	result = models.BooleanField()
	timestamp = models.DateTimeField(auto_now=True)

	def __unicode__(self):
		return u'{0.result} ("{0.post}", {0.filter.shortname} on'\
			u' {0.post.feed.shortname}, {0.timestamp})'.format(self)



class Feed(models.Model):
	feed_url = models.URLField(_('feed url'), unique=True)

	name = models.CharField(_('name'), max_length=100)
	shortname = models.CharField(_('shortname'), max_length=50)
	immutable = models.BooleanField( _('immutable'), default=False,
		help_text=_('Do not update posts that were already fetched.') )
	is_active = models.BooleanField( _('is active'), default=True,
		help_text=_('If disabled, this feed will not be further updated.') )

	title = models.CharField(_('title'), max_length=200, blank=True)
	tagline = models.TextField(_('tagline'), blank=True)
	link = models.URLField(_('link'), blank=True)

	filters = models.ManyToManyField('Filter', related_name='feeds')

	# http://feedparser.org/docs/http-etag.html
	etag = models.CharField(_('etag'), max_length=50, blank=True)
	last_modified = models.DateTimeField(_('last modified'), null=True, blank=True)
	last_checked = models.DateTimeField(_('last checked'), null=True, blank=True)

	class Meta:
		verbose_name = _('feed')
		verbose_name_plural = _('feeds')
		ordering = ('name', 'feed_url',)

	def __unicode__(self):
		return u'{0} ({1})'.format( self.name, self.feed_url
			if len(self.feed_url) <= 50 else '{0}...'.format(self.feed_url[:47]) )



class Tag(models.Model):
	name = models.CharField(_('name'), max_length=50, unique=True)

	class Meta:
		verbose_name = _('tag')
		verbose_name_plural = _('tags')
		ordering = ('name',)

	def __unicode__(self): return self.name



class Post(models.Model):
	feed = models.ForeignKey(Feed, verbose_name=_('feed'), null=False, blank=False)
	title = models.CharField(_('title'), max_length=511)
	link = models.URLField(_('link'), max_length=511)
	content = models.TextField(_('content'), blank=True)
	date_modified = models.DateTimeField(_('date modified'), null=True, blank=True)
	guid = models.CharField(_('guid'), max_length=511, db_index=True)
	author = models.CharField(_('author'), max_length=255, blank=True)
	author_email = models.EmailField(_('author email'), blank=True)
	comments = models.URLField(_('comments'), max_length=511, blank=True)
	tags = models.ManyToManyField(Tag, verbose_name=_('tags'))
	date_created = models.DateField(_('date created'), auto_now_add=True)
	# filtering_results (reverse m2m relation from FilterResult)

	class Meta:
		verbose_name = _('post')
		verbose_name_plural = _('posts')
		ordering = ('-date_modified',)
		unique_together = (('feed', 'guid'),)

	def _filtering_result(self, by_or):
		return self.filtering_results.filter(
			result=bool(by_or) )[0].result # find at least one failed / passed test

	def filtering_result(self, by_or=False):
		'Check that bound FilterResult objects are consistent with current feed filters.'
		'''Check/return if post passes all / at_least_one (by_or parameter) filter(s).
			Filters are evaluated on if-necessary basis'''
		filters, results = self.feed.filters.all(), self.filtering_results.all()
		filters, results_filters = it.imap(set, (filters, it.imap(op.attrgetter('filter'), results)))

		# Check if conclusion can already be made, based on cached results
		if results_filters.issubset(filters):
			# If at least one failed/passed test is already there, and/or outcome is defined
			try: return self._filtering_result(by_or)
			except IndexError: # inconclusive until results are consistent
				if filters == results_filters: return not by_or

		# Consistency check / update
		if filters != results_filters:
			# Drop obsolete (removed, unbound from feed) filters' results (WILL corrupt outcome)
			self.filtering_results.filter(filter__in=results_filters.difference(filters)).delete()
			# One more try, now that results are only from feed filters' subset
			try: return self._filtering_result(by_or)
			except IndexError: pass
			# Check if any filter-results are not cached yet, create them (perform actual filtering)
			for filter_obj in filters.difference(results_filters):
				filter_op = FilterResult(filter=filter_obj, post=self, result=filter_obj.handler(self))
				filter_op.save()
				if filter_op.result == by_or: return by_or # return as soon as first passed / failed

		# Final result
		try: return self._filtering_result(by_or)
		except IndexError: return not by_or # none passed / none failed

	def __unicode__(self): return self.title
	def get_absolute_url(self): return self.link



class Subscriber(models.Model):
	site = models.ForeignKey(Site, verbose_name=_('site') )
	feed = models.ForeignKey(Feed, verbose_name=_('feed') )

	name = models.CharField(_('name'), max_length=100, null=True, blank=True,
		help_text=_('Keep blank to use the Feed\'s original name.') )
	shortname = models.CharField(_('shortname'), max_length=50, null=True,
	  blank=True,
	  help_text=_('Keep blank to use the Feed\'s original shortname.') )
	is_active = models.BooleanField(_('is active'), default=True,
		help_text=_('If disabled, this subscriber will not appear in the site or '
		'in the site\'s feed.') )

	class Meta:
		verbose_name = _('subscriber')
		verbose_name_plural = _('subscribers')
		ordering = ('site', 'name', 'feed')
		unique_together = (('site', 'feed'),)

	def __unicode__(self): return u'%s in %s' % (self.feed, self.site)

	def get_cloud(self):
		from feedjack import fjcloud
		return fjcloud.getcloud(self.site, self.feed.id)

	def save(self):
		if not self.name: self.name = self.feed.name
		if not self.shortname: self.shortname = self.feed.shortname
		super(Subscriber, self).save()
