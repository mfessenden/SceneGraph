#!/X/tools/binlinux/xpython
import simplejson as json


__all__ = ['StringAttribute', 'IntegerAttribute', 'FloatAttribute']


class AttributeBase(object):
    """
    Base attribute class
    """
    def __init__(self, parent=None, name=None, value=None, index=0):
        
        self._parent        = parent                # parent object (Node)
        self._name          = name                  # attribute name
        self._value         = {'default':value}     # attribute value (allows for overrides)
        
        self._index         = index                 # internal index (for recalling in order)
        self._type          = None                  # attribute type (int, float, string, etc.)   
        
        self.is_locked      = False                 # attribute cannot be changed
        self.is_private     = False                 # attribute is private & hidden from the ui  
    
    def __repr__(self):
        return str(self.data())
    
    def __lt__(self, other):
        return self.getValue() < other
    
    def data(self, type='default'):
        return {self.name:self.getValue(type)}
    
    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, name=None):
        self._name = name
        return self._name
    
    @property
    def nice_name(self):
        return self._name.title()
    
    def getValue(self, type='default'):
        """
        Return a value of the given type
        """
        return self._value.get(type, None)
    
    def setValue(self, type='default', value=None):
        """
        Set a value of the given type
        """
        self._value.update(**{type:value})
        return self._value.get(type, None)

    
class StringAttribute(AttributeBase):
    def __init__(self, parent=None, name=None, value=None):
        super(StringAttribute, self).__init__(parent, name, value)        
        self._type          = 'string'
        
    def setValue(self, type='default', value=None):
        if value: value = str(value)
        return super(StringAttribute, self).setValue(value)


class IntegerAttribute(AttributeBase):
    def __init__(self, parent=None, name=None, value=None):
        super(IntegerAttribute, self).__init__(parent, name, value)        
        self._type          = 'int'

    def setValue(self, type='default', value=None):
        if value: value = int(value)
        return super(IntegerAttribute, self).setValue(value)


class FloatAttribute(AttributeBase):
    def __init__(self, parent=None, name=None, value=None):
        super(FloatAttribute, self).__init__(parent, name, value)        
        self._type          = 'float'
        

