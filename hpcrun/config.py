import re
import sys
import json
from os import getcwd
from string import Template
from argparse import ArgumentParser
from subprocess import check_output, DEVNULL
from abspathlib import AbsPath
from json5conf import JSONConfDict, InvalidJSONError, json5_read
from clinterface import *

from .i18n import _
from .utils import catch_keyboard_interrupt

package_dir = AbsPath(__file__).parent
site_packages_dir = AbsPath(__file__).parent.parent
package_data = site_packages_dir/package_dir.name%'dat'
install_dir = AbsPath(sys.argv[0], relto=getcwd()).parent
truthy_options = ['si', 'yes']
falsy_options = ['no']

@catch_keyboard_interrupt
def setup():
    prompt = _('Escriba la ruta del directorio de configuración:')
    config_dir = AbsPath(complete_dirpath(prompt), relto=getcwd())
    with open(package_data, 'w') as f:
        f.write(config_dir)
    if config_dir.exists():
        read_config(config_dir)
    else:
        write_config(config_dir)

@catch_keyboard_interrupt
def reload():
    try:
        with open(package_data, 'r') as file:
            config_dir = AbsPath(file.read())
        read_config(config_dir)
    except FileNotFoundError:
        print_error_and_exit(_('El archivo {file} no existe, ejecute hpcrun-setup para generarlo'), file=package_data)

def write_config(config_dir):
    print_error_and_exit(_('write_config no está implementado aún'))

def read_config(config_dir):
    package_names = {}
    executable_names = {}
    enabled_packages = []

    if not (config_dir).is_dir():
        print_error_and_exit(_('{config_dir} does not exist or is not a directory'), config_dir=config_dir)

    if not (config_dir/'package_profiles').is_dir():
        print_error_and_exit(_('{config_dir}/package_profiles does not exist or is not a directory'), config_dir=config_dir)

    if not (config_dir/'cluster_profile.json').is_file():
        print_error_and_exit(_('{config_dir}/cluster_profile.json does not exist or is not a file'), config_dir=config_dir)

#    (config_dir/'database').mkdir()
#    (config_dir/'database'/'programspecs').mkdir()
#    (config_dir/'database'/'schedulers').mkdir()
#    for specfile in (package_dir/'database'/'programspecs').listdir():
#        if (config_dir/'database'/'programspecs'/specfile).is_file():
#            if json5_read(package_dir/'database'/'programspecs'/specfile) != json5_read(config_dir/'database'/'programspecs'/specfile):
#                prompt = _('¿Desea sobrescribir el archivo de configuración {specfile}?', specfile=specfile)
#                if complete_binary_choice(prompt, truthy_options, falsy_options):
#                    (package_dir/'database'/'programspecs'/specfile).copy(config_dir/'database'/'programspecs')
#        else:
#            (package_dir/'database'/'programspecs'/specfile).copy(config_dir/'database'/'programspecs')
#    for specfile in (package_dir/'database'/'schedulers').listdir():
#        if (config_dir/'database'/'schedulers'/specfile).is_file():
#            if json5_read(package_dir/'database'/'schedulers'/specfile) != json5_read(config_dir/'database'/'schedulers'/specfile):
#                prompt = _('¿Desea sobrescribir la configuración local del gestor de trabajos {queuename}?', queuename=specfile)
#                if complete_binary_choice(prompt, truthy_options, falsy_options):
#                    (package_dir/'database'/'schedulers'/specfile).copy(config_dir/'database'/'schedulers')
#        else:
#            (package_dir/'database'/'schedulers'/specfile).copy(config_dir/'database'/'schedulers')

    package_names_inv = {}
    for profile in (config_dir/'package_profiles').iterdir():
        specdict = json5_read(profile)
        if 'packagename' in specdict:
            package_names[profile.name] = specdict['packagename']
            package_names_inv[specdict['packagename']] = profile.name
            executable_names[profile.name] = specdict['executablename']

    for package in package_names:
        if (install_dir/executable_names[package]).is_file():
            enabled_packages.append(package)

    if package_names:
        prompt = _('Seleccione los programas que desea instalar/desinstalar:')
        selected_packages = select_options(prompt, package_names_inv, enabled_packages)
    else:
        print_warning(_('No hay ningún programa configurado todavía'))

#    systemlibs = set()
#    for line in check_output(('ldconfig', '-Nv'), stderr=DEVNULL).decode(sys.stdout.encoding).splitlines():
#        match = re.fullmatch(r'(\S+):', line)
#        if match:
#            systemlibs.add(match.group(1))
#    pythonlibs = set()
#    for line in check_output(('ldd', sys.executable)).decode(sys.stdout.encoding).splitlines():
#        match = re.fullmatch(r'\s*\S+\s+=>\s+(\S+)\s+\(\S+\)', line)
#        if match:
#            lib = AbsPath(match.group(1)).parent
#            if lib not in systemlibs:
#                pythonlibs.add(lib)

    for package in package_names:
        if package in selected_packages:
            config = JSONConfDict(dict(
                load = [],
                source = [],
                export = {},
                versions = {},
                defaults = {},
                conflicts = {},
                optargs = [],
                posargs = [],
                filekeys = {},
                filevars = {},
                fileopts = {},
                inputfiles = [],
                outputfiles = [],
                ignorederrors = [],
                parametersets = [],
                interpolable = [],
                interpolvars = [],
                prescript = [],
                postscript = [],
                onscript = [],
                offscript = [],
            ))
            try:
                config.update(json5_read(config_dir/'cluster_profile.json'))
                config.update(json5_read(config_dir/'package_profiles'/package))
                config.update(json5_read(package_dir/'database'/'schedulers'/config.scheduler%'json'))
                config.update(json5_read(package_dir/'database'/'programspecs'/config.programspec%'json'))
            except InvalidJSONError:
                print_error_and_exit(_('El archivo de configuración {file} contiene JSON inválido'), file=e.file_path, error=str(e))
            dumping = json.dumps(config)
            try:
                with open(install_dir/executable_names[package], 'w') as file:
                    file.write(f'#!{sys.executable}\n')
                    file.write('import sys\n')
                    file.write('from hpcrun import main\n')
                    file.write('sys.path.append(\n')
                    file.write(f"r'{site_packages_dir}'\n")
                    file.write(')\n')
                    file.write('main.submit_jobs(\n')
                    file.write(f"r'''{dumping}'''\n")
                    file.write(')\n')
                (install_dir/executable_names[package]).chmod(0o755)
            except PermissionError:
                print_error_and_exit(_('No tiene permiso para escribir en el directorio {path}'), path=install_dir)
        else:
            (install_dir/executable_names[package]).unlink(missing_ok=True)
