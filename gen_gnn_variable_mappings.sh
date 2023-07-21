#!/usr/bin/env bash
#Title			: gen_gnn_variable_mappings.sh
#Usage			: bash gen_gnn_variable_mappings.sh
#Author			: pmorvalho
#Date			: July 29, 2022
#Description		: Generates a var mapping for each pair of incorrect/correct programs in the eval dataset using the GNN  
#Notes			: 
# (C) Copyright 2022 Pedro Orvalho.
#==============================================================================

# to activate clara python-environment
if [ -f ~/opt/anaconda3/etc/profile.d/conda.sh ]; then
  # if running on MacOS
    source ~/opt/anaconda3/etc/profile.d/conda.sh
else
  # if running on ARSR Machines (Linux)
    source ~/anaconda3/etc/profile.d/conda.sh
fi

conda activate gnn_env

initial_dir=$(pwd)
data_dir="eval-dataset"
gnn_models_dir="gnn_models"
var_maps_dir=$initial_dir"/variable_mappings"
TIMEOUT_REPAIR=600 # in seconds 

#labs=("lab02" "lab03" "lab04") 	# we are not considering lab05 for this dataset, and only year 2020/2021 has lab05.
labs=("lab02")
# we will only use lab02 of the second year as the evaluation dataset
# models=("wco" "vm" "ed" "all")
#models=("wco")
#models=("vm")
#models=("ed")
models=("all")

for((m=0;m<${#models[@]};m++));
do
    model=${models[$m]}
    echo $model
    results_dir="results/var_maps-"$model
    mkdir -p $results_dir
    for((l=0;l<${#labs[@]};l++));
    do
	lab=${labs[$l]}
	for ex in $(find $data_dir/incorrect_submissions/$lab/ex* -maxdepth 0 -type d);
	do
	    ex=$(echo $ex | rev | cut -d '/' -f 1 | rev)
	    for mut_dir in $(find $data_dir/incorrect_submissions/$lab/$ex/* -maxdepth 0 -mindepth 0 -type d);
	    do
		mut=$(echo $mut_dir | rev | cut -d '/' -f 1 | rev)
		for mutl_dir in $(find $data_dir/incorrect_submissions/$lab/$ex/$mut/* -maxdepth 0 -mindepth 0 -type d);
		do
		    mutl=$(echo $mutl_dir | rev | cut -d '/' -f 1 | rev)
		    echo "Dealing with "$mutl_dir
		    for p in $(find $data_dir/incorrect_submissions/$lab/$ex/$mut/$mutl/*.c -maxdepth 0 -mindepth 0 -type f);
		    do
			stu_id=$(echo $p | rev | cut -d '/' -f 1 | rev)
			stu_id=$(echo $stu_id | sed "s/.c//g")
			d=$results_dir/$lab/$ex/$mut/$mutl/$stu_id-$model
			mkdir -p $d $initial_dir/variable_mappings/$model/$lab/$ex/$mut/$mutl
			c_prog_ast=$(find $data_dir/correct_submissions/$lab/$ex/"ast-"$stu_id* -type f | tail -n 1)
			i_prog_ast=$mutl_dir/"ast-"$stu_id".pkl.gz"
			gnn_model=$(find $gnn_models_dir/$model*.pt -type f | tail -1 )
			# /home/pmorvalho/runsolver/src/runsolver -o $d/out.o -w $d/watcher.w -v $d/var.v -W $TIMEOUT_REPAIR --rss-swap-limit 32000 \
			python3 eval.py -ia $i_prog_ast -ca $c_prog_ast -m $var_maps_dir/$model/$lab/$ex/$mut/$mutl"/var_map-"$stu_id".pkl.gz" -md $var_maps_dir/$model/$lab/$ex/$mut/$mutl"/var_map_distributions-"$stu_id".pkl.gz" -gm $gnn_model -t $d/var_map_time.txt > $d/out.o
		    done
		    # wait
		done
	    done
	done
    done
done

