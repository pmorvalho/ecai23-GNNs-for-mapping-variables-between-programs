#!/usr/bin/env bash
#Title			: prog_checker.sh
#Usage			: bash prog_checker.sh program.c labX/exY 
#Author			: pmorvalho
#Date			: July 20, 2022
#Description	        : Checks if a program is consistent with a set of IO tests for a given lab and exercise 
#Notes			: 
# (C) Copyright 2022 Pedro Orvalho.
#==============================================================================

initial_dir=$(pwd)
prog_2_check=$1
exercise=$2
dataset=$initial_dir"/C-Pack-IPAs"
# reference implementation for the given exercise, we will use this program to confirm the output.
ref_impl=$dataset"/reference_implementations/"$exercise".c"

prog_name=$(echo $prog_2_check | rev | cut -d '/' -f 1 | rev)
wdir="/data/tmp/variable-alignment/"$(python3 -c "import random; print('tmp-{n}/'.format(n=int(random.random()*100000000)))")

if [[ ! -d $wdir ]]; then
    mkdir -p $wdir"outputs"
else
    rm -rf $wdir
    mkdir -p $wdir"outputs"
fi

cp $prog_2_check $wdir/$prog_name
cp $ref_impl $wdir/.
cd $wdir

gcc -O3 -ansi -Wall $prog_name -lm -o prog_2_check.out
gcc -O3 -ansi -Wall ex* -lm -o ref_impl.out

for t in $(find $dataset/tests/$exercise/*.in -maxdepth 0 -type f);
do
    t_id=$(echo $t | rev | cut -d '/' -f 1 | rev)
    t_id=$(echo $t_id | sed -e "s/\.in//")
    timeout 5s ./prog_2_check.out < $t > "outputs/p-"$t_id".out"
    timeout 5s ./ref_impl.out < $t > "outputs/r-"$t_id".out"
    d=$(diff "outputs/p-"$t_id".out" "outputs/r-"$t_id".out")
    if [[ $d == "" ]];
    then
	continue;
    fi
    echo "WRONG"
    cd $initial_dir
    rm -rf $wdir
    exit
done

echo "CORRECT"
cd $initial_dir
rm -rf $wdir
