# -*- coding: utf-8 -*-

from django.core.cache import (
	cache as cache_default, caches, InvalidCacheBackendError )
from django.conf import settings

import itertools as it, operator as op, functools as ft
from hashlib import md5


T_INTERVAL, T_HOST, T_ITEM, T_META = xrange(4)


class lazy_cache(object):
	def __getattr__(self, k):
		global cache # replaces itself with proper cache on first invocation
		try: cache = caches['feedjack']
		except InvalidCacheBackendError: cache = cache_default
		return getattr(cache, k)

cache = lazy_cache()


def str2md5(key):
	'Returns the md5 hash of a string.'
	return md5(key.encode('utf-8')).hexdigest()

def getkey(stype, site_id=None, key=None):
	'Returns the cache key depending on its type.'
	base = '{0}.feedjack'.format(settings.CACHE_MIDDLEWARE_KEY_PREFIX)
	if stype == T_HOST: return '{0}.hostcache'.format(base)
	elif stype == T_ITEM: return '{0}.{1}.item.{2}'.format(base, site_id, str2md5(key))
	elif stype == T_META: return '{0}.{1}.meta'.format(base, site_id)
	elif stype == T_INTERVAL: return '{0}.interval.{1}'.format(base, str2md5(key))


def hostcache_get():
	'Retrieves the hostcache dictionary.'
	return cache.get(getkey(T_HOST))

def hostcache_set(value):
	'Sets the hostcache dictionary.'
	cache.set(getkey(T_HOST), value)


def feed_interval_key(feed_id, parameters):
	return '{0}__{1}'.format( feed_id,
		':'.join(it.starmap('{0}={1}'.format, sorted(parameters.iteritems()))) )

def feed_interval_get(feed_id, parameters):
	'Get adaptive interval between checks for a feed.'
	val = cache.get(getkey( T_INTERVAL,
		key=feed_interval_key(feed_id, parameters) ))
	return val if isinstance(val, tuple) else (val, None)

def feed_interval_set(feed_id, parameters, interval, interval_ts):
	'Set adaptive interval between checks for a feed.'
	cache.set(getkey( T_INTERVAL,
		key=feed_interval_key(feed_id, parameters) ), (interval, interval_ts))

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
