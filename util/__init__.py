#!/usr/bin/env python
import re


#- Naming ----
def clean_name(name):
    """
    Return a cleaned version of a string - removes everything 
    but alphanumeric characters and dots.
    """
    return re.sub(r'[^a-zA-Z0-9\n\.]', '_', name) 


def camel_case_to_lower_case_underscore(string):
    """
    Split string by upper case letters.
    F.e. useful to convert camel case strings to underscore separated ones.
    @return words (list)
    """
    words = []
    from_char_position = 0
    for current_char_position, char in enumerate(string):
        if char.isupper() and from_char_position < current_char_position:
            words.append(string[from_char_position:current_char_position].lower())
            from_char_position = current_char_position
    words.append(string[from_char_position:].lower())
    return '_'.join(words)


def camel_case_to_title(string):
    """
    Split string by upper case letters and return a nice name.
    @return words (list)
    """
    words = []
    from_char_position = 0
    for current_char_position, char in enumerate(string):
        if char.isupper() and from_char_position < current_char_position:
            words.append(string[from_char_position:current_char_position].title())
            from_char_position = current_char_position
    words.append(string[from_char_position:].title())
    return ' '.join(words)


def lower_case_underscore_to_camel_case(string):
    """
    Convert string or unicode from lower-case underscore to camel-case
    """
    splitted_string = string.split('_')
    # use string's class to work on the string to keep its type
    class_ = string.__class__
    return splitted_string[0] + class_.join('', map(class_.capitalize, splitted_string[1:]))


# attribute functions
def attr_type(s):
    """
    Return the attr type of a value as a string.
    """
    if is_none(s):
        return 'null'

    if is_list(s):
        return list_attr_types(s)

    else:
        if is_bool(s):
            return 'bool'

        if is_string(s):
            return 'str'

        if is_number(s):
            if type(s) is float:
                return 'float'
            if type(s) is int:
                return 'int'
    return 'unknown'


def list_attr_types(s):
    """
    Return a string type for the value.

    *todo:
        - 'unknown' might need to be changed
        - we'll need a feature to convert valid int/str to floats
          ie:
            [eval(x) for x in s if type(x) in [str, unicode]]
    """
    if not is_list(s):
        return 'unknown'
    
    for typ in [str, int, float, bool]:
        if all(isinstance(n, typ) for n in s):
            return '%s%d' % (typ.__name__, len(s))

    if False not in list(set([is_number(x) for x in s])):
        return 'float%d' % len(s)

    return 'unknown'


def is_none(s):
    return type(s).__name__ == 'NoneType'


def is_string(s):
    return type(s) in [str, unicode]


def is_number(s):
    """
    Check if a string is a int/float 
    """
    if is_bool(s):
        return False
    return isinstance(s, int) or isinstance(s, float) 


def is_bool(s):
    return isinstance(s, bool) or str(s).lower() in ['true', 'false']


def is_list(s):
    return type(s) in [list, tuple]
