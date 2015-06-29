#!/usr/bin/env python

__package__ = 'SceneGraph'


def main():
	from . import options
	print '[%s]: INFO: initializing %s %s...' % (options.PACKAGE, options.PACKAGE, options.API_VERSION_AS_STRING)


main()