#!/usr/bin/env python

class Signal(object):

    def __init__(self, parent=None):

        self._source = parent
        self._handlers = []

    @property
    def source(self):
        return self._source    

    def connect(self, func):
        if func not in self._handlers:
            self._handlers.append(func)

    def disconnect(self, func):
        try:  
            self._handlers.remove(func)  
        except ValueError:  
            print('Warning: function %s not removed from signal %s' % (func, self))

    def notify( self, *args, **kwargs):
        for handler in self._handlers:
            handler(*args, **kwargs)
