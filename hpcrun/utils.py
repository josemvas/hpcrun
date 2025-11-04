import re
from string import Template, Formatter
from clinterface.printing import *
from .i18n import _

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

class ArgGroups:
    def __init__(self):
        self.__dict__['flags'] = set()
        self.__dict__['options'] = dict()
        self.__dict__['multoptions'] = dict()
    def gather(self, options):
        if isinstance(options, dict):
            for key, value in options.items():
                if value is False:
                    pass
                elif value is True:
                    self.__dict__['flags'].add(key)
                elif isinstance(value, (int, float, str)):
                    self.__dict__['options'].update({key:value})
                elif isinstance(value, list):
                    self.__dict__['multoptions'].update({key:value})
                else:
                    raise ValueError()
    def __repr__(self):
        return repr(self.__dict__)

class IdentityList(list):
    def __init__(self, *args):
        list.__init__(self, args)
    def __contains__(self, other):
        return any(o is other for o in self)

class ConfigTemplate(Template):
    delimiter = '&'
    idpattern = r'[a-z][a-z0-9_]*'

class InterpolationTemplate(Template):
    delimiter = '$'
    idpattern = r'[a-z][a-z0-9_]*'

class FormatKeyError(Exception):
    pass

def natural_sorted(*args, **kwargs):
    if 'key' not in kwargs:
        kwargs['key'] = lambda x: [int(c) if c.isdigit() else c.casefold() for c in re.split('(\d+)', x)]
    return sorted(*args, **kwargs)

def option(key, value=None):
    if value is None:
        return('--{}'.format(key.replace('_', '-')))
    else:
        return('--{}="{}"'.format(key.replace('_', '-'), value))

def tree_repr(title, options):
    tree_lines = [title + ':']
    format_tree_lines(options, tree_lines, level=1)
    return '\n'.join(tree_lines)

def format_tree_lines(options, tree_lines, level):
    for opt in sorted(options):
        tree_lines.append('   '*level + opt)
        if isinstance(options, dict):
            format_tree_lines(options[opt], tree_lines, level + 1)

def catch_keyboard_interrupt(f):
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except KeyboardInterrupt:
            print_error_and_exit(_('Interrumpido por el usuario'))
    return wrapper

def deep_join(nestedlist, nextseparators, pastseparators=[]):
# For example deep_join(['dir1', 'dir2', ['name', 'ext']], ['/', '.'])
# will return dir1/dir2/name.ext
    itemlist = []
    separator = nextseparators.pop(0)
    for item in nestedlist:
        if isinstance(item, (list, tuple)):
            itemlist.append(deepjoin(item, nextseparators, pastseparators + [separator]))
        elif isinstance(item, str):
            for delim in pastseparators:
                if delim in item:
                    raise ValueError('Components can not contain higher level separators')
            itemlist.append(item)
        else:
            raise TypeError('Components must be strings')
    return separator.join(itemlist)

def file_except_info(exception, path):
    if isinstance(exception, IsADirectoryError):
        print_failure(_('La ruta {path} es un directorio'), path=path)
    elif isinstance(exception, FileExistsError):
        print_failure(_('El archivo {path} ya existe'), path=path)
    elif isinstance(exception, FileNotFoundError):
        print_failure(_('El archivo {path} no existe'), path=path)
    elif isinstance(exception, OSError):
        print_failure(_('Error de sistema: {exception}'), exception=str(exception))
    else:
        print_error_and_exit(_('{exceptype}: {exception}'), exceptype=type(exception).__name__, exception=str(exception))

def dir_except_info(exception, path):
    if isinstance(exception, NotADirectoryError):
        print_failure(_('La ruta {path} no es un directorio'), path=path)
    elif isinstance(exception, FileExistsError):
        print_failure(_('El directorio {path} ya existe'), path=path)
    elif isinstance(exception, FileNotFoundError):
        print_failure(_('El directorio {path} no existe'), path=path)
    elif isinstance(exception, OSError):
        print_failure(_('Error de sistema: {exception}'), exception=str(exception))
    else:
        print_error_and_exit(_('{exceptype}: {exception}'), exceptype=type(exception).__name__, exception=str(exception))

def template_parse(template_str, s):
    """Match s against the given format string, return dict of matches.
    We assume all of the arguments in format string are named keyword arguments (i.e. no {} or
    {:0.2f}). We also assume that all chars are allowed in each keyword argument, so separators
    need to be present which aren't present in the keyword arguments (i.e. '{one}{two}' won't work
    reliably as a format string but '{one}-{two}' will if the hyphen isn't used in {one} or {two}).
    We raise if the format string does not match s. Example:
    fs = '{test}-{flight}-{go}'
    s = fs.format('first', 'second', 'third')
    template_parse(fs, s) -> {'test': 'first', 'flight': 'second', 'go': 'third'}
    """
    # First split on any keyword arguments, note that the names of keyword arguments will be in the
    # 1st, 3rd, ... positions in this list
    tokens = re.split(r'\$([a-z][a-z0-9_]*)', template_str, flags=re.IGNORECASE)
    keywords = tokens[1::2]
    # Now replace keyword arguments with named groups matching them. We also escape between keyword
    # arguments so we support meta-characters there. Re-join tokens to form our regexp pattern
    tokens[1::2] = map(u'(?P<{}>.*)'.format, keywords)
    tokens[0::2] = map(re.escape, tokens[0::2])
    pattern = ''.join(tokens)
    # Use our pattern to match the given string, raise if it doesn't match
    matches = re.match(pattern, s)
    if not matches:
        raise Exception("Format string did not match")
    # Return a dict with all of our keywords and their values
    return {x: matches.group(x) for x in keywords}

booleans = {
    'True': True,
    'False': False
}
