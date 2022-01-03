#!/bin/bash
#
#SBATCH --job-name=mip-pyomo
#SBATCH --output=output_slurm.log
#SBATCH --error=error_slurm.log
#
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --time=24:00:00
#SBATCH --mem-per-cpu=1000


cpu=24
spath='/home/umons/math/arosati/mip-pyomo-glpk/pyomo'
wpath='/home/umons/math/arosati/mip-pyomo-glpk/pyomo/output'
wdata='/home/umons/math/arosati/mip-pyomo-glpk/data/data.json'

srun python3 -u /home/umons/math/arosati/mip-pyomo-glpk/pyomo/runner.py ${cpu} ${spath} ${wpath} ${wdata} 2>&1 output.log