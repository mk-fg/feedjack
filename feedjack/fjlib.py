# -*- coding: utf-8 -*-


from django.conf import settings
from django.db import connection
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from django.utils.encoding import smart_unicode, force_unicode

from feedjack import models
from feedjack import fjcache

import itertools as it, operator as op, functools as ft
from datetime import datetime, timedelta
from urllib import quote


try:
	from lxml.html import fromstring as lxml_fromstring, tostring as lxml_tostring
	from lxml.html.clean import Cleaner as lxml_Cleaner
	from lxml.etree import XMLSyntaxError as lxml_SyntaxError

except ImportError:
	# at least strip c0 control codes, which are quite common in broken html
	_xml_c0ctl_chars = bytearray(
		set(it.imap(chr, xrange(32)))\
			.difference('\x09\x0a\x0d').union('\x7f'))
	_xml_c0ctl_trans = dict(it.izip(
		_xml_c0ctl_chars, u'_'*len(_xml_c0ctl_chars) ))

	def html_cleaner(string):
		'Produces template-safe valid xml-escaped string.'
		return force_unicode(string).translate(_xml_c0ctl_trans)

else:
	def lxml_soup(string):
		'Safe processing of any tag soup (which is a norm on the internets).'
		try: doc = lxml_fromstring(force_unicode(string))
		except lxml_SyntaxError: # last resort for "tag soup"
			from lxml.html.soupparser import fromstring as soup
			doc = soup(force_unicode(string))
		return doc

	def html_cleaner(string):
		'str -> str, like lxml.html.clean.clean_html, but removing styles as well.'
		doc = lxml_soup(string)
		lxml_Cleaner(style=True)(doc)
		return lxml_tostring(doc)


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
	mod, chk = op.itemgetter('modified', 'checked')(feeds.timestamps)
	chk = chk or datetime(1970, 1, 1)
	ctx['last_modified'], ctx['last_checked'] = mod or chk, chk
	ctx['site'] = site
	ctx['media_url'] = '{0}feedjack/{1}'.format(settings.MEDIA_URL, site.template)


def get_posts_tags(subscribers, object_list, feed, tag_name):
	'''Adds a qtags property in every post object in a page.
		Use "qtags" instead of "tags" in templates to avoid unnecesary DB hits.'''

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
		if feed == post.feed: user_obj = post.subscriber

	return user_obj, tag_obj


def get_page(site, page=1, **criterias):
	'Returns a paginator object and a requested page from it.'

	if 'since' in criterias:
		since = criterias['since']
		since_formats = '%Y-%m-%d', '%Y-%m-%d %H:%M', '%d.%m.%Y'
		since_days = {
			'yesterday': 1, 'week': 7,
			'10_days': 10, '30_days': 30 }.get(since)
		if since_days:
			since = (datetime.today() - timedelta(since_days)).strftime(since_formats[0])
		for since_format in since_formats:
			try: since = datetime.strptime(since, since_format)
			except ValueError: pass
			else: break
		else: raise Http404 # invalid format
		criterias['since'] = since
	order_force = criterias.pop('asc', None)

	posts = models.Post.objects.filtered(site, **criterias)\
		.sorted(site.order_posts_by, force=order_force).select_related()

	paginator = Paginator(posts, site.posts_per_page)
	try: return paginator.page(page)
	except InvalidPage: raise Http404


def page_context(request, site, **criterias):
	'Returns the context dictionary for a page view.'
	try: page = int(request.GET.get('page', 1))
	except ValueError: page = 1

	feed, tag = criterias.get('feed'), criterias.get('tag')
	if feed:
		try: feed = models.Feed.objects.get(id=feed)
		except ObjectDoesNotExist: raise Http404

	page = get_page(site, page=page, **criterias)
	subscribers = site.active_subscribers

	if site.show_tagcloud and page.object_list:
		from feedjack import fjcloud
		# This will hit the DB once per page instead of once for every post in
		# a page. To take advantage of this the template designer must call
		# the qtags property in every item, instead of the default tags
		# property.
		user_obj, tag_obj = get_posts_tags(
			subscribers, page.object_list, feed, tag )
		tag_cloud = fjcloud.getcloud(site, feed.id)
	else:
		tag_obj, tag_cloud = None, tuple()
		try:
			user_obj = models.Subscriber.objects\
				.get(site=site, feed=feed) if feed else None
		except ObjectDoesNotExist: raise Http404

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
		hits = page.paginator.count,
		last_modified = max(it.imap(
				op.attrgetter('date_updated'), page.object_list ))\
			if len(page.object_list) else datetime(1970, 1, 1) )

	get_extra_content(site, ctx)
	ctx['tagcloud'] = tag_cloud
	ctx['tag'] = tag_obj
	ctx['subscribers'] = subscribers

	# New
	ctx['feed'] = feed
	ctx['url_suffix'] = ''.join((
		'/feed/{0}'.format(feed.id) if feed else '',
		'/tag/{0}'.format(quote(tag)) if tag else '' ))

	# Deprecated
	ctx['user_id'] = feed and feed.id # totally misnamed and inconsistent with user_obj
	ctx['user'] = user_obj

	return ctx
