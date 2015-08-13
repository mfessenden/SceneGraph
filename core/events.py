#!/usr/bin/env python
'''
class Event(object):

    def __init__(self):
        self.handlers = []
    
    def add(self, handler):
        self.handlers.append(handler)
        return self
    
    def remove(self, handler):
        self.handlers.remove(handler)
        return self
    
    def fire(self, sender, earg=None):
        for handler in self.handlers:
            handler(sender, earg)
    
    __iadd__ = add
    __isub__ = remove
    __call__ = fire
'''

class Event(object):    
    def __init__(self, doc=None):
        self.__doc__ = doc

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return EventHandler(self, obj)
    
    def __set__(self, obj, value):
        pass


class EventHandler(object):    
    def __init__(self, event, obj): 

        self.event = event
        self.obj = obj
    
    def _getHandlers(self):        
        """(internal use) """        
        try:
            eventhandler = self.obj.__eventhandler__
        except AttributeError:
            eventhandler = self.obj.__eventhandler__ = {}
        return eventhandler.setdefault(self.event, [])
    
    def add(self, func):        
        """Add new event handler function.
        
        Event handler function must be defined like func(sender, earg).
        You can add handler also by using '+=' operator.
        """
        self._getHandlers().append(func)
        return self
    
    def remove(self, func):        
        """Remove existing event handler function.
        
        You can remove handler also by using '-=' operator.
        """
        self._getHandlers().remove(func)
        return self
    
    def notify(self, *args, **kwargs):        
        """Fire event and call all handler functions
        
        You can call EventHandler object itself like e(earg) instead of 
        e.fire(earg).
        """        
        for func in self._getHandlers():
            func(self.obj, *args, **kwargs)

    def handlerCount(self):
        return len(self._getHandlers())

    __iadd__ = add
    __isub__ = remove
    __call__ = notify


