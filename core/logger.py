#!/usr/bin/env python
import logging
import sys
import os
import datetime


LOGGERS = {}
LOGGER_LEVEL = logging.INFO



def myLogger():
    global LOGGERS
    from SceneGraph import options
    
    if LOGGERS.get(options.PACKAGE):
        return LOGGERS.get(options.PACKAGE)
    else:
        logger=logging.getLogger(options.PACKAGE)
        #logger.setLevel(logging.DEBUG)
        logger.setLevel(LOGGER_LEVEL)
        
        console_handler = logging.StreamHandler()
        file_handler = logging.FileHandler(getLogFile())        


        formatter_console = logging.Formatter('%(levelname)s: %(message)s')
        formatter_file = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # set handler formatters
        console_handler.setFormatter(formatter_console)
        file_handler.setFormatter(formatter_file)
        
        # add handlers
        logger.addHandler(console_handler)        
        #logger.addHandler(file_handler)

        logger.propagate = False
        LOGGERS.update(dict(name=logger))        
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
    LOGGER_LEVEL = logging.WARNING
    return


def getLogFile():
    """ Returns the user log file """
    import os
    from SceneGraph import options
    if not os.path.exists(options.SCENEGRAPH_PREFS_PATH):
        os.makedirs(options.SCENEGRAPH_PREFS_PATH)
    return os.path.join(options.SCENEGRAPH_PREFS_PATH, '%s.log' % options.PACKAGE)
