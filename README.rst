
Feedjack
========

Feedjack is a feed aggregator, allowing to aggregate multiple rss/atom feeds
into multiple "sites", accessible as regular web pages, somewhat like "planet"
aggregator does, but better.

It is intended to be useful as a multisite feed aggregator (planet, e.g.
"planet python"), as well as a personal feed reader app with web interface. It's
also a Django app, which can be integrated into larger Django projects.

This project is a fork of the original Feedjack project by Gustavo Picón, which
seem to be abandoned for a while now. See CHANGES file for more details on what
happened here over time.



Installation
------------


Python module (Django app)
``````````````````````````

This feedjack fork is a regular package for Python 2.7 (not 3.X).

Best way to install it (from PyPI_) would be to use pip_::

  % pip install Feedjack

If you don't have it, use::

  % easy_install pip
  % pip install Feedjack

Alternatively (see also `pip2014.com`_ and `pip install guide`_)::

  % curl https://raw.github.com/pypa/pip/master/contrib/get-pip.py | python
  % pip install Feedjack

Current-git version can be installed like this::

  % pip install 'git+https://github.com/mk-fg/feedjack.git#egg=Feedjack'

All of these will automatically fetch and install 'feedjack' Django app to a
configured python site-path, along with all the required dependencies.

Another way of installing from a git chechout would be running
``python setup.py install`` in the dir.

Note that to install stuff in system-wide PATH and site-packages, elevated
privileges are often required. Use "install --user", `~/.pydistutils.cfg`_ or
virtualenv_ to do unprivileged installs into custom paths.

.. _PyPI: https://pypi.python.org/pypi/Feedjack/
.. _pip: http://pip-installer.org/
.. _pip2014.com: http://pip2014.com/
.. _pip install guide: http://www.pip-installer.org/en/latest/installing.html
.. _~/.pydistutils.cfg: http://docs.python.org/install/index.html#distutils-configuration-files
.. _virtualenv: http://pypi.python.org/pypi/virtualenv


Django project
``````````````

If you are not familiar with Django framework and how Django apps are deployed,
please see this short tutorial, which contains all the steps necessary to
initialize "django project" directory, also explaining what's in there:

  https://docs.djangoproject.com/en/stable/intro/tutorial01/#creating-a-project

Django project - at it's minimum - is just a few `configuration files`_,
specifying which database to use, and which "apps" should handle which URLs.

Feedjack can only be deployed as an "app" in such project, so it either has to
be created, or app can be enabled in any existing one.

.. _configuration files: https://docs.djangoproject.com/en/dev/topics/settings/


Enabling app in a Django project
````````````````````````````````

* First of all, 'feedjack' app must be enabled in settings.py under `INSTALLED_APPS`_.

* Running ``./manage.py migrate`` (`"migrate" command`_, supersedes "syncdb" in
  Django-1.7+) from the command line should then populate database (whichever is
  configured in the same file) with feedjack-specific schema.

* Feedjack "static files" directory should be setup to be reachable under
  configured `STATIC_URL`_ (under "STATIC_URL/feedjack/", to be precise).

  This can be done automatically by using `django.contrib.staticfiles`_ app,
  that `will copy/link static files`_ with ``./manage.py collectstatic``
  command.

  It can also be done manually. For instance, if your STATIC_URL resolves to
  "/var/www/htdocs", and Feedjack was installed to
  "/usr/lib/python2.7/site-packages/feedjack",
  symlinking dir from there should probably do the trick::

    % ln -s /usr/lib/python2.7/site-packages/feedjack/static/feedjack /var/www/htdocs/

* Be sure to enable/add/uncomment/check "django.contrib.admin" app (`Django
  admin interface`_) as well, since it's the most convenient and supported way
  to configure and control feedjack.

  "migrate" operation (same as after enabling feedjack itself) might be
  necessary after that.

  Other ways to configure and control feedjack app after installation
  are:

  * Command-line tools.

    These are accessible via django-admin.py (or "./manage.py" wrapper) - see
    --help output for reference on all the supported commands there.

    Some (e.g. "feedjack_update") can also be installed as python
    console_scripts entry points.

  * Manipulate models from the python code or ``./manage.py shell`` directly,
    which might be desirable for some kind of migration or automated
    configuration.

* Add an entry for feedjack.urls in your Django "urls.py" file, so it'd look
  like this (with admin interface also enabled on "/admin/")::

    urlpatterns = patterns( '',
      (r'^admin/', include('django.contrib.admin.urls')),
      (r'', include('feedjack.urls')) )

  (of course, less trivial Django configurations should probably have way more
  entries there)

After all that, it might be worth checking out "/admin" interface (if
django.contrib.admin app was enabled) to create a feedjack site, otherwise
sample default site will be created upon first request.

Be sure to check out deployment section of Django docs and a checklist there
before making project accessible from the internet:

  | https://docs.djangoproject.com/en/stable/howto/deployment/
  | https://docs.djangoproject.com/en/stable/howto/deployment/checklist/

See also "Configuration" section below.

.. _INSTALLED_APPS: http://docs.djangoproject.com/en/stable/ref/settings/#installed-apps
.. _"migrate" command: http://docs.djangoproject.com/en/stable/ref/django-admin/#migrate-app-label-migrationname
.. _STATIC_URL: http://docs.djangoproject.com/en/dev/ref/settings/#static-url
.. _django.contrib.staticfiles: https://docs.djangoproject.com/en/stable/ref/contrib/staticfiles/
.. _will copy/link static files: https://docs.djangoproject.com/en/dev/howto/static-files/
.. _Django admin interface: https://docs.djangoproject.com/en/dev/ref/contrib/admin/


Requirements
````````````

* `Python 2.7 <http://python.org/>`__ (not 3.X)

* `Django 1.8+ <http://djangoproject.com>`__

* `feedparser 4.1+ <https://code.google.com/p/feedparser/>`__

* (optional, recommended) `pytz <http://pythonhosted.org/pytz/>`__ -
  required by Django in some cases, facilitates correct handling/interpretation
  of timezones.

* (optional) `lxml <http://lxml.de>`__ - used for html mangling in some themes
  (fern, plain) processing of more free-form timestamps on feeds, if feedparser
  can't handle these for whatever reason.

* (optional, only for updating from older Feedjack/Django versions)
  `South <http://south.aeracode.org>`__


Updating from older versions
````````````````````````````

The only non-backwards-compatible changes should be in the database schema,
thus requiring migration, but it's much easier (automatic even) than it sounds.

Feedjack didn't have any automatic db migration features in the past, then used
South module (in this fork), and now uses stock `Django database migration
features`_ (which only work with Django-1.7+).

* To upgrade older installations where there were no migrations in use at all,
  install and enable South app, backup "feedjack/migrations" (which now contains
  Django-native migration info), then rename "feedjack/migrations.south" dir to
  "feedjack/migrations".

  There is no automated way to determine schema version in current database, so
  use South's ``./manage.py migrate --list`` command to list migrations, find
  the one that matches current db state and run e.g. ``./manage.py migrate
  feedjack 0013 --fake`` to make South aware of it.

  In case of pre-fork Feedjack versions (0.9.16 and below), this would be very
  first (0001) schema version.

* To upgrade from South to Django-1.7+ native migrations, temporarily restore
  "migrations.south" dir to "migrations", as outlined above, run
  ``./manage.py migrate`` to make sure all South migrations were applied, then
  restore Django's "migrations" directory, replace "south" with
  "django.db.migrations" in INSTALLED_APPS and run ``./manage.py migrate``
  again to apply all these.

  See also `Upgrading from South`_ section in Django docs on migrations.

.. _Django database migration features: https://docs.djangoproject.com/en/1.7/topics/migrations/
.. _Upgrading from South: https://docs.djangoproject.com/en/1.7/topics/migrations/#upgrading-from-south



Configuration
-------------

The first thing you want to do is to add a Site.

To do this, open Django admin interface and create your first planet.  You must
use a valid address in the URL field, since it will be used to identify the
current planet when there are multiple planets in the same instance and to
generate all the links.

Then you should add Subscribers to your first planet. A Subscriber is a relation
between a Feed and a Site, so when you add your first Subscriber, you should
also add your first Feed by clicking in the “+” button at the right of the Feed
combobox.

Feedjack is designed to use `Django cache system`_ to store database-intensive
data like pages of posts and tagclouds, so it is highly recomended to
`configure CACHES`_ in django settings (memcached, db, files, etc). Feedjack
will try to use cache with "feedjack" alias, falling back to "default" if that
one is not defined.

Now that you have everything set up, run ``./manage.py feedjack_update`` (or
something like ``DJANGO_SETTINGS_MODULE=myproject.settings feedjack_update``) to
retrieve the actual data from the feeds. This script should be setup to be run
periodically (to retreive new posts from the feeds), which is usually a task for
unix cron daemon.

In case of some missing or inaccessible functionality, feedjack may issue (once
per runtime) `python warnings`_, which can (and most likely should) be captured
by logging system, so they can be handled by django (e.g. notification mail sent
to ADMINS).

To do that, add following code to Django's settings.py::

  import logging
  logging.captureWarnings(True)

.. _Django cache system: https://docs.djangoproject.com/en/dev/topics/cache/
.. _configure CACHES: http://docs.djangoproject.com/en/dev/topics/cache/#setting-up-the-cache
.. _python warnings: http://docs.python.org/library/warnings.html


Usage
-----

Navigate to http(s) url where Django app is deployed and you should see a page
with aggregation of all the stuff from configured feeds, or maybe an empty page
if none were configured or fetched.

Updates to feeds (fetching new entries) happen only on running feedjack_update
command, which (among others) can be used either as a command-line script
(installed by setup.py as a cli entry point) or a regular Django management
command.


Management commands
```````````````````

Feedjack app adds several Django management commands, full list of which can be
found by running e.g. ``./manage.py help`` (or similar thing via
django-admin.py).

Run each one of these with --help (or -h) option to see full info on the
particular command.

* ``feedjack_update``

  Fetches new items for all active (default) or a specified sites/feeds
  (see command-line --site and --feed options).

* ``feedjack_add_feed``

  Adds specified feed, with optional adding of site subscriber, fetching (see
  also --hidden option to make only future entries show up) and related stuff.

* ``feedjack_status``

  General command to list all sites/feeds and various information on these.

* ``feedjack_purge``

  Command to cleanup (purge) feed entries by specified criteria.

  Most common use is probably "by-age" subcommand, allowing to drop way-too-old
  posts (or newer ones, be sure to check out --dry-run option and lists of posts
  with --debug - might be useful to do before actual removal).

There might be more command since this README was updated, see ``./manage.py
help`` and ``--help`` in these for a full list and/or info on each.



Bugs, development, support
--------------------------

All the issues with this fork should probably be reported to respective github
project/fork, since code here can be quite different from the original project.

Until 2012, this fork was kept in a `fossil <http://www.fossil-scm.org/>`__ repo
`here <http://fraggod.net/code/fossil/feedjack/>`__.



Links
-----

* Github page (home): https://github.com/mk-fg/feedjack

* PyPI page: https://pypi.python.org/pypi/Feedjack/

* Original feedjack project links

  * Bitbucket repository: http://code.tabo.pe/feedjack/
  * Github mirror: https://github.com/tabo/feedjack
  * Website (now offline, it seems): http://www.feedjack.org/

* Other known forks

  * https://github.com/cato-/django-feedjack
  * https://github.com/squarepegsys/feedjack
  * https://code.google.com/p/feedjack-extension/
