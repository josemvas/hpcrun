import os
import re
import sys
import json
from socket import gethostname
from abspathlib import AbsPath, NotAbsolutePathError
from boolparse import BoolParser
from clinterface.printing import *

from .i18n import _
from .cli import parse_args
from .submission import configure_submission, submit_single_job
from .shared import sysvars, environ, config, options
from .utils import ConfigTemplate, InterpolationTemplate, option, natural_sorted as sorted, catch_keyboard_interrupt, file_except_info

@catch_keyboard_interrupt
def submit_jobs(json_config):

    config.update(json.loads(json_config))
    sysvars.commandname = os.path.basename(sys.argv[0])
    optiondict, argumentlist = parse_args(sysvars.commandname, config)
    options.update(optiondict)
    configure_submission()

    if 'filter' in options.arguments:
        filtere = re.compile(options.arguments.filter)
    else:
        filtere = re.compile('.+')

    for inputfile in argumentlist:
        if options.common.job:
            indir = AbsPath(options.common['in'])
            for key in config.inputfiles:
                if (indir/inputfile%key).is_file():
                    inputname = inputfile
                    break
            else:
                print_failure(_('No hay archivos de entrada con nombre {inputname}'), inputname=inputfile, indir=indir)
                continue
        else:
            try:
                abspath = AbsPath(inputfile)
            except NotAbsolutePathError:
                abspath = AbsPath(options.common['in']) / inputfile
            try:
                abspath.assert_file()
            except Exception as e:
                file_except_info(e, abspath)
                continue
            for key in config.inputfiles:
                if abspath.name.endswith('.' + key):
                    inputname = abspath.name[:-len('.' + key)]
                    break
            else:
                print_failure(_('{file} no es un archivo de entrada de {package_name}'), file=abspath.name, package_name=config.packagename)
                continue
            indir = abspath.parent
        filestatus = {}
        for key in config.filekeys:
            abspath = indir/inputname%key
            filestatus[key] = abspath.is_file() #or key in options.restartfiles
        conflict = False
        for boolexpr, message in config.conflicts.items():
            if BoolParser(boolexpr).evaluate(filestatus):
                print_failure(message, file=inputname)
                conflict = True
        if conflict:
            continue
        matched = filtere.fullmatch(inputname)
        if matched:
            filtergroups = {str(i): x for i, x in enumerate(matched.groups())}
            submit_single_job(indir, inputname, filtergroups)

#if __name__ == '__main__':
#    run()
