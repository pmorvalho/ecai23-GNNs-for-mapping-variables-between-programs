#!/usr/bin/env bash
#Title			: get_gnn_based_repairs.sh
#Usage			: bash get_gnn_based_repairs.sh
#Author			: pmorvalho
#Date			: July 26, 2022
#Description		: Runs our repair script using the variable mappins produced by our GNN models
#Notes			: 
# (C) Copyright 2022 Pedro Orvalho.
#==============================================================================

initial_dir=$(pwd)
data_dir="eval-dataset"
var_maps_dir=$initial_dir"/variable_mappings"
TIMEOUT_REPAIR=122 # in seconds 

#labs=("lab02" "lab03" "lab04") 	# we are not considering lab05 for this dataset, and only year 2020/2021 has lab05.
labs=("lab02")
# we will only use lab02 of the second year as the evaluation dataset
# models=("wco" "vm" "ed" "all")
#models=("wco" "all")
#models=("vm")
#models=("ed")
models=("all")
# bugs=("wco" "vm" "ed" "all") # to check for specific types of bugs
bugs=("all")

for((m=0;m<${#models[@]};m++));
do
    model=${models[$m]}
    echo $model 
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
			var_map=$initial_dir/variable_mappings/$model/$lab/$ex/$mut/$mutl"/var_map-"$stu_id".pkl.gz"
			c_prog=$(find $data_dir/correct_submissions/$lab/$ex/*$stu_id*.c -type f | tail -n 1)
			for((b=0;b<${#bugs[@]};b++));
			do
			    bug=${bugs[$b]}
			    results_dir="/data/benchmarks/variable-alignment/results/gnn-"$model
    			    mkdir -p $results_dir
			    d=$results_dir/$lab/$ex/$mut/$mutl/$stu_id-$bug
			    mkdir -p $d
			    # /home/pmorvalho/runsolver/src/runsolver -o $d/out.o -w $d/watcher.w -v $d/var.v -W $TIMEOUT_REPAIR --rss-swap-limit 32000 \
			    python3 prog_fixer.py -ip $p -cp $c_prog -m $var_maps_dir/$model/$lab/$ex/$mut/$mutl/"/var_map-"$stu_id".pkl.gz" -md $var_maps_dir/$model/$lab/$ex/$mut/$mutl/"/var_map_distributions-"$stu_id".pkl.gz" --$bug --ipa $lab/$ex -o $d/$stu_id"-fixed" -v > $d/out.o &
			done
			wait
		    done
		    # wait
		done
	    done
	    # telegram-send $lab/$ex" is done!"	    
	done
	# telegram-send "$lab is done!"
    done
done
