#!/usr/bin/env python
from SceneGraph.core import log


class Observer(object):

    def update_observer(self, obs, event, *args, **kwargs):
        """
        Called when the observed object has changed.

        :param Observable obs: Observable object.
        :param Event event: Event object.
        """
        pass


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

        :param Observer obs: Observer object.
        """
        if obs not in self._observers:
            self._observers.append(obs)
    
    def get_observers(self):
        """
        Return the current observers.

        :returns: list of observers.
        :rtype: list
        """
        return self._observers
    
    def observer_count(self):
        """
        Returns the number of current observers.

        :returns: number of observers.
        :rtype: list
        """
        return len(self._observers)
    
    def remove_observer(self, obs):
        """
        Remove an observer.

        :param Observer obs: Observer object.

        :returns: observer was successfully removed.
        :rtype: bool
        """
        if obs in self._observers:
            self._observers.remove(obs)
            return True
        return False

    def notify(self, event, *args, **kwargs):
        """
        Callback to update all observers.

        :param Event event: Event object.
        """
        if not self.has_changed:
            return

        if event is None:
            return
            
        log.debug('updating observers...')
        self.clear_changed()
        for obs in self._observers:
            if hasattr(obs, 'update_observer'):
                obs.update_observer(self, event, *args, **kwargs)
    
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

        :returns: Observable has been changed.
        :rtype: bool
        """
        return self._changed
 
  
 