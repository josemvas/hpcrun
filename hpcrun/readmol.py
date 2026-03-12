from clinterface.printing import *
from .i18n import _
#from logging import WARNING

class ParseError(Exception):
    def __init__(self, *message):
        super().__init__(' '.join(message))

def molblock(coords, jobspec):
    if jobspec in ('gaussian', 'demon2k'):
        return '\n'.join('{:<2s}  {:10.4f}  {:10.4f}  {:10.4f}'.format(*line) for line in coords)
    elif jobspec in ('dftbplus'):
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
        print_error_and_exit(_('Formato desconocido: {format}'), format=jobspec)

def readmol(molfile):
    if molfile.is_file():
        with open(molfile, mode='r') as fh:
            if molfile.suffix in ('.mol', '.sdf'):
                try:
                    return parsemdl(fh)
                except ParseError:
                    try:
                        return parsexyz(fh)
                    except ParseError:
                        print_error_and_exit(_('{file} no es un archivo de coordenadas válido'), file=molfile)
            elif molfile.suffix == '.xyz':
                try:
                    return parsexyz(fh)
                except ParseError:
                    print_error_and_exit(_('{file} no es un archivo XYZ válido'), file=molfile)
            elif molfile.suffix == '.mol2':
                try:
                    return parsemol2(fh)
                except ParseError:
                    print_error_and_exit(_('{file} no es un archivo MOL2 válido'), file=molfile)
            elif molfile.suffix == '.log':
                try:
                    return parseglf(fh)
                except ParseError:
                    print_error_and_exit(_('{file} no es un archivo de salida de gaussian válido'), file=molfile)
            else:
                print_error_and_exit(_('Solamente se pueden leer archivos mol, sdf, mol2, xyz y log'))
    elif molfile.is_dir():
        print_error_and_exit(_('El archivo {file} es un directorio'), file=molfile)
    elif molfile.exists():
        print_error_and_exit(_('El archivo {file} no es regular'), file=molfile)
    else:
        print_error_and_exit(_('El archivo {file} no existe'), file=molfile)

def parsexyz(fh):
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
            for _ in range(natom):
                e, x, y, z, *_ = next(fh).split()
                coords.append((e, float(x), float(y), float(z)))
        except StopIteration:
            raise ParseError(_('Unexpected end of file'))
        trajectory.append(coords)

def parsemdl(fh):
    """Parse MDL molfile (V2000 or V3000) or SDF containing multiple records."""
    fh.seek(0)
    trajectory = []
    while True:
        coords = _read_mdl_record(fh)
        if coords is None:
            break
        trajectory.append(coords)
    if not trajectory:
        raise ParseError(_('No valid MDL records found'))
    return trajectory

def _read_mdl_record(fh):
    """Read a single MDL/SDF record (V2000 or V3000). Returns coords list or None at EOF."""
    # Skip blank lines between records and read the title line
    title = None
    for line in fh:
        if line.strip():
            title = line
            break
    if title is None:
        return None  # EOF

    try:
        metadata = next(fh)
        comment  = next(fh)
        counts   = next(fh)
    except StopIteration:
        raise ParseError(_('Unexpected end of file'))

    parts = counts.split()
    if not parts:
        raise ParseError(_('Invalid format'))

    # Detect version
    version = parts[-1].strip().upper() if parts[-1].strip().upper() in ('V2000', 'V3000') else 'V2000'

    if version == 'V3000':
        coords = _parse_v3000_ctab(fh)
    else:
        coords = _parse_v2000_ctab(counts, fh)

    # Consume the rest of the record up to $$$$ (SDF) or EOF
    for line in fh:
        if line.startswith('$$$$'):
            break

    return coords

def _parse_v2000_ctab(counts_line, fh):
    """Parse the atom block of a V2000 CTAB given the counts line and open file handle."""
    parts = counts_line.split()
    try:
        natom = int(parts[0])
        nbond = int(parts[1])
    except (IndexError, ValueError):
        raise ParseError(_('Invalid format'))

    coords = []
    try:
        for _ in range(natom):
            fields = next(fh).split()
            x, y, z, e = fields[0], fields[1], fields[2], fields[3]
            coords.append((e, float(x), float(y), float(z)))
        for _ in range(nbond):
            next(fh)
    except StopIteration:
        raise ParseError(_('Unexpected end of file'))

    # Validate remaining property lines
    for line in fh:
        stripped = line.strip()
        if not stripped or stripped == 'M  END':
            break
        if stripped.startswith('$$$$'):
            break
        if not stripped.startswith('M '):
            raise ParseError(_('Invalid format'))

    return coords

def _parse_v3000_ctab(fh):
    """Parse a V3000 CTAB atom block from an open file handle."""
    coords = []
    in_atom_block = False
    try:
        for line in fh:
            stripped = line.strip()
            upper = stripped.upper()
            if upper == 'M  V30 BEGIN ATOM':
                in_atom_block = True
            elif upper == 'M  V30 END ATOM':
                in_atom_block = False
            elif upper in ('M  V30 END CTAB', 'M  END'):
                break
            elif in_atom_block:
                # Handle line continuations (trailing '-')
                full = stripped
                while full.endswith('-'):
                    full = full[:-1] + next(fh).strip()
                # M  V30 <index> <element> <x> <y> <z> ...
                parts = full.split()
                if len(parts) < 6:
                    raise ParseError(_('Invalid V3000 atom line'))
                # parts: M V30 idx element x y z ...
                e, x, y, z = parts[3], parts[4], parts[5], parts[6]
                coords.append((e, float(x), float(y), float(z)))
    except StopIteration:
        raise ParseError(_('Unexpected end of file'))

    if not coords:
        raise ParseError(_('No atoms found in V3000 CTAB'))
    return coords

def parsemol2(fh):
    """Parse a Tripos MOL2 file, which may contain multiple molecules."""
    fh.seek(0)
    trajectory = []
    coords = []
    in_atom_block = False

    for line in fh:
        stripped = line.strip()
        if stripped.startswith('@<TRIPOS>MOLECULE'):
            # Save any previously accumulated molecule
            if coords:
                trajectory.append(coords)
                coords = []
            in_atom_block = False
        elif stripped.startswith('@<TRIPOS>ATOM'):
            in_atom_block = True
        elif stripped.startswith('@<TRIPOS>'):
            # Any other section ends the atom block
            in_atom_block = False
        elif in_atom_block and stripped:
            # atom_id atom_name x y z atom_type [subst_id subst_name charge]
            parts = stripped.split()
            if len(parts) < 5:
                raise ParseError(_('Invalid MOL2 atom line'))
            # atom_type is the 6th field (index 5) if present; fall back to atom_name
            raw_type = parts[5] if len(parts) > 5 else parts[1]
            # Tripos atom types look like "C.3", "N.am", "O.2" — keep only element symbol
            element = raw_type.split('.')[0].capitalize()
            x, y, z = parts[2], parts[3], parts[4]
            coords.append((element, float(x), float(y), float(z)))

    if coords:
        trajectory.append(coords)

    if not trajectory:
        raise ParseError(_('No valid MOL2 records found'))
    return trajectory

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
    return [[(pt.element[data.atomnos[i]], e[0], e[1], e[2]) for i, e in enumerate(data.atomcoords[-1])]]