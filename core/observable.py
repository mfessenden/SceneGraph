#!/usr/bin/env python


class Observable(object):
    """
    Simple Observable example.
    """
    def __init__(self):
        
        self._observers = []
        self._changed = 0
    
    def addObserver(self, obs):
        """
        Add an observer.

        params:
            obs (obj) - Observer object.
        """
        if obs not in self._observers:
            self._observers.append(obs)
    
    def getObservers(self):
        """
        Add an observer.

        params:
            obs (obj) - Observer object.

        returns:
            (list) - list of observers.
        """
        return self._observers
    
    def observerCount(self):
        """
        Returns the number of observers.

        returns:
            (int) - number of observers.
        """
        return len(self._observers)
    
    def removeObserver(self, obs):
        """
        Remove an observer.

        params:
            obs (obj) - Observer object.

        returns:
            (bool) - observer was removed.
        """
        if obs in self._observers:
            self._observers.remove(obs)
            return True
        return False
            
    def notifyObservers(self, *args, **kwargs):
        """
        Callback to update all observers.
        """
        if not self._changed:
            return

        self.clearChanged()
        for obs in self._observers:
            obs.update(*args, **kwargs)
    
    def clearChanged(self):
        """
        Clear the changed status.
        """
        self._changed = 0
        
    def setChanged(self):
        """
        Set the changed status.
        """
        self._changed = 1
    
    def hasChanged(self):
        """
        Indicates the observer changed status.
        """
        return self._changed
 
 
class Observer(object):
    def __init__(self):
        pass
        
    def update(self, *args):
        pass
 
 
class Event(object):
    def __init__(self, name, parent, *args, **kwargs):        

        self.name   = name
        self.parent = parent

        self._data  = dict()
        self._data.update(*args, **kwargs)
