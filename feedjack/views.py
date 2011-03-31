# -*- coding: utf-8 -*-


from django.utils import feedgenerator
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponsePermanentRedirect, Http404
from django.utils.cache import patch_vary_headers
from django.template import Context, RequestContext, loader
from django.views.generic.simple import redirect_to
from django.core.exceptions import ObjectDoesNotExist
from django.utils import simplejson as json
from django.utils.encoding import smart_unicode

from feedjack import models
from feedjack import fjlib
from feedjack import fjcache

import itertools as it, operator as op, functools as ft
from collections import defaultdict
from urlparse import urlparse


def initview(request, response_cache=True):
	'''Retrieves the basic data needed by all feeds (host, feeds, etc)
		Returns a tuple of:
			1. A valid cached response or None
			2. The current site object
			3. The cache key
			4. The subscribers for the site (objects)
			5. The feeds for the site (ids)'''

	http_host, path_info = ( smart_unicode(part.strip('/')) for part in
		[ request.META['HTTP_HOST'],
			request.META.get('REQUEST_URI', request.META.get('PATH_INFO', '/')) ] )
	query_string = request.META['QUERY_STRING']

	url = '{}/{}'.format(http_host, path_info)
	cachekey = u'{}?{}'.format(*it.imap(smart_unicode, (path_info, query_string)))
	hostdict = fjcache.hostcache_get() or dict()

	if url in hostdict:
		site = models.Site.objects.get(pk=hostdict[url])

	else:
		sites = list(models.Site.objects.all())

		if not sites:
			# Somebody is requesting something, but the user
			#  didn't create a site yet. Creating a default one...
			site = models.Site(
				name='Default Feedjack Site/Planet',
				url='www.feedjack.org',
				title='Feedjack Site Title',
				description='Feedjack Site Description.'
					' Please change this in the admin interface.' )
			site.save()

		else:
			# Select the most matching site possible,
			#  preferring "default" when everything else is equal
			results = defaultdict(list)
			for site in sites:
				relevance, site_url = 0, urlparse(site.url)
				if site_url.netloc == http_host: relevance += 10 # host matches
				if path_info.startswith(site_url.path.strip('/')): relevance += 10 # path matches
				if site.default_site: relevance += 5 # marked as "default"
				results[relevance].append((site_url, site))
			for relevance in sorted(results, reverse=True):
				try: site_url, site = results[relevance][0]
				except IndexError: pass
				else: break
			if site_url.netloc != http_host: # redirect to proper site hostname
				# TODO: SERVER_PORT doesn't seem very useful here, but just "http://{}/" is just wrong
				#  ...in a way that it doesn't respect port and protocol
				response = HttpResponsePermanentRedirect(
					'http://{}/{}{}'.format( site_url.netloc, path_info,
						'?{}'.format(query_string) if query_string.strip() else '') )
				return response, None, cachekey

		hostdict[url] = site.id
		fjcache.hostcache_set(hostdict)

	if response_cache:
		response = fjcache.cache_get(site.id, cachekey)
		if response: return response, None, cachekey

	return None, site, cachekey


def redirect(request, url, **kwz):
	'''Simple redirect, taking site prefix into account,
		otherwise similar to redirect_to generic view.'''
	response, site, cachekey = initview(request)
	if response: return response
	return redirect_to(request, url=site.url + url, **kwz)


def blogroll(request, btype):
	'View that handles the generation of blogrolls.'
	response, site, cachekey = initview(request)
	if response: return response

	# for some reason this isn't working:
	#
	#response = render_to_response('feedjack/%s.xml' % btype, \
	#  fjlib.get_extra_content(site, sfeeds_ids))
	#response.mimetype = 'text/xml; charset=utf-8'
	#
	# so we must use this:

	template = loader.get_template('feedjack/{0}.xml'.format(btype))
	ctx = dict()
	fjlib.get_extra_content(site, ctx)
	ctx = Context(ctx)
	response = HttpResponse(template.render(ctx), mimetype='text/xml; charset=utf-8')

	patch_vary_headers(response, ['Host'])
	fjcache.cache_set(site, cachekey, response)
	return response


def foaf(request):
	'View that handles the generation of the FOAF blogroll.'
	return blogroll(request, 'foaf')


def opml(request):
	'View that handles the generation of the OPML blogroll.'
	return blogroll(request, 'opml')


def buildfeed(request, feedclass, tag=None, feed_id=None):
	'View that handles the feeds.'
	# TODO: quite a mess, can't it be handled with a default feed-vews?
	response, site, cachekey = initview(request)
	if response: return response

	feed_title = site.title
	if feed_id:
		try: feed_title = u'{0} - {1}'.format(models.Feed.objects.get(id=feed_id).title, feed_title)
		except ObjectDoesNotExist: raise Http404 # no such feed
	object_list = fjlib.get_page(site, page=1, tag=tag, feed=feed_id).object_list

	feed = feedclass( title=feed_title, link=site.url,
		description=site.description, feed_url=u'{0}/{1}'.format(site.url, '/feed/rss/') )
	for post in object_list:
		feed.add_item(
			title = u'{0}: {1}'.format(post.feed.name, post.title),
			link = post.link,
			description = fjlib.c0ctl_escape(post.content),
			author_email = post.author_email,
			author_name = post.author,
			pubdate = post.date_modified,
			unique_id = post.link,
			categories = [tag.name for tag in post.tags.all()] )
	response = HttpResponse(mimetype=feed.mime_type)

	# per host caching
	patch_vary_headers(response, ['Host'])

	feed.write(response, 'utf-8')
	if site.use_internal_cache: fjcache.cache_set(site, cachekey, response)
	return response


def rssfeed(request, tag=None, feed_id=None):
	'Generates the RSS2 feed.'
	return buildfeed(request, feedgenerator.Rss201rev2Feed, tag, feed_id)


def atomfeed(request, tag=None, feed_id=None):
	'Generates the Atom 1.0 feed.'
	return buildfeed(request, feedgenerator.Atom1Feed, tag, feed_id)


def ajax_store(request, id):
	'Handler for JS requests.'
	raise NotImplementedError
	return HttpResponse(json.dumps(response), content_type='application/json')


def mainview(request, tag=None, feed_id=None):
	'View that handles all page requests.'
	response, site, cachekey = initview(request)
	if not response:
		ctx = fjlib.page_context(request, site, tag, feed_id)
		response = render_to_response(
			u'feedjack/{0}/post_list.html'.format(site.template),
			ctx, context_instance=RequestContext(request) )
		# per host caching, in case the cache middleware is enabled
		patch_vary_headers(response, ['Host'])
		if site.use_internal_cache:
			fjcache.cache_set(site, cachekey, response)
	fj_track_header = request.META.get('HTTP_X_FEEDJACK_TRACKING')
	if fj_track_header: response['X-Feedjack-Tracking'] = fj_track_header
	return response

