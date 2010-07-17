import itertools as it, operator as op, functools as ft

from django import template
register = template.Library()

from BeautifulSoup import BeautifulSoup


@register.filter
def text_to_blocks(soup, classname='text_node'):
	soup = BeautifulSoup(soup)
	for node in it.imap(op.methodcaller('strip'), soup.findAll(text=True)):
		if node: node.replaceWith('<div class="text_node">{0}</div>'.format(node))
	return unicode(soup)
