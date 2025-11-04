from clinterface.printing import *
from .i18n import _
#from logging import WARNING

class ParseError(Exception):
    def __init__(self, *message):
        super().__init__(' '.join(message))

def molblock(coords, programspec):
    if programspec in ('gaussian', 'demon2k'):
        return '\n'.join('{:<2s}  {:10.4f}  {:10.4f}  {:10.4f}'.format(*line) for line in coords)
    elif programspec in ('dftbplus'):
        atoms = []
        blocklines = []
        for line in coords:
            if not line[0] in atoms:
                atoms.append(line[0])
        blocklines.append(f'{len(coords):5} C')
        blocklines.append(' '.join(atoms))
        for i, line in enumerate(coords, start=1):
            blocklines.append(f'{i:5}  {atoms.index(line[0])+1:3}  {line[1]:10.4f}  {line[2]:10.4f}  {line[3]:10.4f}')
        return '\n'.join(blocklines)
    else:
        print_error_and_exit(_('Formato desconocido: {format}'), format=molformat)

def readmol(molfile):
# Guess format and read molfile
    if molfile.is_file():
        with open(molfile, mode='r') as fh:
            if molfile.has_suffix('.mol'):
                try:
                    return parsemdl(fh)
                except ParseError:
                    try:
                        return parsexyz(fh)
                    except ParseError:
                        print_error_and_exit(_('{file} no es un archivo de coordenadas válido'), file=molfile)
            elif molfile.has_suffix('.xyz'):
                try:
                    return parsexyz(fh)
                except ParseError as e:
                    print_error_and_exit(_('{file} no es un archivo XYZ válido'), file=molfile)
            elif molfile.has_suffix('.log'):
                try:
                    return parseglf(fh)
                except ParseError:
                    print_error_and_exit(_('{file} no es un archivo de salida de gaussian válido'), file=molfile)
            else:
                print_error_and_exit(_('Solamente se pueden leer archivos mol, xyz y log'))
    elif molfile.is_dir():
        print_error_and_exit(_('El archivo {file} es un directorio'), file=molfile)
    elif molfile.exists():
        print_error_and_exit(_('El archivo {file} no es regular'), file=molfile)
    else:
        print_error_and_exit(_('El archivo {file} no existe'), file=molfile)

def parsexyz(fh):
# Parse XYZ molfile
    fh.seek(0)
    trajectory = []
    while True:
        coords = []
        try:
            natom = next(fh)
        except StopIteration:
            if trajectory:
                return trajectory
            else:
                print_error_and_exit(_('El archivo de coordenadas está vacío'))
        try:
            natom = int(natom)
        except ValueError:
            raise ParseError(_('Invalid format'))
        try:
            title = next(fh)
            for line in range(natom):
                e, x, y, z, *_ = next(fh).split()
                coords.append((e, float(x), float(y), float(z)))
        except StopIteration:
            raise ParseError(_('Unexpected end of file'))
        trajectory.append(coords)

# Parse MDL molfile
def parsemdl(fh):
    fh.seek(0)
    coords = []
    try:
        title = next(fh)
    except StopIteration:
        print_error_and_exit(_('El archivo de coordenadas está vacío'))
    try:
        metadata = next(fh)
        comment = next(fh)
        natom, nbond, *_ = next(fh).split()
        try:
            natom = int(natom)
            nbond = int(nbond)
        except ValueError:
            raise ParseError(_('Invalid format'))
        for _ in range(natom):
            x, y, z, e, *_ = next(fh).split()
            coords.append((e, float(x), float(y), float(z)))
        for _ in range(nbond):
            next(fh)
    except StopIteration:
        raise ParseError(_('Unexpected end of file'))
    for line in fh:
        if line.split()[0] != 'M':
            raise ParseError(_('Invalid format'))
    return [coords]

# Parse Gaussian logfile
def parseglf(fh):
    try:
        import cclib
    except ImportError:
        print_error_and_exit(_('Debe instalar cclib para poder leer el archivo de coordenadas'))
    logfile = cclib.io.ccopen(fh)
#    logfile = cclib.io.ccopen(fh, loglevel=WARNING)
    try:
        data = logfile.parse()
    except Exception:
        raise ParseError(_('Invalid format'))
    pt = cclib.parser.utils.PeriodicTable()
    return [(pt.element[data.atomnos[i]], e[0], e[1], e[2]) for i, e in enumerate(data.atomcoords[-1])]
