#!/usr/bin/env bash
#Title			: get_ground_truth_repairs.sh
#Usage			: bash get_ground_truth_repairs.sh
#Author			: pmorvalho
#Date			: July 26, 2022
#Description		: Runs our repair script considering the real (ground truth) variable mappings
#Notes			: 
# (C) Copyright 2022 Pedro Orvalho.
#==============================================================================

initial_dir=$(pwd)
data_dir="eval-dataset"
results_dir="results/ground_truth/"

TIMEOUT_REPAIR=122 # in seconds 

#labs=("lab02" "lab03" "lab04") 	# we are not considering lab05 for this dataset, and only year 2020/2021 has lab05.
labs=("lab02")
# we will only use lab02 of the second year as the evaluation dataset
bugs=("wco" "vm" "ed" "all")
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
		   for((b=0;b<${#bugs[@]};b++));
		   do
		       bug=${bugs[$b]}
		       #bug="all"
		       d=$results_dir/$lab/$ex/$mut/$mutl/$stu_id-$bug
		       mkdir -p $d
		       c_prog=$(find $data_dir/correct_submissions/$lab/$ex/*$stu_id*.c -type f | tail -n 1)
		       #/home/pmorvalho/runsolver/src/runsolver -o $d/out.o -w $d/watcher.w -v $d/var.v -W $TIMEOUT_REPAIR --rss-swap-limit 32000 \
		       python3 prog_fixer.py -ip $p -cp $c_prog -m $mutl_dir"/var_map-"$stu_id".pkl.gz" --$bug --ipa $lab/$ex -o $d/$stu_id"-fixed" -v > $d/out.o & 
		   done
		   wait
	       done
	       #wait
	       #assuming that this script and the GNN script are not running at the same time, we can execute the following:
	       rm -rf tmp-*
	    done
	done
    done
done

