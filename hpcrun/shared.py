from os import path
from pwd import getpwnam
from grp import getgrgid
from getpass import getuser 
from abspathlib import AbsPath
from json5conf import JSONConfDict
from os import getcwd

config = JSONConfDict()
options = JSONConfDict()
parameterfiles = []
parameterdirs = []
interpolationdict = {}
script = JSONConfDict()
names = JSONConfDict()
nodes = JSONConfDict()
environ = JSONConfDict()
settings = JSONConfDict()
names.user = getuser()

syspaths = JSONConfDict()
syspaths.homedir = AbsPath(path.expanduser('~'))
syspaths.usrdir = syspaths.homedir/'.hpcrun'
syspaths.usrconfdir = syspaths.usrdir/'config.json'
syspaths.sshdir = syspaths.homedir/'.ssh'
syspaths.cwd = getcwd()
