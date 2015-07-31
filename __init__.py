#!/usr/bin/env python
__package__ = 'SceneGraph'
__version__ = None
__version_info__  = ()


def main():
    global __version__
    global __version_info__
    from . import options
    print '[%s]: INFO: initializing %s %s...' % (options.PACKAGE, options.PACKAGE, options.API_VERSION_AS_STRING)
    __version__ = options.API_VERSION_AS_STRING
    __version_info__ = [int(x) for x in str(options.API_MAJOR_VERSION).split('.')]
    __version_info__.extend([options.API_REVISION, "development", 0]) 
    __version_info__  = tuple(__version_info__)


main()