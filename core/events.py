#!/usr/bin/env python


class EventHandler(object):

    def __init__(self, sender):

        self.callbacks = []
        self.sender = sender
        self.blocked = False

    def __call__(self, *args, **kwargs):
        """
        Runs all callbacks.
        """
        if not self.blocked:
            return [callback(self.sender, *args, **kwargs) for callback in self.callbacks]
        return []

    def __iadd__(self, callback):
        """
        Add a callback to the stack.
        """
        self.add(callback)
        return self

    def __isub__(self, callback):
        """
        Remove a callback to the stack.

        :param callable callback: callback function/method.
        """
        self.remove(callback)
        return self

    def __len__(self):
        return len(self.callbacks)

    def __getitem__(self, index):
        return self.callbacks[index]

    def __setitem__(self, index, value):
        self.callbacks[index] = value

    def __delitem__(self, index):
        del self.callbacks[index]

    def blockSignals(self, block):
        """
        Temporarily block the handler from signalling its observers.

        :param bool block: block signals.
        """
        self.blocked = block

    def add(self, callback):
        """
        Add a callback. Raises error if callback is not
        callable.

        :param callable callback: callback function or method.
        """
        if not callable(callback):
            raise TypeError("callback must be callable")
        self.callbacks.append(callback)

    def remove(self, callback):
        """
        Remove a callback.

        :param callable callback: callback function or method.
        """
        self.callbacks.remove(callback)

