# -*- coding: utf-8 -*-


from django.utils import feedgenerator
from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404
from django.utils.cache import patch_vary_headers
from django.template import Context, RequestContext, loader
from django.views.generic.simple import redirect_to
from django.core.exceptions import ObjectDoesNotExist

from feedjack import models
from feedjack import fjlib
from feedjack import fjcache


def initview(request):
	'''Retrieves the basic data needed by all feeds (host, feeds, etc)
		Returns a tuple of:
			1. A valid cached response or None
			2. The current site object
			3. The cache key
			4. The subscribers for the site (objects)
			5. The feeds for the site (ids)'''
	site_id, cachekey = fjlib.getcurrentsite( request.META['HTTP_HOST'],
	  request.META.get('REQUEST_URI', request.META.get('PATH_INFO', '/')),
	  request.META['QUERY_STRING'] )
	response = fjcache.cache_get(site_id, cachekey)
	if response: return response, None, cachekey
	site = models.Site.objects.get(pk=site_id)
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
	# TODO: quote a mess, can't it be handled with a default feed-vews?
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


def mainview(request, tag=None, feed_id=None):
	'View that handles all page requests.'
	response, site, cachekey = initview(request)
	if response: return response

	ctx = fjlib.page_context(request, site, tag, feed_id)
	response = render_to_response(
		u'feedjack/{0}/post_list.html'.format(site.template),
		ctx, context_instance=RequestContext(request) )

	# per host caching, in case the cache middleware is enabled
	patch_vary_headers(response, ['Host'])

	if site.use_internal_cache: fjcache.cache_set(site, cachekey, response)
	return response

