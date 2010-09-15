# -*- coding: utf-8 -*-


from django.conf import settings
from django.db import connection
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from django.utils.encoding import smart_unicode

from feedjack import models
from feedjack import fjcache

import itertools as it, operator as op, functools as ft
from urllib import urlencode



def getquery(query):
	'Performs a query and get the results.'
	try:
		conn = connection.cursor()
		conn.execute(query)
		data = conn.fetchall()
		conn.close()
	except: data = list()
	return data



def get_extra_content(site, ctx):
	'Returns extra data useful to the templates.'
	# get the subscribers' feeds
	feeds = site.active_feeds
	ctx['feeds'] = feeds.order_by('name')
	# get the last_modified/checked time
	mod,chk = op.itemgetter('modified', 'checked')(feeds.timestamps)
	chk = chk.ctime() if chk else '??'
	mod = mod.ctime() if mod else chk
	ctx['last_modified'], ctx['last_checked'] = mod, chk
	ctx['site'] = site
	ctx['media_url'] = '{0}feedjack/{1}'.format(settings.MEDIA_URL, site.template)



def get_posts_tags(subscribers, object_list, feed_id, tag_name):
	'''Adds a qtags property in every post object in a page.
		Use "qtags" instead of "tags" in templates to avoid innecesary DB hits.'''

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
	for sub in subscribers: subd[sub.feed.id] = sub
	for post in object_list:
		if post.id in tagd: post.qtags = tagd[post.id]
		else: post.qtags = list()
		post.subscriber = subd[post.feed.id]
		if feed_id and feed_id == post.feed.id: user_obj = post.subscriber

	return user_obj, tag_obj



def getcurrentsite(http_post, path_info, query_string):
	'Returns the site id and the page cache key based on the request.'

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



def get_page(site, page=1, tag=None, feed=None):
	'Returns a paginator object and a requested page from it.'

	posts = models.Post.objects.filtered(site, feed=feed, tag=tag)\
		.sorted(site.order_posts_by).select_related()

	paginator = Paginator(posts, site.posts_per_page)
	try: return paginator.page(page)
	except InvalidPage: raise Http404



def page_context(request, site, tag=None, feed_id=None):
	'Returns the context dictionary for a page view.'
	try: page = int(request.GET.get('page', 1))
	except ValueError: page = 1

	page = get_page(site, page=page, tag=tag, feed=feed_id)
	subscribers = site.active_subscribers

	if site.show_tagcloud and page.object_list:
		from feedjack import fjcloud
		# This will hit the DB once per page instead of once for every post in
		# a page. To take advantage of this the template designer must call
		# the qtags property in every item, instead of the default tags
		# property.
		user_obj, tag_obj = get_posts_tags(subscribers, page.object_list, feed_id, tag)
		tag_cloud = fjcloud.getcloud(site, feed_id)
	else:
		tag_obj, tag_cloud = None, tuple()
		user_obj = models.Subscriber.objects\
			.get(site=site, feed=feed_id) if feed_id else None

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

	get_extra_content(site, ctx)
	ctx['tagcloud'] = tag_cloud
	ctx['tag'] = tag_obj
	ctx['subscribers'] = subscribers

	# New
	ctx['feed'] = models.Feed.objects.get(id=feed_id) if feed_id else None
	ctx['url_suffix'] = ''.join((
		'/feed/{0}'.format(feed_id) if feed_id else '',
		'/tag/{0}'.format(urlencode(tag)) if tag else '' ))

	# Deprecated
	ctx['user_id'] = feed_id # totally misnamed and inconsistent with user_obj
	ctx['user'] = user_obj

	return ctx

