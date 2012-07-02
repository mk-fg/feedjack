# -*- coding: utf-8 -*-

from django.core.cache import cache, get_cache
from django.conf import settings

import itertools as it, operator as op, functools as ft
from hashlib import md5


try:
	ajax_cache = settings.FEEDJACK_CACHE
	settings.CACHES # django 1.3
except AttributeError:
	try: ajax_cache = 'persistent' if 'persistent' in settings.CACHES else 'default'
	except AttributeError: ajax_cache = cache
	else: ajax_cache = get_cache(ajax_cache)
else: ajax_cache = get_cache(ajax_cache)


T_INTERVAL, T_HOST, T_ITEM, T_META = xrange(4)


def str2md5(key):
	'Returns the md5 hash of a string.'
	return md5(key.encode('utf-8')).hexdigest()

def getkey(stype, site_id=None, key=None):
	'Returns the cache key depending on its type.'
	base = '{}.feedjack'.format(settings.CACHE_MIDDLEWARE_KEY_PREFIX)
	if stype == T_HOST: return '{}.hostcache'.format(base)
	elif stype == T_ITEM: return '{}.{}.item.{}'.format(base, site_id, str2md5(key))
	elif stype == T_META: return '{}.{}.meta'.format(base, site_id)
	elif stype == T_INTERVAL: return '{}.interval.{}'.format(base, str2md5(key))


def hostcache_get():
	'Retrieves the hostcache dictionary.'
	return cache.get(getkey(T_HOST))

def hostcache_set(value):
	'Sets the hostcache dictionary.'
	cache.set(getkey(T_HOST), value)


def feed_interval_key(feed_id, parameters):
	return '{}__{}'.format( feed_id,
		':'.join(it.starmap('{}={}'.format, sorted(parameters.viewitems()))) )

def feed_interval_get(feed_id, parameters):
	'Get adaptive interval between checks for a feed.'
	return cache.get(getkey( T_INTERVAL,
		key=feed_interval_key(feed_id, parameters) ))

def feed_interval_set(feed_id, parameters, value):
	'Set adaptive interval between checks for a feed.'
	cache.set(getkey( T_INTERVAL,
		key=feed_interval_key(feed_id, parameters) ), value)

def feed_interval_delete(feed_id, parameters):
	'Invalidate cached adaptive interval value.'
	cache.delete(getkey( T_INTERVAL,
		key=feed_interval_key(feed_id, parameters) ))


def cache_get(site_id, key):
	'Retrieves cache data from a site.'
	return cache.get(getkey(T_ITEM, site_id, key))

def cache_set(site, key, data):
	'''Sets cache data for a site.
		All keys related to a site are stored in a meta key. This key is per-site.'''
	tkey = getkey(T_ITEM, site.id, key)
	mkey = getkey(T_META, site.id)
	tmp = cache.get(mkey)
	longdur = 365*24*60*60
	if not tmp:
		tmp = [tkey]
		cache.set(mkey, [tkey], longdur)
	elif tkey not in tmp:
		tmp.append(tkey)
		cache.set(mkey, tmp, longdur)
	cache.set(tkey, data, site.cache_duration)

def cache_delsite(site_id):
	'Removes all cache data from a site.'
	mkey = getkey(T_META, site_id)
	tmp = cache.get(mkey)
	if not tmp:
		return
	for tkey in tmp:
		cache.delete(tkey)
	cache.delete(mkey)
