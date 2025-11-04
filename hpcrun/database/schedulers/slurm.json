{
   sbmtcmd: [ "sbatch", "--export=ALL" ],
   statcmd: [ "squeue", "--noheader", "-o%T", "-j" ],
   sbmtregex: ".* ([0-9]+)",
   statregex: "([A-Z_]+)",

   logfiles: [
       "#SBATCH -o '&logdir/%A.out'",
       "#SBATCH -e '&logdir/%A.out'",
   ],

   jobname: "#SBATCH -J '&jobname'",
   jobtype: "#SBATCH --comment='&jobtype'",

   queue: "#SBATCH -p '&queue'",

   serial: [
       "#SBATCH -n '1'",
   ],

   serialat: [
       "#SBATCH -w '&hosts'",
       "#SBATCH -n '1'",
   ],

   singlehost: [
       "#SBATCH -n '&nproc'",
       "#SBATCH -N '1'",
   ],

   singlehostat: [
       "#SBATCH -n '&nproc'",
       "#SBATCH -w '&hosts'",
   ],

   multihost: [
       "#SBATCH -n '&nproc'",
       "#SBATCH -N '&nhost'",
   ],

   multihostat: [
       "#SBATCH -n '&nproc'",
       "#SBATCH -w '&hosts'",
   ],

   envars: {
       jobid: "$SLURM_JOB_ID",
       nproc: "$SLURM_NTASKS",
       hosts: "$(getent hosts $SLURM_JOB_NODELIST | cut -d\\  -f1 | uniq)",
   },
   
   mpirun: {
       openmpi: "mpirun",
       intelmpi: "mpirun",
       mpich: "mpirun",
   },
   
   running_states: [
       "PENDING",
       "RUNNING",
       "SUSPENDED",
       "STOPPED",
       "CONFIGURING",
       "COMPLETING",
       "SIGNALING",
       "RESV_DEL_HOLD",
       "REQUEUE_HOLD",
       "REQUEUED",
   ],
   
   finished_states: [
       "COMPLETED",
       "CANCELLED",
       "PREEMPTED",
       "DEADLINE",
       "TIMEOUT",
       "FAILED",
       "BOOT_FAIL",
       "NODE_FAIL",
       "OUT_OF_MEMORY",
   ],

   ignorederrors: [
      "slurm_load_jobs error: Invalid job id specified",
   ],

}
