#!/usr/bin/env python
from SceneGraph.core import log


class Observable(object):
    """
    Simple Observable example.
    """
    def __init__(self):
        
        self._observers = []
        self._changed = 0
    
    def add_observer(self, obs):
        """
        Add an observer.

        params:
            obs (obj) - Observer object.
        """
        if obs not in self._observers:
            self._observers.append(obs)
    
    def get_observers(self):
        """
        Add an observer.

        params:
            obs (obj) - Observer object.

        returns:
            (list) - list of observers.
        """
        return self._observers
    
    def observer_count(self):
        """
        Returns the number of observers.

        returns:
            (int) - number of observers.
        """
        return len(self._observers)
    
    def remove_observer(self, obs):
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
            
    def notify(self, *args, **kwargs):
        """
        Callback to update all observers.
        """
        if not self._changed:
            return

        log.info('updating observers...')
        self.clear_changed()
        for obs in self._observers:
            obs.update(*args, **kwargs)
    
    def clear_changed(self):
        """
        Clear the changed status.
        """
        self._changed = 0
        
    def set_changed(self):
        """
        Set the changed status.
        """
        self._changed = 1
    
    def has_changed(self):
        """
        Indicates the observer changed status.
        """
        return self._changed
 
  
 