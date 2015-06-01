#!/usr/bin/env python
import logging


LOGGER_INITIALIZED = False
LOGGER_LEVEL = logging.INFO


def getLogger():
    """ Returns logger object for use in this package """
    from . import options
    global LOGGER_INITIALIZED
    logger = logging.getLogger(options.PACKAGE)
    if not LOGGER_INITIALIZED:
        for handler in logger.handlers:
            logger.removeHandler(handler)
        logger.propagate = False
        logger.setLevel(LOGGER_LEVEL)
        console_handler = logging.StreamHandler()
        file_handler = logging.FileHandler(getLogFile())
        formatter_console = logging.Formatter('[SceneGraph]: %(levelname)s: %(message)s')
        formatter_file = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter_console)
        file_handler.setFormatter(formatter_file)
        logger.addHandler(console_handler)
        #logger.addHandler(file_handler)

    LOGGER_INITIALIZED = True
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


def getLogFile():
    """ Returns the user log file """
    import os
    from . import options
    if not os.path.exists(options.SCENEGRAPH_PREFS_PATH):
        os.makedirs(options.SCENEGRAPH_PREFS_PATH)
    return os.path.join(options.SCENEGRAPH_PREFS_PATH, '%s.log' % options.PACKAGE)
