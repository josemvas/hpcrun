from os import getcwd
from argparse import ArgumentParser, Action, SUPPRESS, RawTextHelpFormatter
from abspathlib import AbsPath, NotAbsolutePathError
from clinterface.printing import *

from .i18n import _
from .utils import option, tree_repr
from .shared import config

def get_path_tree(path):
    def dirbranches(parent, partlist, dirtree):
        if partlist:
            part = partlist.pop(0)
            try:
                part.format()
            except IndexError:
                children = parent.listdir()
                for child in children:
                    dirtree[child] = {}
                    dirbranches(parent/child, partlist, dirtree[child])
            else:
                dirbranches(parent/part, partlist, dirtree)
    dirtree = {}
    partlist = list(AbsPath(path).parts)
    dirbranches(AbsPath(), partlist, dirtree)
    return dirtree

class StorePath(Action):
    def __init__(self, **kwargs):
        super().__init__(nargs=1, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, AbsPath(values[0], relto=getcwd()))

def parse_args(command, config):

    parser = ArgumentParser(prog=command, add_help=False, description='Envía trabajos de {} a la cola de ejecución.'.format(config.packagename), formatter_class=RawTextHelpFormatter)

    group1 = parser.add_argument_group('Argumentos')
    group1.add_argument('files', nargs='*', metavar='FILE', help='Rutas de los archivos de entrada.')

    group2 = parser.add_argument_group('Opciones comunes')
    group2.name = 'common'
    group2.add_argument('-h', '--help', action='help', help='Mostrar este mensaje de ayuda y salir.')
    group2.add_argument('-v', '--version', metavar='VERSION', default=SUPPRESS, help=tree_repr('Versiones disponibles', config.versions.keys()))
    group2.add_argument('-n', '--nproc', type=int, metavar='#PROCS', default=1, help='Requerir #PROCS núcleos de procesamiento.')
    group2.add_argument('-q', '--queue', metavar='QUEUE', default=SUPPRESS, help='Requerir la cola QUEUE.')
    group2.add_argument('-j', '--job', action='store_true', help='Interpretar los argumentos como nombres de trabajo en vez de rutas de archivo.')
    group2.add_argument('--in', action=StorePath, metavar='PATH', default=getcwd(), help='Buscar los archivos de entrada del trabajo en el directorio PATH.')
    group2.add_argument('--out', action=StorePath, metavar='PATH', default=SUPPRESS, help='Escribir los archivos de salida del trabajo en el directorio PATH.')
    group2.add_argument('--scratch', action=StorePath, metavar='PATH', default=SUPPRESS, help='Escribir los archivos temporales en el directorio PATH.')
    group2.add_argument('--proxy', action='store_true', help='Enviar el trabajo procesado por un cliente remoto.')
    group2.add_argument('--debug', action='store_true', help='Procesar el trabajo sin enviarlo.')
    hostgroup = group2.add_mutually_exclusive_group()
    hostgroup.add_argument('-N', '--nhost', type=int, metavar='#NODES', default=1, help='Requerir #NODES nodos de ejecución.')
    hostgroup.add_argument('--hosts', metavar='NODE', default=SUPPRESS, help='Solicitar nodos específicos de ejecución.')
    yngroup = group2.add_mutually_exclusive_group()
    yngroup.add_argument('--yes', action='store_true', help='Responder "si" a todas las preguntas.')
    yngroup.add_argument('--no', action='store_true', help='Responder "no" a todas las preguntas.')

    group3 = parser.add_argument_group('Opciones remotas')
    group3.name = 'remote'
    group3.add_argument('-H', '--remote-host', metavar='HOSTNAME', help='Procesar el trabajo en el host HOSTNAME.')

    group4 = parser.add_argument_group('Opciones de selección de archivos')
    group4.name = 'arguments'
    group4.add_argument('-f', '--filter', metavar='REGEX', default=SUPPRESS, help='Enviar únicamente los trabajos que coinciden con la expresión regular.')
#    group4.add_argument('-r', '--restart', help='Restart job.')

    group5 = parser.add_argument_group('Opciones de interpolación')
    group5.name = 'interpolation'
    group5.add_argument('--prefix', metavar='PREFIX', default=None, help='Agregar el prefijo PREFIX al nombre del trabajo.')
    group5.add_argument('-m', '--mol', metavar='MOLFILE', action='append', default=[], help='Incluir el último paso del archivo MOLFILE en las variables de interpolación.')
    group5.add_argument('-x', '--var', dest='posvars', metavar='VALUE', action='append', default=[], help='Variables posicionales de interpolación.')

    group6 = parser.add_argument_group('Conjuntos de parámetros')
    group6.name = 'parametersets'
    for key in config.parametersets:
        group6.add_argument(option(key), metavar='SETNAME', default=SUPPRESS, help=tree_repr('Conjuntos de parámetros', get_path_tree(config.parameterpathdict[key])))

    group7 = parser.add_argument_group('Variables de interpolación')
    group7.name = 'interpolvars'
    for key in config.interpolvars:
        group7.add_argument(option(key), metavar='VALUE', default=SUPPRESS, help='Variable de interpolación')

    parsedargs = parser.parse_args()

    options = {}
    for group in parser._action_groups:
        group_dict = {a.dest:getattr(parsedargs, a.dest) for a in group._group_actions if a.dest in parsedargs}
        if hasattr(group, 'name'):
            options[group.name] = group_dict

    if not parsedargs.files:
        print_error_and_exit(_('Debe especificar al menos un archivo de entrada'))

    return options, parsedargs.files
