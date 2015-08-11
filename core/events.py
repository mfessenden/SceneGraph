#!/usr/bin/env python

class Event(object):
    """
    The Event class represents a callback that is passed from observer to
    observable.
    """
    event_type = 'generic'
    def __init__(self, parent, *args, **kwargs):        

        self.name    = kwargs.get('name', None)
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
    def __init__(self, parent, *args, **kwargs):
        super(NodePositionChanged, self).__init__(parent, *args,**kwargs)


class NodeNameChanged(Event):
    event_type = 'nameChanged'
    def __init__(self, parent, *args, **kwargs):
        super(NodeNameChanged, self).__init__(parent, *args,**kwargs)


class AttributeUpdatedEvent(Event):
    event_type = 'attributeUpdated'
    def __init__(self, parent, *args, **kwargs):
        super(AttributeUpdatedEvent, self).__init__(parent, *args,**kwargs)

        self.value = kwargs.get('value', None)
        #print '# AttributeUpdatedEvent: "%s": %s' % (self.name, str(self.value))


class MouseHoverEvent(Event):
    event_type = 'mouseHover'
    def __init__(self, parent, *args, **kwargs):
        super(MouseHoverEvent, self).__init__(parent, *args,**kwargs)


class MouseMoveEvent(Event):
    event_type = 'mouseMove'
    def __init__(self, parent, *args, **kwargs):
        super(MouseMoveEvent, self).__init__(parent, *args,**kwargs)


class MousePressEvent(Event):
    event_type = 'mousePress'
    def __init__(self, parent, *args, **kwargs):
        super(MousePressEvent, self).__init__(parent, *args,**kwargs)
