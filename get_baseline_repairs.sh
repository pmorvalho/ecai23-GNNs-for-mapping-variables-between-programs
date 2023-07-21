#!/usr/bin/env bash
#Title			: get_baseline_repairs.sh
#Usage			: bash get_baseline_repairs.sh
#Author			: pmorvalho
#Date			: April 19, 2023
#Description		: Runs our repair script using our baseline i.e. random variable mappings
#Notes			: 
# (C) Copyright 2023 Pedro Orvalho.
#==============================================================================


initial_dir=$(pwd)
data_dir="eval-dataset"
var_maps_dir=$initial_dir"/variable_mappings"
TIMEOUT_REPAIR=122 # in seconds 

#labs=("lab02" "lab03" "lab04") 	# we are not considering lab05 for this dataset, and only year 2020/2021 has lab05.
labs=("lab02")
# we will only use lab02 of the second year as the evaluation dataset
model="all"
bugs=("wco" "vm" "ed" "all")

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
		    c_prog=$(find $data_dir/correct_submissions/$lab/$ex/*$stu_id*.c -type f | tail -n 1)
		    for((b=0;b<${#bugs[@]};b++));
		    do
			bug=${bugs[$b]}
			results_dir="results/baseline"
    			mkdir -p $results_dir
			d=$results_dir/$lab/$ex/$mut/$mutl/$stu_id-$bug
			mkdir -p $d
			# /home/pmorvalho/runsolver/src/runsolver -o $d/out.o -w $d/watcher.w -v $d/var.v -W $TIMEOUT_REPAIR --rss-swap-limit 32000 \
			python3 prog_fixer.py -ip $p -cp $c_prog -m $var_maps_dir/$model/$lab/$ex/$mut/$mutl/"var_map-"$stu_id".pkl.gz" -md $var_maps_dir/$model/$lab/$ex/$mut/$mutl/"var_map_distributions-"$stu_id".pkl.gz" --$bug --ipa $lab/$ex -o $d/$stu_id"-fixed" -v -b > $d/out.o &
		    done
		    wait
		done
		# wait
	    done
	done
    done
done

