#!/X/tools/binlinux/xpython
import simplejson as json
import uuid
from SceneGraph import util


__all__  = [StringAttribute, IntegerAttribute, FloatAttribute]


class Attribute(object):

    def __init__(name, value=None, parent=None, index=0):

        self._name            = name        
        self._parent          = parent

        # value & overrides
        self._value           = value
        self._value_override  = None        # secondary "override" value
        self._has_override    = False       # signifies that the value has an override

        # indexing
        self._index           = index       # internal index (for recalling in order)
        self._type            = None        # attribute type (int, float, string, etc.)   
        
        self._is_locked       = False       # attribute cannot be changed
        self._is_private      = False       # attribute is private & hidden from the ui  


    def __repr__(self):
        if self.value is not None:
            return '"%s" : "%s"' % (self.name, self.value)
        return '"%s" : None' % self.name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return (self.name) == (other.name)

    @property
    def name(self):
        return self.name

    @name.setter
    def name(self, name=None):
        if self._name != name:
            self._name = name
        return self.name

    @property
    def nice_name(self):
        return util.clean_name(self.name)

    @property
    def value(self):
        """
        Returns the current value. If the attribute has an override, 
        return that instead.
        """
        if self._has_override:
            return self._value_override
        return self._value

    @value.setter
    def value(self, value=None):
        """
        Set the current value - If the attribute currently 
        has an override, set that.
        """
        if not self.is_locked:
            if self._has_override:
                return self._value_override
            else:
                self._value = value
        return self.value

    @property
    def attribute_type(self):
        return self._type

    #- Overrides ----
    def addOverride(self, value=None):
        """
        Override the attribute value with another.
        """
        if not self.is_locked:
            self._has_override = True
            if self._value_override != value:
                self._value_override = value
        return self.value

    def clearOverride(self):
        """
        Remove the override flag - but stash any override 
        value for future use.
        """
        if not self._is_locked:
            self._has_override = False

    #- Locking ---
    @property
    def is_locked(self):
        """
        Returns the current lock state of the attribute.
        """
        return self._is_locked

    def lock(self):
        """
        Lock the attribute. If successful, returns true.
        """
        if self._is_locked is not True:
            self._is_locked = True
            return True
        return False

    def unlock(self):
        """
        Unock the attribute. If successful, returns true.
        """
        if self._is_locked is not False:
            self._is_locked = False
            return True
        return False

    
class StringAttribute(Attribute):
    def __init__(self, name, value=None, parent=None, **kwargs):
        super(StringAttribute, self).__init__(name, value=value, parent=parent, **kwargs)        
        self._type = 'string'
    
    @property 
    def value(self):
        return str(self.value)

    @value.setter
    def value(self, value=None):
        if value: value = str(value)
        self.value = value


class IntegerAttribute(Attribute):
    def __init__(self, name, value=None, parent=None, **kwargs):
        super(IntegerAttribute, self).__init__(name, value=value, parent=parent, **kwargs)        
        self._type  = 'int'

    @property 
    def value(self):
        return int(self.value)

    @value.setter
    def value(self, value=None):
        if value: value = int(value)
        self.value = value

        
class FloatAttribute(Attribute):
    def __init__(self, name, value=None, parent=None, **kwargs):
        super(FloatAttribute, self).__init__(name, value=value, parent=parent, **kwargs)        
        self._type  = 'float'

    @property 
    def value(self):
        return float(self.value)

    @value.setter
    def value(self, value=None):
        if value: value = float(value)
        self.value = value
