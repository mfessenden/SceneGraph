#!/usr/bin/env python
import logging
import sys
import os
import datetime
from PySide import QtCore


LOGGERS = {}
LOGGER_LEVEL = logging.INFO


class QStream(QtCore.QObject):
    """
    Custom QObject for receiving signals from the logger.
    """   
    messageWritten = QtCore.Signal(str)

    def fileno(self):
        return -1
    
    def write(self, msg):
        if (not self.signalsBlocked()):
            self.messageWritten.emit(unicode(msg))


class QtHandler(logging.Handler):
    """
    Custom handler for sending messages to the ui
    """
    def __init__(self):
        logging.Handler.__init__(self)
        self.qstream = QStream()

    def emit(self, record):
        record = self.format(record)
        if record: 
            self.qstream.write('%s\n'%record)


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


def getLogFile():
    """ Returns the user log file """
    import os
    from SceneGraph import options
    if not os.path.exists(options.SCENEGRAPH_PREFS_PATH):
        os.makedirs(options.SCENEGRAPH_PREFS_PATH)
    return os.path.join(options.SCENEGRAPH_PREFS_PATH, '%s.log' % options.PACKAGE)
