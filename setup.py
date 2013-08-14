#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from finddata import find_package_data
import feedjack
import os, sys

# Error-handling here is to allow package to be built w/o README included
try:
    readme = open(os.path.join(
        os.path.dirname(__file__), 'README.txt' )).read()
except IOError: readme = ''

package_data = find_package_data(where='feedjack', package='feedjack')
package_data.setdefault('', list()).append('README.txt')

setup(
    name = 'Feedjack',
    version = feedjack.__version__,
    author = 'Gustavo Picón, Mike Kazantsev',
    author_email = 'gpicon@gmail.com, mk.fraggod@gmail.com',
    license = 'BSD',
    keywords = [ 'feed', 'aggregator', 'planet',
        'rss', 'atom', 'syndication', 'django', 'feedparser', 'news' ],
    url = feedjack.__url__,

    description = 'Multisite Feed Agregator (Planet) or personal feed reader',
    long_description = readme,

    classifiers = [
        'Development Status :: 4 - Production/Stable',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Natural Language :: German',
        'Natural Language :: Serbian',
        'Natural Language :: Spanish',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2 :: Only',
        'Topic :: Internet',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application' ],

    install_requires = ['feedparser', 'Django >= 1.5'],
    extras_require = {
        'db_migration': ['South'],
        'themes.fern': ['lxml'],
        'themes.plain': ['lxml'] },

    zip_safe = False,
    packages = find_packages(),
    package_data = package_data,
    include_package_data = True,

    entry_points = {
        'console_scripts': ['feedjack_update = feedjack.fjupdate:main'] } )
