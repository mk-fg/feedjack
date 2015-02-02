Feedjack
----------------------------------------

Feedjack is a feed aggregator, allowing to aggregate multiple rss/atom feeds
into multiple "sites", somewhat like "planet" aggregator does, but better.

This project is a fork of the original feedjack project, which seem to be
abandoned for a while now.

Unlike the original, it is somewhat maintained and extended upon, latter might
be a good or a bad thing, depending on how you look at it.
See CHANGES file for more details on what happened here over time.


Installation
----------------------------------------


### Python module (Django app)

This feedjack fork is a regular package for Python 2.7 (not 3.X), but not in
pypi.

Best way to install it, would be to use [pip](http://pip-installer.org/) (see
also [pip2014.com](http://pip2014.com/)):

	% pip install 'git+https://github.com/mk-fg/feedjack.git#egg=feedjack'

That will automatically fetch and install 'feedjack' Django app to a configured
python site-path, along with all the required dependencies.

Another way of installing from a git chechout would be running `python setup.py
install`.

Note that to install stuff in system-wide PATH and site-packages, elevated
privileges are often required.
Use "install --user",
[~/.pydistutils.cfg](http://docs.python.org/install/index.html#distutils-configuration-files)
or [virtualenv](http://pypi.python.org/pypi/virtualenv) to do unprivileged
installs into custom paths.


### Django project

If you are not familiar with Django framework and how Django apps are deployed,
please see this short tutorial, which contains all the steps necessary to
initialize "django project" directory, also explaining what's in there:

	https://docs.djangoproject.com/en/stable/intro/tutorial01/#creating-a-project

Django project - at it's minimum - is just a few
[configuration files](https://docs.djangoproject.com/en/dev/topics/settings/),
specifying which database to use, and which "apps" should handle which URLs.

Feedjack can only be deployed as an "app" in such project, so it either has to
be created, or app can be enabled in any existing one.


### Enabling app in a Django project

* First of all, 'feedjack' app must be enabled in settings.py under
	[INSTALLED_APPS](http://docs.djangoproject.com/en/stable/ref/settings/#installed-apps).

	Running `./manage.py syncdb`
	(["syncdb" command](http://docs.djangoproject.com/en/stable/ref/django-admin/#syncdb))
	from the command line should then populate database (whichever is configured in
	the same file) with feedjack-specific schema.

* If Django 1.7+ is used (highly recommended), or [South app](http://south.aeracode.org)
	is available (with older Django versions), make sure to add it to INSTALLED_APPS
	as well, so it'd be able to apply future database schema updates effortlessly.

	`./manage.py migrate feedjack` should be run in addition to syncdb in that
	case, both initially, and (ideally) on every "feedjack" app update (in case
	there were any db schema changes).

* Feedjack "static files" directory should be setup to be reachable under
	configured [STATIC_URL](http://docs.djangoproject.com/en/dev/ref/settings/#static-url)
	(under "STATIC_URL/feedjack/", to be precise).

	This can be done automatically by using
	[django.contrib.staticfiles](https://docs.djangoproject.com/en/stable/ref/contrib/staticfiles/)
	app, that [will copy/link static files](https://docs.djangoproject.com/en/dev/howto/static-files/)
	with `./manage.py collectstatic` command.

	It can also be done manually.
	For instance, if your STATIC_URL resolves to "/var/www/htdocs", and Feedjack
	was installed to "/usr/lib/python2.7/site-packages/feedjack", symlinking dir
	from there should probably do the trick:

		% ln -s /usr/lib/python2.7/site-packages/feedjack/static/feedjack /var/www/htdocs/

* Be sure to enable/add/uncomment "django.contrib.admin" app
	([Django admin interface](https://docs.djangoproject.com/en/dev/ref/contrib/admin/))
	as well, since it's the most convenient and supported way to configure and
	control feedjack.

	"syncdb" operation (same as after enabling feedjack itself) might be necessary
	after that.

	Other ways to configure and control feedjack app after installation are:

	* Command-line tools.

		These are accessible via django-admin.py (or "./manage.py" wrapper) - see
		`--help` output for reference on all the supported commands there.

		Some (e.g. "feedjack_update") can also be installed as python
		console_scripts entry points.

	* Manipulate models from the python code or `./manage.py shell` directly,
		which might be desirable for some kind of migration or automated
		configuration.

* Add an entry for feedjack.urls in your Django "urls.py" file, so it'd look
	like this (with admin interface also enabled on "/admin/"):

		urlpatterns = patterns( '',
			(r'^admin/', include('django.contrib.admin.urls')),
			(r'', include('feedjack.urls')) )

	(of course, less trivial Django configurations should probably have way more
	entries there)

After all that, it might be worth checking out "/admin" section
(if django.contrib.admin app was enabled) to create a feedjack site,
otherwise sample default site will be created upon first request.

See also "Configuration" section below.


### Requirements

* [Python 2.7 (not 3.X)](http://python.org/)

* [feedparser 4.1+](https://code.google.com/p/feedparser/)

* [Django 1.5+](http://djangoproject.com)

* (optional) [lxml](http://lxml.de) - used for html mangling in some themes
	(fern, plain) processing of more free-form timestamps on feeds, if feedparser
	can't handle these for whatever reason.

* (optional, only for pre-1.7 Django versions)
  [South](http://south.aeracode.org) - for automated database schema migrations
  (when updating from older Feedjack versions).


### Updating from older versions

The only non-backwards-compatible changes should be in the database schema, thus
requiring migration, but it's much easier (automatic even) than it sounds.

Feedjack uses Django database migration features (or South module for older Django versions,
[where it has to be installed](http://south.readthedocs.org/en/latest/installation.html)).

Django/South "migrate" command can be used to see current database schema
version and which migrations are available/necessary:

	% ./manage.py migrate --list

	feedjack
	  ...
	  (*) 0013_auto__add_field_filterbase_crossref_rebuild__add_field_filterbase_cros
	  ( ) 0014_auto__add_field_post_hidden
	  ( ) 0015_auto__add_field_feed_skip_errors
	  ( ) 0016_auto__chg_field_post_title__chg_field_post_link
	  ( ) 0017_auto__chg_field_tag_name

This output shows which version the current schema is and how far it's behind
what code (models.py) expects it to be.

If South or Django-1.7+ was just installed, it might be necessary to specify
initial schema version manually, by using command like this:

	% ./manage.py migrate feedjack 0013 --fake

Best way to manually find which model version was used before is probably to
inspect git history for models.py to find the first not-yet applied change to
the model classes.
In case of pre-fork Feedjack versions (0.9.16 and below), this would be very
first (0001) schema version.

All the necessary migrations can be applied with a single `./manage.py migrate
feedjack` command:

	% ./manage.py migrate feedjack

	Running migrations for feedjack:
	 - Migrating forwards to 0017_auto__chg_field_tag_name.
	 > feedjack:0014_auto__add_field_post_hidden
	 > feedjack:0015_auto__add_field_feed_skip_errors
	 > feedjack:0016_auto__chg_field_post_title__chg_field_post_link
	 > feedjack:0017_auto__chg_field_tag_name
	 - Loading initial data for feedjack.
	Installed 4 object(s) from 1 fixture(s)

In case of any issues and for more advanced usage information, please refer to
either Django or [South project documentation](http://south.readthedocs.org/en/latest/).


Configuration
----------------------------------------

The first thing you want to do is to add a Site.

To do this, open Django admin interface and create your first planet.
You must use a valid address in the URL field, since it will be used to identify
the current planet when there are multiple planets in the same instance and to
generate all the links.

Then you should add Subscribers to your first planet.
A Subscriber is a relation between a Feed and a Site, so when you add your first
Subscriber, you must also add your first Feed by clicking in the “+” button at
the right of the Feed combobox.

Feedjack is designed to use
[Django cache system](https://docs.djangoproject.com/en/dev/topics/cache/)
to store database-intensive data like pages of posts and tagclouds, so it is highly
recomended to
[configure CACHES](http://docs.djangoproject.com/en/dev/topics/cache/#setting-up-the-cache)
in django settings (memcached, db, files, etc).

Now that you have everything set up, run `./manage.py feedjack_update` (or
something like `DJANGO_SETTINGS_MODULE=myproject.settings feedjack_update`)
to retrieve the actual data from the feeds.
This script should be setup to be run periodically (to retreive new posts from
the feeds), which is usually a task for unix cron daemon.

In case of some missing or inaccessible functionality, feedjack may issue (once
per runtime) [python warnings](http://docs.python.org/library/warnings.html),
which can (and most likely should) be captured by logging system, so they can be
handled by django (e.g. notification mail sent to ADMINS).

To do that, add following code to Django's settings.py:

	import logging
	logging.captureWarnings(True)


Bugs, development, support
----------------------------------------

All the issues with this fork should probably be reported to respective github
project/fork, since code here can be quite different from the original project.

Until 2012, this fork was kept in a [fossil](http://www.fossil-scm.org/) repo
[here](http://fraggod.net/code/fossil/feedjack/).


Links
----------------------------------------

* Original feedjack project links

	* Bitbucket repository: http://code.tabo.pe/feedjack/
	* Github mirror: https://github.com/tabo/feedjack
	* Website (now offline, it seems): http://www.feedjack.org/

* Other known forks

	* https://pypi.python.org/pypi/Feedjack/
	* https://github.com/cato-/django-feedjack
	* https://github.com/squarepegsys/feedjack
	* https://code.google.com/p/feedjack-extension/
