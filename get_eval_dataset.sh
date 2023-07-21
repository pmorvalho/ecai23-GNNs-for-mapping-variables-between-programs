#!/usr/bin/env bash
#Title			: get_eval_dataset.sh
#Usage			: bash get_eval_dataset.sh
#Author			: pmorvalho
#Date			: July 25, 2022
#Description		: Generates an evaluation dataset randomly selecting an incorrect program for each student, considering all the program mutations and mutilations configurations.
#Notes			: 
# (C) Copyright 2022 Pedro Orvalho.
#==============================================================================

dataset="C-Pack-IPAs"
eval_dir="eval-dataset"

#labs=("lab02" "lab03" "lab04") 	# we are not considering lab05 for this dataset, and only year 2020/2021 has lab05.
labs=("lab02")
years=("year-2")
# we will only use lab02 of the second year as the evaluation dataset

data_dir="mutilated_programs"

mkdir -p $eval_dir/incorrect_submissions

NUM_CPU_CORES=$(nproc --all) #Automatically detects your system's number of CPU cores.
NUM_CPU_CORES=$((NUM_CPU_CORES-62))
function pwait() {
    while [ $(jobs -p | wc -l) -ge $NUM_CPU_CORES ]; do
        sleep 1
    done
}

for((y=0;y<${#years[@]};y++));
do
    ys=${years[$y]}
    for((l=0;l<${#labs[@]};l++));
    do
	lab=${labs[$l]}
	mkdir -p $eval_dir/correct_submissions/
	cp -r $dataset/correct_submissions/$ys/$lab $eval_dir/correct_submissions/$lab &
    done
done
wait

for((y=0;y<${#years[@]};y++));
do
    ys=${years[$y]}
    for((l=0;l<${#labs[@]};l++));
    do
	lab=${labs[$l]}
	for ex in $(find $data_dir/$ys/$lab/ex* -maxdepth 0 -type d);
	do
	    ex=$(echo $ex | rev | cut -d '/' -f 1 | rev)
	    for mut_dir in $(find $data_dir/$ys/$lab/$ex/* -maxdepth 1 -mindepth 1 -type d);
	    do
	       echo $mut_dir
	       m=$(echo $mut_dir | sed "s/.*${ex}//g")
	       d=$eval_dir/incorrect_submissions/$lab/$ex/$m
	       mkdir -p $d
	       python3 gen_eval_dataset.py -d $mut_dir -o $d --ipa $lab/$ex
	       #pwait $NUM_CPU_CORES
	    done
	    wait
	done
    done
done
