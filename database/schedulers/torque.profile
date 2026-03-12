{
   sbmtcmd: [ "qsub", "-V" ],
   statcmd: [ "qstat", "-x" ],
   sbmtregex: "([0-9]+)\\.[^.]+",
   statregex: ".*<job_state>([A-Z])</job_state>.*",

   logfiles: [
      "#PBS -o '&logdir/%J.out'",
      "#PBS -e '&logdir/%J.out'",
   ],

   jobname: "#PBS -N '&jobname'",

   queue: "#PBS -q '&queue'",

   serial: [
      "#PBS -l 'nodes=1:ppn=1'",
   ],

   serialat: [
      "#PBS -l 'nodes=&hosts:ppn=1'",
   ],

   singlehost: [
      "#PBS -l 'nodes=1:ppn=&nproc'",
   ],

   singlehostat: [
      "#PBS -l 'nodes=&hosts:ppn=&nproc'",
   ],

   multihost: [
      "#PBS -l 'nodes=&nhost:ppn=&nproc'",
   ],

   multihostat: [
      "#PBS -l 'nodes=&hosts:ppn=&nproc'",
   ],

   envars: {
      jobid: "$PBS_JOBID",
      nproc: "$(expr $PBS_NUM_NODES \\* $PBS_NUM_PPN)",
      hosts: "$(printf '%s\\n' $PBS_NODEFILE | uniq)",
   },
    
   mpirun: {
      openmpi: "mpirun -np %nproc",
      intelmpi: "mpirun -np %nproc",
      mpich: "mpirun -np %nproc",
   },
    
   running_states: [
      "Q",
      "R",
      "H",
      "S",
      "W",
      "T",
      "E",
   ],
    
   finished_states: [
      "C",
   ],

   ignorederrors: [
      "qstat: Unknown Job Id Error [0-9]+\\.[^.]+",
   ],

}
