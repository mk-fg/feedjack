#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from finddata import find_package_data # XXX: drop this
import os, sys, runpy

pkg_root = os.path.dirname(__file__)
feedjack = type( 'ModuleVars', (object,),
	runpy.run_path(os.path.join(pkg_root, 'feedjack', '__init__.py')) )

package_data = find_package_data(where='feedjack', package='feedjack')

# Error-handling here is to allow package to be built w/o README included
try: readme = open(os.path.join(pkg_root, 'README.txt')).read()
except IOError: readme = ''
else: package_data.setdefault('', list()).append('README.txt')

setup(

	name='Feedjack',
	version=feedjack.__version__,
	author='Gustavo Picón, Mike Kazantsev',
	author_email='mk.fraggod@gmail.com',
	license='BSD',
	keywords=[
		'feed', 'aggregator', 'reader', 'planet',
		'syndication', 'subscribe', 'news', 'web',
		'rss', 'atom', 'rdf', 'opml', 'django', 'feedparser' ],

	url=feedjack.__url__,

	description='Multisite Feed Agregator (Planet) or personal feed reader',
	long_description=readme,

	classifiers=[
		'Development Status :: 5 - Production/Stable',
		'Environment :: Console',
		'Environment :: Web Environment',
		'Framework :: Django',
		'Intended Audience :: End Users/Desktop',
		'Intended Audience :: Information Technology',
		'License :: OSI Approved :: BSD License',
		'Natural Language :: English',
		'Operating System :: POSIX',
		'Operating System :: Unix',
		'Programming Language :: Python',
		'Programming Language :: Python :: 2.7',
		'Programming Language :: Python :: 2 :: Only',
		'Topic :: Internet',
		'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
		'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
		'Topic :: Software Development :: Libraries :: Python Modules' ],

	install_requires=['feedparser', 'Django >= 1.7'],
	extras_require={
		'old_db_migration': ['South'],
		'themes.fern': ['lxml'],
		'themes.plain': ['lxml'] },

	zip_safe=False,
	packages=find_packages(),
	package_data=package_data,
	include_package_data=True,

	entry_points={
		'console_scripts': ['feedjack_update=feedjack.fjupdate:main'] } )
