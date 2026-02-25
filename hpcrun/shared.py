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
environ = JSONConfDict()
settings = JSONConfDict()

sysvars = JSONConfDict()
sysvars.username = getuser()
sysvars.usrsshdir = AbsPath('~/.ssh')
sysvars.usrhpcdir = AbsPath('~/.hpcrun')
sysvars.usrhpcconf = sysvars.usrhpcdir/'config.json'
