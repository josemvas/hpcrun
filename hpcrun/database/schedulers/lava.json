{
   sbmtcmd: [ "bsub" ],
   statcmd: [ "bjobs", "-ostat", "-noheader" ],
   sbmtregex: ".*<([0-9]+)>.*",
   statregex: "([A-Z]+)",

   logfiles: [
      "#BSUB -o '&logdir/%J.out'",
      "#BSUB -e '&logdir/%J.out'",
   ],

   jobname: "#BSUB -J '&jobname'",
   jobtype: "#BSUB -P '&jobtype'",

   queue: "#BSUB -q '&queue'",

   serial: [
      "#BSUB -n '1'",
   ],

   serialat: [
      "#BSUB -m '&hosts'",
      "#BSUB -n '1'",
   ],

   singlehost: [
      "#BSUB -n '&nproc'",
      "#BSUB -R 'span[hosts=1]'",
   ],

   singlehostat: [
      "#BSUB -n '&nproc'",
      "#BSUB -m '&hosts'",
   ],

   multihost: [
      "#BSUB -n '&nproc'",
      "#BSUB -R 'span[hosts=&nhost]'",
   ],

   multihostat: [
      "#BSUB -n '&nproc'",
      "#BSUB -m '&hosts'",
   ],

   envars: {
      jobid: "$LSB_JOBID",
      nproc: "$(echo $LSB_HOSTS | wc -w)",
      hosts: "$(printf '%s\\n' $LSB_HOSTS | uniq)",
   },
    
   mpirun: {
      openmpi: "openmpi-mpirun",
      intelmpi: "impi-mpirun",
      mpich: "mpich-mpirun",
   },

   running_states: [
      "PEND",
      "RUN",
      "PSUSP",
      "USUSP",
      "SSUSP",
   ],

   finished_states: [
      "DONE",
      "EXIT",
   ],

   ignorederrors: [
      "Job <[0-9]+> is not found",
   ],

}
