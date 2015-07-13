#!/usr/bin/env python
import logging
import sys
import os
import datetime


LOGGERS = {}
LOGGER_LEVEL = logging.INFO


def myLogger(name=None):
    global LOGGERS
    from SceneGraph import options

    if name is None:
        name = options.PACKAGE

    if LOGGERS.get(name):
        return LOGGERS.get(name)
    else:
        logger=logging.getLogger(name)
        logger.setLevel(LOGGER_LEVEL)
        
        console_handler = logging.StreamHandler()
        file_handler = logging.FileHandler(getLogFile(name))        

        formatter_console = logging.Formatter('[%(name)s]: %(levelname)s: %(message)s')
        formatter_file = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # set handler formatters
        console_handler.setFormatter(formatter_console)
        file_handler.setFormatter(formatter_file)
        file_handler.setLevel(logging.WARNING)
        
        # add handlers
        logger.addHandler(console_handler)        
        logger.addHandler(file_handler)

        logger.propagate = False
        LOGGERS[options.PACKAGE]=logger    
        return logger


def enableDebugging():
    """ Enables debugging on the logger """
    global LOGGER_INITIALIZED
    global LOGGER_LEVEL
    LOGGER_INITIALIZED = False
    LOGGER_LEVEL = logging.DEBUG
    return


def disableDebugging():
    """ Disables debugging on the logger """
    global LOGGER_INITIALIZED
    global LOGGER_LEVEL
    LOGGER_INITIALIZED = False
    LOGGER_LEVEL = logging.INFO
    return


def getLogFile(name):
    """ Returns the user log file """
    import os
    from SceneGraph import options
    if not os.path.exists(options.SCENEGRAPH_PREFS_PATH):
        os.makedirs(options.SCENEGRAPH_PREFS_PATH)
    return os.path.join(options.SCENEGRAPH_PREFS_PATH, '%s.log' % name)
