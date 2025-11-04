About
-----
**HPCRun** is a configurable tool to run simulation jobs in HPC clusters. It is compatible with PBS, LSF and Slurm and currently supports the following simulation software:

* DFTB+
* Gaussian
* deMon2k
* ORCA
* VASP

Install
-------
Install from GitHub with pip
```
pip3 install --user git+https://github.com/josemvas/hpcrun.git
```

Configuration
-------------
To setup create a file `cluster_profile.json` and a directory `package_profiles` and run
```
hpcrun-setup
```
and follow the instructions printed on the screen.

To update the configuration edit `cluster_profile.json` and/or `package_profiles` and run
```
hpcrun-reload
```

Upgrade
-------
Upgrade from GitHub with pip
```
pip3 install --user --upgrade git+https://github.com/josemvas/hpcrun.git
```

Notes
-----
For system wide installation drop the `--user` option.
