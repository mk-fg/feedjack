# -*- coding: utf-8 -*-


from django.conf import settings
from django.db import connection
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from django.utils.encoding import smart_unicode

from feedjack import models
from feedjack import fjcache

import itertools as it, operator as op, functools as ft



def sitefeeds(siteobj):
	""" Returns the active feeds of a site.
	"""
	return siteobj.subscriber_set.filter(is_active=True).select_related()
	#return [subscriber['feed'] \
	#  for subscriber \
	#  in siteobj.subscriber_set.filter(is_active=True).values('feed')]



def getquery(query):
	""" Performs a query and get the results.
	"""
	try:
		conn = connection.cursor()
		conn.execute(query)
		data = conn.fetchall()
		conn.close()
	except: data = list()
	return data



def get_extra_content(site, sfeeds_ids, ctx):
	""" Returns extra data useful to the templates.
	"""

	# get the subscribers' feeds
	if sfeeds_ids:
		basefeeds = models.Feed.objects.filter(id__in=sfeeds_ids)
		try: ctx['feeds'] = basefeeds.order_by('name').select_related()
		except: ctx['feeds'] = list()

		# get the last_checked time
		try:
			ctx['last_modified'] = basefeeds\
				.filter(last_checked__isnull=False)\
				.order_by('-last_checked')\
				.select_related()[0].last_checked.ctime()
		except: ctx['last_modified'] = '??'
	else:
		ctx['feeds'] = list()
		ctx['last_modified'] = '??'
	ctx['site'] = site
	ctx['media_url'] = '{0}feedjack/{1}'.format(settings.MEDIA_URL, site.template)



def get_posts_tags(object_list, sfeeds_obj, user_id, tag_name):
	""" Adds a qtags property in every post object in a page.
	Use "qtags" instead of "tags" in templates to avoid innecesary DB hits.
	"""

	tagd = dict()
	user_obj = None
	tag_obj = None
	tags = models.Tag.objects.extra(
	  select=dict(post_id='{0}.{1}'.format(
			*it.imap( connection.ops.quote_name,
				('feedjack_post_tags', 'post_id') ) )),
	  tables=['feedjack_post_tags'],
	  where=[
		'{0}.{1}={2}.{3}'.format(*it.imap( connection.ops.quote_name,
			('feedjack_tag', 'id', 'feedjack_post_tags', 'tag_id') )),
		'{0}.{1} IN ({2})'.format(
		  connection.ops.quote_name('feedjack_post_tags'),
		  connection.ops.quote_name('post_id'),
		  ', '.join([str(post.id) for post in object_list]) ) ] )

	for tag in tags:
		if tag.post_id not in tagd: tagd[tag.post_id] = list()
		tagd[tag.post_id].append(tag)
		if tag_name and tag.name == tag_name: tag_obj = tag

	subd = dict()
	for sub in sfeeds_obj: subd[sub.feed.id] = sub
	for post in object_list:
		if post.id in tagd: post.qtags = tagd[post.id]
		else: post.qtags = list()
		post.subscriber = subd[post.feed.id]
		if user_id and int(user_id) == post.feed.id: user_obj = post.subscriber

	return user_obj, tag_obj



def getcurrentsite(http_post, path_info, query_string):
	""" Returns the site id and the page cache key based on the request.
	"""

	url = u'http://{0}/{1}'.format(*it.imap( smart_unicode,
		(http_post.rstrip('/'), path_info.lstrip('/')) ))
	pagecachekey = u'{0}?{1}'.format(*it.imap(smart_unicode, (path_info, query_string)))
	hostdict = fjcache.hostcache_get() or dict()

	if url not in hostdict:
		default, ret = None, None
		for site in models.Site.objects.all():
			if url.startswith(site.url):
				ret = site
				break
			if not default or site.default_site: default = site

		if not ret:
			if default: ret = default
			else:
				# Somebody is requesting something, but the user didn't create
				# a site yet. Creating a default one...
				ret = models.Site( name='Default Feedjack Site/Planet',
				  url='www.feedjack.org',
				  title='Feedjack Site Title',
				  description='Feedjack Site Description. '
					'Please change this in the admin interface.' )
				ret.save()

		hostdict[url] = ret.id
		fjcache.hostcache_set(hostdict)

	return hostdict[url], pagecachekey



def get_page(site, sfeeds_ids, page=1, tag=None, user=None):
	""" Returns a paginator object and a requested page from it.
	"""

	if tag:
		try:
			localposts = models.Tag.objects\
				.get(name=tag).post_set.filter(feed__in=sfeeds_ids)
		except: raise Http404
	else:
		localposts = models.Post.objects.filter(feed__in=sfeeds_ids)

	if user:
		try: localposts = localposts.filter(feed=user)
		except: raise Http404

	localposts = localposts.order_by( *(['-date_created']
		if site.order_posts_by == 2 else [] + ['-date_modified', 'feed']) )

	paginator = Paginator(localposts.select_related(), site.posts_per_page)
	try: return paginator.page(page)
	except InvalidPage: raise Http404



def page_context(request, site, tag=None, user_id=None, sfeeds=None):
	""" Returns the context dictionary for a page view.
	"""
	sfeeds_obj, sfeeds_ids = sfeeds

	try: page = int(request.GET.get('page', 1))
	except ValueError: page = 1

	page = get_page(site, sfeeds_ids, page=page, tag=tag, user=user_id)
	if site.show_tagcloud and page.object_list:
		# This will hit the DB once per page instead of once for every post in
		# a page. To take advantage of this the template designer must call
		# the qtags property in every item, instead of the default tags
		# property.
		user_obj, tag_obj = get_posts_tags(page.object_list, sfeeds_obj, user_id, tag)
	else:
		tag_obj = None
		user_obj = models.Subscriber.objects\
			.get(site=site, feed=user_id) if user_id else None

	ctx = dict(
		object_list = page.object_list,
		is_paginated = page.paginator.num_pages > 1,
		results_per_page = site.posts_per_page,
		has_next = page.has_next(),
		has_previous = page.has_previous(),
		page = page.number,
		next = page.number + 1,
		previous = page.number - 1,
		pages = page.paginator.num_pages,
		hits = page.paginator.count )

	get_extra_content(site, sfeeds_ids, ctx)
	from feedjack import fjcloud
	ctx['tagcloud'] = fjcloud.getcloud(site, user_id)
	ctx['user_id'] = user_id
	ctx['user'] = user_obj
	ctx['tag'] = tag_obj
	ctx['subscribers'] = sfeeds_obj
	return ctx



