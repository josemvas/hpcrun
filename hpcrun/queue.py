import os
import re
import sys
from subprocess import Popen, PIPE
from clinterface.printing import *
from .shared import config

def submitjob(jobscript):
    with open(jobscript, 'r') as fh:
        process = Popen(config.sbmtcmd, stdin=fh, stdout=PIPE, stderr=PIPE, close_fds=True)
    output, error = process.communicate()
    output = output.decode(sys.stdout.encoding).strip()
    error = error.decode(sys.stdout.encoding).strip()
    if process.returncode == 0:
        return re.fullmatch(config.sbmtregex, output).group(1)
    else:
        raise RuntimeError(error)
        
def dispatchedjob(jobid, jobname, outdir):
    process = Popen(config.statcmd + [jobid], stdout=PIPE, stderr=PIPE, close_fds=True)
    output, error = process.communicate()
    output = output.decode(sys.stdout.encoding).strip()
    error = error.decode(sys.stdout.encoding).strip()
    if process.returncode == 0:
        if not output:
            return True, None
        match = re.fullmatch(config.statregex, output)
        if match is None:
            print_failure('El trabajo "{jobname}" no se envió porque no se pudo determinar su estado', jobname=jobname, output=output)
            return False
        if match.group(1) in config.finished_states:
            return True, None
        elif match.group(1) in config.running_states:
            print_failure('El trabajo "{jobname}" no se envió porque hay otro trabajo escribiendo en el directorio {outdir}', jobname=jobname, outdir=outdir)
            return False
        else:
            print_failure('El trabajo "{jobname}" no se envió porque tiene un código de estado desconocido', status=match.group(1))
            return False
    else:
        for regex in config.ignorederrors:
            if re.fullmatch(regex, error):
                return True, None
        print_failure('El trabajo "{jobname}" no se envió porque ocurrió un error al consultar su estado', jobname=jobname, error=error)
        return False
