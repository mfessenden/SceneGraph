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


# attribute conversions
def is_number(s):
    """
    Check if a string is a int/float 
    """
    try:
        float(s)
        return True
    except ValueError:
        return False


def is_bool(s):
    if str(s).lower() in ['true', 'false', '1', '0']:
        return True
    return False