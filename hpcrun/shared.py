from os import path
from pwd import getpwnam
from grp import getgrgid
from getpass import getuser 
from abspathlib import AbsPath
from json5conf import JSONConfDict
from os import getcwd

config = JSONConfDict()
options = JSONConfDict()
parameterdict = {}
parameterpaths = []
interpolationdict = {}
script = JSONConfDict()
names = JSONConfDict()
nodes = JSONConfDict()
paths = JSONConfDict()
environ = JSONConfDict()
settings = JSONConfDict()
names.user = getuser()
paths.home = AbsPath(path.expanduser('~'))
paths.rundir = paths.home/'.hpcrun'
paths.runconf = paths.rundir/'config'
paths.sshdir = paths.home/'.ssh'
paths.cwd = getcwd()
