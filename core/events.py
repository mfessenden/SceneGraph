#!/usr/bin/env python

class Event(object):
    event_type = 'generic'
    def __init__(self, name, parent, *args, **kwargs):        

        self.name    = name
        self.dagnode = parent

        self._data  = dict()
        self._data.update(**kwargs)

    @property
    def type(self):
        return self.event_type    

    @property
    def data(self):
        return self._data   


class NodePositionChanged(Event):
    event_type = 'positionChanged'
    def __init__(self, name, parent, *args, **kwargs):
        super(NodePositionChanged, self, *args, **kwargs)


class AttributeUpdatedEvent(Event):
    event_type = 'attributeUpdated'
    def __init__(self, name, parent, *args, **kwargs):
        super(AttributeUpdatedEvent, self, *args, **kwargs)


class MouseHoverEvent(Event):
    event_type = 'mouseHover'
    def __init__(self, name, parent, *args, **kwargs):
        super(MouseHoverEvent, self, *args, **kwargs)


class MouseMoveEvent(Event):
    event_type = 'mouseMove'
    def __init__(self, name, parent, *args, **kwargs):
        super(MouseMoveEvent, self, *args, **kwargs)


class MousePressEvent(Event):
    event_type = 'mousePress'
    def __init__(self, name, parent, *args, **kwargs):
        super(MousePressEvent, self, *args, **kwargs)
