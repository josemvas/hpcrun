import re
import os
import sys
import json
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

truthy_options = ['si', 'yes']
falsy_options = ['no']

def _default_install_dir():
    # Root/privileged users -> /usr/local/bin
    if os.geteuid() == 0:
        return AbsPath('/usr/local/bin')
    # Normal users -> ~/.local/bin
    return AbsPath('~/.local/bin')

def _default_config_dir():
    # Root/privileged users -> /usr/local/etc
    if os.geteuid() == 0:
        return AbsPath('/usr/local/etc')
    # Normal users -> ~/.local/etc
    return AbsPath('~/.local/etc')

def _validate_config_dir(config_dir):
    """Validates that the required config directories and files exist."""
    if not config_dir.is_dir():
        print_error_and_exit(_('{config_dir} does not exist or is not a directory'), config_dir=config_dir)
    if not (config_dir/'package_profiles').is_dir():
        print_error_and_exit(_('{config_dir}/package_profiles does not exist or is not a directory'), config_dir=config_dir)
    if not (config_dir/'cluster_profile.json').is_file():
        print_error_and_exit(_('{config_dir}/cluster_profile.json does not exist or is not a file'), config_dir=config_dir)

def _load_package_info(config_dir):
    """Reads all package profiles and returns names, profiles dict, and executables dict."""
    package_names = []
    package_profiles_dict = {}
    package_executables_dict = {}
    for profile in (config_dir/'package_profiles').iterdir():
        specdict = json5_read(profile)
        if 'packagename' in specdict:
            packagename = specdict['packagename']
            package_names.append(packagename)
            package_profiles_dict[packagename] = profile
            package_executables_dict[packagename] = specdict['executablename']
    return package_names, package_profiles_dict, package_executables_dict

def _build_config(packagename, config_dir, package_profiles_dict):
    """Builds and returns the merged JSONConfDict for a given package."""
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
        parameterpathlist = [],
        parameterpathdict = {},
        interpolable = [],
        interpolvars = [],
        prescript = [],
        postscript = [],
        onscript = [],
        offscript = [],
    ))
    try:
        config.update(json5_read(config_dir/'cluster_profile.json'))
        config.update(json5_read(package_profiles_dict[packagename]))
        config.update(json5_read(package_dir/'database'/'schedulers'/config.scheduler%'json'))
        config.update(json5_read(package_dir/'database'/'programspecs'/config.programspec%'json'))
    except InvalidJSONError as e:
        print_error_and_exit(_('El archivo de configuración {file} contiene JSON inválido'), file=e.file_path, error=str(e))
    return config

def _write_executable(packagename, config_dir, package_profiles_dict, package_executables_dict, install_dir):
    """Builds config and writes the executable script for a given package."""
    config = _build_config(packagename, config_dir, package_profiles_dict)
    dumping = json.dumps(config)
    try:
        with open(install_dir/package_executables_dict[packagename], 'w') as file:
            file.write(f'#!{sys.executable}\n')
            file.write('import sys\n')
            file.write('from hpcrun import main\n')
            file.write('sys.path.append(\n')
            file.write(f"r'{site_packages_dir}'\n")
            file.write(')\n')
            file.write('main.submit_jobs(\n')
            file.write(f"r'''{dumping}'''\n")
            file.write(')\n')
        (install_dir/package_executables_dict[packagename]).chmod(0o755)
    except PermissionError:
        print_error_and_exit(_('No tiene permiso para escribir en el directorio {path}'), path=install_dir)

@catch_keyboard_interrupt
def reconfig():
    config_dir = _default_config_dir()
    install_dir = _default_install_dir()
    _validate_config_dir(config_dir)

    package_names, package_profiles_dict, package_executables_dict = _load_package_info(config_dir)

    enabled_packages = [
        packagename for packagename in package_names
        if (install_dir/package_executables_dict[packagename]).is_file()
    ]

    if package_names:
        prompt = _('Seleccione los programas que desea instalar/desinstalar:')
        selected_packages = select_options(prompt, package_names, enabled_packages)
    else:
        print_warning(_('No hay ningún programa configurado todavía'))
        return

    for packagename in package_names:
        if packagename in selected_packages:
            _write_executable(packagename, config_dir, package_profiles_dict, package_executables_dict, install_dir)
        else:
            (install_dir/package_executables_dict[packagename]).unlink(missing_ok=True)

@catch_keyboard_interrupt
def rewrite():
    config_dir = _default_config_dir()
    install_dir = _default_install_dir()
    _validate_config_dir(config_dir)

    package_names, package_profiles_dict, package_executables_dict = _load_package_info(config_dir)

    enabled_packages = [
        packagename for packagename in package_names
        if (install_dir/package_executables_dict[packagename]).is_file()
    ]

    if not enabled_packages:
        print_warning(_('No hay ningún ejecutable instalado para recargar'))
        return

    for packagename in enabled_packages:
        _write_executable(packagename, config_dir, package_profiles_dict, package_executables_dict, install_dir)
