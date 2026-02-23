import os
import sys
import time
import json
from string import Template
from glob import has_magic as has_glob
from subprocess import call, check_output, CalledProcessError
from abspathlib import AbsPath, NotAbsolutePathError
from clinterface import *

from .i18n import _
from .queue import submitjob, dispatchedjob
from .shared import names, nodes, syspaths, config, options, environ, settings, script, interpolationdict, parameterfiles, parameterdirs
from .utils import ConfigTemplate, InterpolationTemplate, ArgGroups, booleans, option, collect_matches, template_parse
from .readmol import readmol, molblock

truthy_options = ['si', 'yes']
falsy_options = ['no']

def configure_submission():

    script.meta = []
    script.vars = []
    script.config = []
    script.body = []
    parameterpaths = []

    try:
        settings.delay = float(config.delay)
    except ValueError:
        print_error_and_exit(_('El tiempo de espera no es numérico'), delay=config.delay)

    if not syspaths.usrdir.exists():
        syspaths.usrdir.mkdir()
    elif syspaths.usrdir.is_file():
        print_warning(_('No se puede crear el directorio de trabajo {usrdir} porque existe un archivo con el mismo nombre'), usrdir=syspaths.usrdir)

    if syspaths.usrconfdir.is_file():
        try:
            with open(syspaths.usrconfdir, 'r') as f:
                config.update(json.load(f))
        except json.JSONDecodeError as e:
            print_warning(_('El archivo de configuración {file} contiene JSON inválido'), file=syspaths.usrconfdir, error=str(e))

    try:
        config.packagename
    except AttributeError:
        print_error_and_exit(_('No se definió el nombre del programa'))

    try:
        names.cluster = config.clustername
    except AttributeError:
        print_error_and_exit(_('No se definió el nombre del clúster'))

    try:
        nodes.head = config.headnode
    except AttributeError:
        print_error_and_exit(_('No se definió el nombre del nodo maestro'))

    try:
        environ.TELEGRAM_BOT_URL = os.environ['TELEGRAM_BOT_URL']
        environ.TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
    except KeyError:
        pass

#    for key, path in options.restartfiles.items():
#        if not path.is_file():
#            print_error_and_exit(_('El archivo de reinicio {path} no existe'), path=path)

    if options.remote.remote_host:
        if not (syspaths.sshdir).is_dir():
            print_error_and_exit(_('El directorio de configuración de SSH no existe'), path=syspaths.sshdir)
        syspaths.sshsocket = syspaths.sshdir/options.remote.remote_host%'sock'
        try:
            remoteroot = check_output(['ssh', '-o', 'ControlMaster=auto', '-o', 'ControlPersist=60', '-S', syspaths.sshsocket, \
                options.remote.remote_host, 'printenv JOBRUN_REMOTE_ROOT || true']).strip().decode(sys.stdout.encoding)
        except CalledProcessError as e:
            print_error_and_exit(_('No se pudo conectar con el servidor {host}'), host=options.remote.remote_host, error=e.output.decode(sys.stdout.encoding).strip())
        if remoteroot:
            syspaths.remotehomedir = AbsPath(remoteroot) / (names.user + '@' + nodes.head)
        else:
            print_error_and_exit(_('El servidor {host} no está configurado para aceptar trabajos'), host=options.remote.remote_host)

    if 'parameterpaths' in config:
        if isinstance(config.parameterpaths, list):
            if 'parameterset' in options:
                optiondict = collect_matches(config.parameterpaths)
                parameterpaths.append(AbsPath(optiondict[options.parameterset]))
        elif isinstance(config.parameterpaths, dict):
            for key in options.parametersets:
                optiondict = collect_matches(config.parameterpaths[key])
                parameterpaths.append(AbsPath(optiondict[options.parametersets[key]]))

    interpolationdict.update(options.interpolvars)

    for i, var in enumerate(options.interpolation.posvars, start=1):
        interpolationdict[str(i)] = var

    if options.interpolation.mol:
        for i, path in enumerate(options.interpolation.mol, start=1):
            path = AbsPath(path, relto=options.common['in'])
            coords = readmol(path)[-1]
            interpolationdict[f'mol{i}'] = molblock(coords, config.programspec)

    if options.interpolation.prefix:
        try:
            settings.prefix = InterpolationTemplate(options.interpolation.prefix).substitute(interpolationdict)
        except ValueError as e:
            print_error_and_exit(_('El prefijo contiene variables de interpolación inválidas'), prefix=options.interpolation.prefix, key=e.args[0])
        except KeyError as e:
            print_error_and_exit(_('El prefijo contiene variables de interpolación indefinidas'), prefix=options.interpolation.prefix, key=e.args[0])
    else:
        settings.prefix = None

    if interpolationdict and not options.interpolation.prefix:
        if len(options.interpolation.mol) == 1:
            settings.prefix = AbsPath(options.interpolation.mol[0], relto=options.common['in']).stem
        elif len(options.interpolation.mol) == 0:
            print_error_and_exit(_('Se debe especificar un prefijo o sufijo para interpolar sin un archivo coordenadas'))
        else:
            print_error_and_exit(_('Se debe especificar un prefijo o sufijo para interpolar con más de un archivo de coordenadas'))

    if not 'scratch' in config.defaults:
        print_error_and_exit(_('No se especificó el directorio de escritura predeterminado'))

    if 'scratch' in options.common:
        settings.execdir = AbsPath(options.common.scratch/'$jobid')
    else:
        settings.execdir = AbsPath(ConfigTemplate(config.defaults.scratch).substitute(names))/'$jobid'

    if 'mpilaunch' in config:
        try: config.mpilaunch = booleans[config.mpilaunch]
        except KeyError:
            print_error_and_exit(_('Se requier un valor boolenano'), mpilaunch=config.mpilaunch)
    
    if not config.filekeys:
        print_error_and_exit(_('Se requiere una lista de claves de archivo no vacía'), filekeys=config.filekeys)
    
    if config.inputfiles:
        for key in config.inputfiles:
            if not key in config.filekeys:
                print_error_and_exit(_('{key} está en config.inputfiles pero no en config.filekeys'), key=key)
    else:
        print_error_and_exit(_('Se requiere una lista de archivos de entrada no vacía'), inputfiles=config.inputfiles)
    
    if config.outputfiles:
        for key in config.outputfiles:
            if not key in config.filekeys:
                print_error_and_exit(_('{key} está en config.outputfiles pero no en config.filekeys'), key=key)
    else:
        print_error_and_exit(_('Se requiere una lista de archivos de salida no vacía'), outputfiles=config.outputfiles)

    if options.remote.remote_host:
        return

    ############ Local execution ###########

    if 'jobtype' in config:
        script.meta.append(ConfigTemplate(config.jobtype).substitute(jobtype=config.programspec))

    if 'queue' in options.common:
        script.meta.append(ConfigTemplate(config.queue).substitute(queue=options.common.queue))
    elif 'queue' in config.defaults:
        script.meta.append(ConfigTemplate(config.queue).substitute(queue=config.defaults.queue))

    #TODO MPI support for Slurm
    if config.parallel:
        if config.parallel.lower() == 'none':
            if 'hosts' in options.common:
                for i, item in enumerate(config.serialat):
                    script.meta.append(ConfigTemplate(item).substitute(options.common))
            else:
                for i, item in enumerate(config.serial):
                    script.meta.append(ConfigTemplate(item).substitute(options.common))
        elif config.parallel.lower() == 'omp':
            if 'hosts' in options.common:
                for i, item in enumerate(config.singlehostat):
                    script.meta.append(ConfigTemplate(item).substitute(options.common))
            else:
                for i, item in enumerate(config.singlehost):
                    script.meta.append(ConfigTemplate(item).substitute(options.common))
            script.body.append(f'OMP_NUM_THREADS={options.common.nproc}')
        elif config.parallel.lower() == 'mpi':
            if 'hosts' in options.common:
                for i, item in enumerate(config.multihostat):
                    script.meta.append(ConfigTemplate(item).substitute(options.common))
            else:
                for i, item in enumerate(config.multihost):
                    script.meta.append(ConfigTemplate(item).substitute(options.common))
            if 'mpilib' in config:
                if config.mpilib in config.mpirun:
                    script.body.append(ConfigTemplate(config.mpirun[config.mpilib]).substitute(options.common))
                elif config.mpilib == 'builtin':
                    pass
                else:
                    print_error_and_exit(_('Libreríá MPI no soportada'), mpilib=config.mpilib)
            else:
                print_error_and_exit(_('No se especificó la biblioteca MPI del programa (mpilib)'))
        else:
            print_error_and_exit(_('Tipo de paralelización no soportado'), parallel=config.parallel)
    else:
        print_error_and_exit(_('No se especificó el tipo de paralelización del programa (parallel)'))

    if not config.versions:
        print_error_and_exit(_('Se requiere una lista de versiones no vacía'), versions=config.versions)

    for version in config.versions:
        if not 'executable' in config.versions[version]:
            print_error_and_exit(_('No se especificó el ejecutable del programa'), version=version)
    
    for version in config.versions:
        config.versions[version].update({'load':[], 'source':[], 'export':{}})

    prompt = _('Seleccione una versión:')

    if 'version' in options.common:
        if options.common.version not in config.versions:
            print_error_and_exit(_('La versión especificada {version} no es válida'), version=options.common.version)
        settings.version = options.common.version
    elif len(config.versions) == 1:
        settings.version = next(iter(config.versions))
    else:
        if 'version' in config.defaults:
            if not config.defaults.version in config.versions:
                print_error_and_exit(_('La versión predeterminada {version} no es válida'), version=config.defaults.version)
            settings.version = select_option(prompt, list(config.versions.keys()), config.defaults.version)
        else:
            settings.version = select_option(prompt, list(config.versions.keys()))

    ############ Interactive parameter selection ###########

    if 'parameterpaths' in config:
        if isinstance(config.parameterpaths, list):
            if 'parameterset' not in options:
                if not has_glob(config.parameterpaths[0]):
                    parameterpaths.append(AbsPath(config.parameterpaths[0]))
                else:
                    optiondict = collect_matches(config.parameterpaths)
                    if len(optiondict) >= 1:
                        prompt = _('Seleccione un conjunto de parámetros:')
                        parameterpaths.append(AbsPath(select_option(prompt, optiondict)))
                    else:
                        print_error_and_exit(_('No matching parameter set found'))
        elif isinstance(config.parameterpaths, dict):
            for key in config.parametersets:
                if key not in options.parametersets:
                    if len(config.parameterpaths[key]) == 1 and not has_glob(config.parameterpaths[key][0]):
                        parameterpaths.append(AbsPath(config.parameterpaths[key][0]))
                    else:
                        optiondict = collect_matches(config.parameterpaths[key])
                        if len(optiondict) >= 1:
                            prompt = _('Seleccione un conjunto de parámetros:')
                            parameterpaths.append(AbsPath(select_option(prompt, optiondict)))
                        else:
                            print_error_and_exit(_('No matching parameter set found'))

    for path in parameterpaths:
        if path.is_file():
            parameterfiles.append(path)
        elif path.is_dir():
            parameterdirs.append(path)
        elif path.exists():
            print_error_and_exit(_('$path does not exist', path=path))
        else:
            print_error_and_exit(_('$path is not a regular file', path=path))

    ############ End of interactive parameter selection ###########

    try:
        script.body.append(AbsPath(ConfigTemplate(config.versions[settings.version].executable).substitute(names)))
    except NotAbsolutePathError:
        script.body.append(config.versions[settings.version].executable)

    for i, path in enumerate(config.logfiles):
        script.meta.append(ConfigTemplate(path).safe_substitute(dict(logdir=AbsPath(ConfigTemplate(config.logdir).substitute(names)))))

    for key, value in config.export.items():
        if value:
            script.config.append(f'export {key}={value}')
        else:
            print_error_and_exit(_('La variable config.export[{key}] no está definida'), key=key)

    for key, value in config.versions[settings.version].export.items():
        if value:
            script.config.append(f'export {key}={value}')
        else:
            print_error_and_exit(_('La variable config.export[{key}] no está definida'), key=key)

    for i, path in enumerate(config.source + config.versions[settings.version].source):
        if path:
            script.config.append(f'source {AbsPath(ConfigTemplate(path).substitute(names))}')
        else:
            print_error_and_exit(_('La ruta del script de entorno no está definida'))

    if config.load or config.versions[settings.version].load:
        script.config.append('module purge')

    for i, module in enumerate(config.load + config.versions[settings.version].load):
        if module:
            script.config.append(f'module load {module}')
        else:
            print_error_and_exit(_('El nombre del módulo de entorno no está definido'))

    for key, value in config.envars.items():
        script.vars.append(f'{key}="{value}"')

    script.vars.append("totram=$(free | awk 'NR==2{print $2}')")
    script.vars.append("totproc=$(getconf _NPROCESSORS_ONLN)")
    script.vars.append("maxram=$(($totram*$nproc/$totproc))")

    for key, value in config.filevars.items():
        script.vars.append(f'{key}="{config.filekeys[value]}"')

    for key, value in names.items():
        script.vars.append(f'{key}name="{value}"')

    for key, value in nodes.items():
        script.vars.append(f'{key}node="{value}"')

    for key in config.optargs:
        if not config.optargs[key] in config.filekeys:
            print_error_and_exit(_('{key} está en config.optargs pero no en config.filekeys'), key=key)
        script.body.append(f'-{key} {config.filekeys[config.optargs[key]]}')
    
    for item in config.posargs:
        for key in item.split('|'):
            if not key in config.filekeys:
                print_error_and_exit(_('{key} está en config.posargs pero no en config.filekeys'), key=key)
        script.body.append(f"@({'|'.join(config.filekeys[i] for i in item.split('|'))})")
    
    if 'stdinfile' in config:
        try:
            script.body.append(f'0< {config.filekeys[config.stdinfile]}')
        except KeyError:
            print_error_and_exit(_('{stdinfile} no está en config.filekeys'), stdinfile=config.stdinfile)

    if 'stdoutfile' in config:
        try:
            script.body.append(f'1> {config.filekeys[config.stdoutfile]}')
        except KeyError:
            print_error_and_exit(_('{stdoutfile} no está en config.filekeys'), stdoutfile=config.stdoutfile)

    if 'stderrfile' in config:
        try:
            script.body.append(f'2> {config.filekeys[config.stderrfile]}')
        except KeyError:
            print_error_and_exit(_('{stderrfile} no está en config.filekeys'), stderrfile=config.stderrfile)
    
    script.chdir = 'cd "{}"'.format

    if config.filesync == 'local':
        script.makedir = 'mkdir -p -m 700 "{}"'.format
        script.removedir = 'rm -rf "{}"'.format
        script.importfile = 'cp "{}" "{}"'.format
        script.importdir = 'cp -r "{}/." "{}"'.format
        script.exportfile = 'if test -f "{0}"; then rm -f "{1}"; cp "{0}" "{1}"; fi'.format
    elif config.filesync == 'remote':
        script.makedir = 'for host in ${{hosts[*]}}; do rsh $host mkdir -p -m 700 "\'{}\'"; done'.format
        script.removedir = 'for host in ${{hosts[*]}}; do rsh $host rm -rf "\'{}\'"; done'.format
        script.importfile = 'for host in ${{hosts[*]}}; do rcp $headnode:"\'{0}\'" $host:"\'{1}\'"; done'.format
        script.importdir = 'for host in ${{hosts[*]}}; do rsh $host cp -r "\'{0}/.\'" "\'{1}\'"; done'.format
        script.exportfile = 'if test -f "{0}"; then rsh $headnode "rm -f \'{1}\'"; rcp "{0}" $headnode:"\'{1}\'"; fi'.format
    elif config.filesync == 'secure':
        script.makedir = 'for host in ${{hosts[*]}}; do ssh $host mkdir -p -m 700 "\'{}\'"; done'.format
        script.removedir = 'for host in ${{hosts[*]}}; do ssh $host rm -rf "\'{}\'"; done'.format
        script.importfile = 'for host in ${{hosts[*]}}; do scp $headnode:"\'{0}\'" $host:"\'{1}\'"; done'.format
        script.importdir = 'for host in ${{hosts[*]}}; do ssh $host cp -r "\'{0}/.\'" "\'{1}\'"; done'.format
        script.exportfile = 'if test -f "{0}"; then ssh $headnode "rm -f \'{1}\'"; scp "{0}" $headnode:"\'{1}\'"; fi'.format
    else:
        print_error_and_exit(_('El método de copia no es válido'), filesync=config.filesync)

def submit_single_job(indir, inputname, filtergroups):

    if settings.prefix is None:
        jobname = inputname
    else:
        jobname = settings.prefix + '_' + inputname

    script.vars.append(f'jobname="{jobname}"')
    script.meta.append(ConfigTemplate(config.jobname).substitute(jobname=jobname))

    if 'out' in options.common:
        outdir = AbsPath(options.common.out, relto=syspaths.cwd)
    else:
        outdir = AbsPath(jobname, relto=indir)

    literal_inputs = {}
    interpolated_inputs = {}

    if options.common.proxy:
        stagedir = indir
    else:
        if outdir == indir:
            print_failure(_('El directorio de salida debe ser distinto al directorio de trabajo'))
            return
        stagedir = outdir
        for key in config.inputfiles:
            srcpath = indir/inputname%key
            destpath = stagedir/jobname%key
            if srcpath.is_file():
                if interpolationdict and key in config.interpolable:
                    with open(srcpath, 'r') as f:
                        contents = f.read()
                        try:
                            interpolated_inputs[destpath] = InterpolationTemplate(contents).substitute(interpolationdict)
                        except ValueError:
                            print_failure(_('El archivo {file} contiene variables de interpolación inválidas'), file=srcpath, key=e.args[0])
                            return
                        except KeyError as e:
                            print_failure(_('El archivo {file} contiene variables de interpolación sin definir'), file=srcpath, key=e.args[0])
                            return
                else:
                    literal_inputs[destpath] = srcpath

    jobdir = stagedir/'.job'

    if outdir.is_dir():
        if jobdir.is_dir():
            try:
                with open(jobdir/'id', 'r') as f:
                    jobid = f.read()
                if not dispatchedjob(jobid, jobname, outdir):
                    return
            except FileNotFoundError:
                pass
        if not set(outdir.listdir()).isdisjoint(f'{jobname}.{key}' for key in config.outputfiles):
            prompt = _('Si corre este cálculo los archivos de salida existentes en el directorio {outdir} serán sobreescritos, ¿desea continuar de todas formas?').format(outdir=outdir)
            if options.common.no or (not options.common.yes and not complete_binary_choice(prompt, truthy_options, falsy_options)):
                print_failure(_('Cancelado por el usuario'))
                return
        if indir != outdir:
            for ext in config.inputfiles:
                (outdir/jobname%ext).unlink(missing_ok=True)
        for ext in config.outputfiles:
            (outdir/jobname%ext).unlink(missing_ok=True)
    else:
        try:
            outdir.mkdir(parents=True)
        except FileExistsError:
            if outdir.is_file():
                print_failure(_('No se puede crear el directorio {outdir} porque existe un archivo con el mismo nombre'), outdir=outdir)
                return

    for path in literal_inputs:
        literal_inputs[path].copyfile(path)

    for path in interpolated_inputs:
        with open(path, 'w') as file:
            file.write(interpolated_inputs[path])

#    for key, targetfile in options.restartfiles.items():
#        targetfile.symlink_to(stagedir/jobname%config.fileopts[key])

    ############ Remote execution ###########

    if options.remote.remote_host:
        remote_args = ArgGroups()
        remote_in = syspaths.remotehomedir/'input'
        remote_out = syspaths.remotehomedir/'output'
        rel_outdir = os.path.relpath(outdir, syspaths.homedir)
        remote_args.gather(options.common)
        remote_args.flags.add('job')
        remote_args.flags.add('proxy')
        remote_args.options['in'] = remote_in/rel_outdir
        remote_args.options['out'] = remote_out/rel_outdir
        filelist = []
        for key in config.filekeys:
            if (outdir/jobname%key).is_file():
                filelist.append(syspaths.homedir/'.'/rel_outdir/jobname%key)
        arglist = ['ssh', '-qt', '-S', syspaths.sshsocket, options.remote.remote_host]
        arglist.extend(f'{envar}={value}' for envar, value in environ.items())
        arglist.append(names.command)
        arglist.extend(option(key) for key in remote_args.flags)
        arglist.extend(option(key, value) for key, value in remote_args.options.items())
        arglist.extend(option(key, value) for key, listval in remote_args.multoptions.items() for value in listval)
        arglist.append(jobname)
        if options.common.debug:
            print('<FILELIST>')
            print('\n'.join(filelist))
            print('</FILELIST>')
            print('<COMMAND>')
            print('\n'.join(arglist))
            print('</COMMAND>')
        else:
            try:
                check_output(['ssh', '-S', syspaths.sshsocket, options.remote.remote_host, f"mkdir -p '{remote_in}' '{remote_out}'"])
                check_output([f'rsync', '-e', "ssh -S '{syspaths.sshsocket}'", '-qRLtz'] + filelist + [f'{options.remote.remote_host}:{remote_in}'])
                check_output([f'rsync', '-e', "ssh -S '{syspaths.sshsocket}'", '-qRLtz', '-f', '-! */'] + filelist + [f'{options.remote.remote_host}:{remote_out}'])
            except CalledProcessError as e:
                print_error_and_exit(_('Error al copiar los archivos al servidor {host}'), host=options.remote.remote_host, error=e.output.decode(sys.stdout.encoding).strip())
            call(arglist)
        return

    ############ Local execution ###########

    try:
        jobdir.mkdir()
    except FileExistsError:
        if jobdir.is_file():
            print_failure(_('No se puede crear el directorio {jobdir} porque existe un archivo con el mismo nombre'), jobdir=jobdir)
            return

    jobscript = jobdir/'script'

    with open(jobscript, 'w') as f:
        f.write('#!/bin/bash -x' + '\n')
        f.write(''.join(i + '\n' for i in script.meta))
        f.write('shopt -s extglob nullglob' + '\n')
        f.write(''.join(i + '\n' for i in script.vars))
        f.write(''.join(i + '\n' for i in script.config))
        f.write(script.makedir(settings.execdir) + '\n')
        for key in config.inputfiles:
            if (indir/inputname%key).is_file():
                f.write(script.importfile(stagedir/jobname%key, settings.execdir/config.filekeys[key]) + '\n')
    #    for key in options.restartfiles:
    #        f.write(script.importfile(stagedir/jobname%config.fileopts[key], settings.execdir/config.filekeys[config.fileopts[key]]) + '\n')
        for path in parameterfiles:
            f.write(script.importfile(path, settings.execdir/path.name) + '\n')
        for path in parameterdirs:
            f.write(script.importdir(path, settings.execdir) + '\n')
        f.write(script.chdir(settings.execdir) + '\n')
        f.write(''.join(i + '\n' for i in config.prescript))
        f.write(' '.join(script.body) + '\n')
        f.write(''.join(i + '\n' for i in config.postscript))
        for key in config.outputfiles:
            f.write(script.exportfile(settings.execdir/config.filekeys[key], outdir/jobname%key) + '\n')
        f.write(script.removedir(settings.execdir) + '\n')
        f.write(''.join(i + '\n' for i in config.offscript))

    if options.common.debug:

        print_success(_('Se procesó el trabajo "{jobname}" y se generaron los archivos para el envío en el directorio {jobdir}'), jobname=jobname, jobdir=jobdir)

    else:

        try:
            last_time = os.stat(syspaths.usrdir).st_mtime
        except (FileNotFoundError, PermissionError):
            pass
        else:
            wait_time = last_time - time.time() + settings.delay
            if wait_time > 0:
                time.sleep(wait_time)

        try:
            jobid = submitjob(jobscript)
        except RuntimeError as error:
            print_failure(_('El gestor de trabajos reportó un problema al enviar el trabajo {jobname}'), jobname=jobname, error=error)
            return
        else:
            print_success(_('El trabajo "{jobname}" se correrá en {nproc} núcleo(s) en {clustername} con el número {jobid}'), jobname=jobname, nproc=options.common.nproc, clustername=names.cluster, jobid=jobid)
            with open(jobdir/'id', 'w') as f:
                f.write(jobid)
            try: 
                os.utime(syspaths.usrdir, None)
            except (FileNotFoundError, PermissionError):
                pass
