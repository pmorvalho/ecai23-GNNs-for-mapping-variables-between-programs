#!/usr/bin/env bash
#Title			: config_gnn.sh
#Usage			: bash config_gnn.sh
#Author			: pmorvalho
#Date			: July 29, 2022
#Description		: Jelle's commands to config the GNN's environment, plus the python packages needed to run MultIPAs
#Notes			: 
# (C) Copyright 2022 Pedro Orvalho.
#==============================================================================

#!/usr/bin/env bash
source ~/anaconda3/etc/profile.d/conda.sh
conda create -n gnn_env python=3.9
conda activate gnn_env
#conda install pytorch torchvision torchaudio cpuonly -c pytorch
#pip3 install torch torchvision torchaudio
pip install torch==1.11.0+cpu torchvision==0.12.0+cpu torchaudio==0.11.0 --extra-index-url https://download.pytorch.org/whl/cpu
# check with nvidia-smi if the 'cu102' should be replaced with another cuda version
pip install torch-scatter torch-sparse torch-cluster torch-spline-conv torch-geometric -f https://data.pyg.org/whl/torch-1.11.0+cpu.html
pip install pycparser==2.21
conda activate gnn_env


