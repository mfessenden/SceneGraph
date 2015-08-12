#!/usr/bin/env python


class Observer(object):

    def update_observer(self, obs, event, *args, **kwargs):
        """
        Called when the observed object has changed.

        :param Observable obs: Observable object.
        :param Event event: Event object.
        """
        pass