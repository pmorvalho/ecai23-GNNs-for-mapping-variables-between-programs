#!/usr/bin/env bash
#Title			: run_all.sh
#Usage			: bash run_all.sh
#Author			: pmorvalho
#Date			: May 03, 2022
#Description	        : Bash commands to mutate and mutilate programs and generate their representations
#Notes			: For each new mutation added to the mutations vector a new for-loop is needed to compute all possible mutations (permutations)
# (C) Copyright 2022 Pedro Orvalho.
#==============================================================================

# The following command installs the dependencies (pycparser, ..) and creates a conda environment.
# ./config_gnn.sh
conda activate gnn_env

# mutations=("swap_comp_ops" "swap_if_else_sttms" "swap_incr_decr_ops" "decl_dummy_vars" "reorder_decls" "for_2_while")
mutations=("swap_comp_ops" "swap_if_else_sttms" "swap_incr_decr_ops" "reorder_decls" "for_2_while")
mutations_flags=("-c"  "-if" "-io" "-rd" "-fw")

dataset="C-Pack-IPAs"
#labs=("lab02" "lab03" "lab04") 	# we are not considering lab05 for this dataset, and only year 2020/2021 has lab05.
labs=("lab02")
years=()

for y in $(find $dataset/correct_submissions/* -maxdepth 0 -type d);
do
    y=$(echo $y | rev | cut -d '/' -f 1 | rev)
    years+=("$y")
    echo "Found year: "$y
done

data_dir="mutated_programs"

mutate_programs(){
# $1 - year directory
# $2 - submissions directory
    year=$1
    sub_dir=$2
    sub_type=$(echo $sub_dir | rev | cut -d '/' -f 1 | rev)
    for((l=0;l<${#labs[@]};l++));
    do
	lab=${labs[$l]}
	for ex in $(find $sub_dir/$year/$lab/ex* -maxdepth 0 -type d);
	do
	    ex=$(echo $ex | rev | cut -d '/' -f 1 | rev)
	    mkdir -p  $data_dir/$sub_type/$year/$lab/$ex
	    n_mut=0
	    echo "Mutating "$dataset/$sub_type/$year/$lab/$ex
	    for((m1=0;m1<${#mutations[@]};m1++));
	    do
		mut1=${mutations[$m1]}
		f1=${mutations_flags[$m1]}
		# echo $mut1
		python prog_mutator.py -d $sub_dir/$year/$lab/$ex -o $data_dir/$sub_type/$year/$lab/$ex/$mut1 $f1 &
		n_mut=$((n_mut+1))
		for((m2=m1+1;m2<${#mutations[@]};m2++));
		do
		    mut2=${mutations[$m2]}
		    f2=${mutations_flags[$m2]}
		    # # echo $mut1-$mut2
		    python prog_mutator.py -d $sub_dir/$year/$lab/$ex -o $data_dir/$sub_type/$year/$lab/$ex/$mut1-$mut2 $f1 $f2 &
		    n_mut=$((n_mut+1))
		    for((m3=m2+1;m3<${#mutations[@]};m3++));
		    do
			mut3=${mutations[$m3]}
			f3=${mutations_flags[$m3]}
			# echo $mut1-$mut2-$mut3
			python prog_mutator.py -d $sub_dir/$year/$lab/$ex -o $data_dir/$sub_type/$year/$lab/$ex/$mut1-$mut2-$mut3 $f1 $f2 $f3 &
			n_mut=$((n_mut+1))
			for((m4=m3+1;m4<${#mutations[@]};m4++));
			do
			    mut4=${mutations[$m4]}
			    f4=${mutations_flags[$m4]}
			    # echo $mut1-$mut2-$mut3-$mut4
			    python prog_mutator.py -d $sub_dir/$year/$lab/$ex -o $data_dir/$sub_type/$year/$lab/$ex/$mut1-$mut2-$mut3-$mut4 $f1 $f2 $f3 $f4 &
			    n_mut=$((n_mut+1))
			    for((m5=m4+1;m5<${#mutations[@]};m5++));
			    do
				mut5=${mutations[$m5]}
				f5=${mutations_flags[$m5]}
				# echo $mut1-$mut2-$mut3-$mut4-$mut5
				python prog_mutator.py -d $sub_dir/$year/$lab/$ex -o $data_dir/$sub_type/$year/$lab/$ex/$mut1-$mut2-$mut3-$mut4-$mut5 $f1 $f2 $f3 $f4 $f5 &
				n_mut=$((n_mut+1))
				for((m6=m5+1;m6<${#mutations[@]};m6++));
				do
				    mut6=${mutations[$m6]}
				    f6=${mutations_flags[$m6]}
				    # echo $mut1-$mut2-$mut3-$mut4-$mut5
				    python prog_mutator.py -d $sub_dir/$year/$lab/$ex -o $data_dir/$sub_type/$year/$lab/$ex/$mut1-$mut2-$mut3-$mut4-$mut5-$mut6 $f1 $f2 $f3 $f4 $f5 $f6 &
				    n_mut=$((n_mut+1))
				done
			    done
			done
		    done
		    #wait
		done
	    done
	    wait
	    echo "In total "$n_mut" different mutations were perform to "$sub_type/$year/$lab/$ex
	    echo
	    echo
	done
    done
    wait
}

represent_programs()
{
    local year=$1
    local sub_dir=$2
    for((l=0;l<${#labs[@]};l++));
    do
	lab=${labs[$l]}
	for ex in $(find $sub_dir/$year/$lab/ex* -maxdepth 0 -type d);
	do
	    ex=$(echo $ex | rev | cut -d '/' -f 1 | rev)
	    for mut_d in $(find $sub_dir/$year/$lab/$ex/* -maxdepth 0 -type d);
	    do
	       mut=$(echo $mut_d | rev | cut -d '/' -f 1 | rev)
	       echo "Generating program representations for "$sub_dir/$year/$lab/$ex/$mut
	       for s in $(find $sub_dir/$year/$lab/$ex/$mut/* -maxdepth 0 -mindepth 0 -type d);
	       do
		   python gen_progs_repr.py -d $s &
	       done
	       wait
	    done
	done
    done 
}

# echo "Starting program mutation..."
# for((y=0;y<${#years[@]};y++));
# do
#    ys=${years[$y]}
#    mutate_programs $ys $dataset/correct_submissions
# done

# echo "Starting to compute program representations"
# for((y=0;y<${#years[@]};y++));
# do
#    ys=${years[$y]}
#    represent_programs $ys $data_dir/correct_submissions
# done

# wait

mutilations=("wrong_comp_op" "variable_misuse" "expression_deletion")
mutilations_flags=("-c" "-vm" "-ad")
num_progs_2_mutilate=5

mutilate_programs(){
# $1 - year directory
# $2 - submissions directory
    local year=$1
    local sub_dir=$2
    local sub_type="mutilated_programs"
    for((l=0;l<${#labs[@]};l++));
    do
	lab=${labs[$l]}
	for ex in $(find $sub_dir/$year/$lab/ex* -maxdepth 0 -type d);
	do
	    ex=$(echo $ex | rev | cut -d '/' -f 1 | rev)
	    for mut_d in $(find $sub_dir/$year/$lab/$ex/* -maxdepth 0 -type d);
	    do
		mut=$(echo $mut_d | rev | cut -d '/' -f 1 | rev)
		n_mutil=0
		echo "Mutilating "$dataset/$sub_type/$year/$lab/$ex/$mut
		for s_d  in $(find $sub_dir/$year/$lab/$ex/$mut/* -maxdepth 0 -type d);
		do
		    s=$(echo $s_d | rev | cut -d '/' -f 1 | rev)
		    for((m1=0;m1<${#mutilations[@]};m1++));
		    do
			mutil1=${mutilations[$m1]}
			f1=${mutilations_flags[$m1]}
			mkdir -p $data_dir$sub_type/$year/$lab/$ex/$mut/$mutil1/$s
			# echo $mutil1
			python prog_mutilator.py -pp $num_progs_2_mutilate -d $sub_dir/$year/$lab/$ex/$mut/$s -o $data_dir$sub_type/$year/$lab/$ex/$mut/$mutil1/$s $f1 &
			n_mutil=$((n_mutil+1))
		    done
		    wait
		done
		wait
		echo "In total "$n_mutil" different mutilations were perform to "$sub_type/$year/$lab/$ex/$mut
		echo
		echo
	    done
	done
    done
    wait
}

represent_mutilated_programs()
{
    local year=$1
    local sub_dir=$2
    for((l=0;l<${#labs[@]};l++));
    do
	lab=${labs[$l]}
	for ex in $(find $sub_dir/$year/$lab/ex* -maxdepth 0 -type d);
	do
	    ex=$(echo $ex | rev | cut -d '/' -f 1 | rev)
	    for mut_d in $(find $sub_dir/$year/$lab/$ex/* -maxdepth 0 -type d);
	    do
		mut=$(echo $mut_d | rev | cut -d '/' -f 1 | rev)
		for mutil_d in $(find $sub_dir/$year/$lab/$ex/$mut/* -maxdepth 0 -type d);
		do
		    mutil=$(echo $mutil_d | rev | cut -d '/' -f 1 | rev)	    
		    echo "Generating program representations for "$sub_dir/$year/$lab/$ex/$mut/$mutil
		    for s in $(find $sub_dir/$year/$lab/$ex/$mut/$mutil/* -maxdepth 0 -mindepth 0 -type d);
		    do
			for d in $(find $s/* -maxdepth 0 -mindepth 0 -type d);
			do
			    python gen_progs_repr.py -d $d &
			done
			wait
		    done
		done
	    done
	    wait
	done
   done
}

data_dir=""

# echo "Starting program mutilation..."
# for((y=0;y<${#years[@]};y++));
# do
#     ys=${years[$y]}
#     mutilate_programs $ys $data_dir"mutated_programs/correct_submissions"
# done

# echo "Starting to compute program representations for our set of erroneous programs"
# for((y=0;y<${#years[@]};y++));
# do
#     ys=${years[$y]}
#     represent_mutilated_programs $ys $data_dir"mutilated_programs"
# done

represent_correct_programs()
{
    local year=$1
    local sub_dir=$2
    echo "Representing "$year" and directory "$sub_dir
    for((l=0;l<${#labs[@]};l++));
    do
	lab=${labs[$l]}
	for ex in $(find $sub_dir/$year/$lab/ex* -maxdepth 0 -type d);
	do
	    #ex=$(echo $ex | rev | cut -d '/' -f 1 | rev)
	    python gen_progs_repr.py -d $ex 
	for ast in $(find $sub_dir/$year/$lab/ex*/ast* -maxdepth 0 -type f);
	do
	    prog_ast=$(echo $ast | rev | cut -d '/' -f 1 | rev)
	    stu=$(echo $prog_ast | rev | cut -d '-' -f 2 | rev)
	    echo $ex/$prog_ast" to "$ex/"ast-"$stu
	    mv $ex/$prog_ast $ex/"ast-"$stu".pkl.gz"
	done
	done
   done
}

# echo "Starting to compute program representations for our set of erroneous programs"
# for((y=0;y<${#years[@]};y++));
# do
#    ys=${years[$y]}
#    represent_correct_programs $ys $dataset/"correct_submissions"
# done

## the following command will regenerate the evaluation dataset.
## ./get_eval_dataset.sh 

# dataset="C-Pack-IPAs"
# labs=("lab02")
# years=()

# for y in $(find $dataset/correct_submissions/* -maxdepth 0 -type d);
# do
#     y=$(echo $y | rev | cut -d '/' -f 1 | rev)
#     years+=("$y")
#     echo "Found year: "$y
# done

# ./get_clara_repairs.sh
# ./get_verifix_repairs.sh

./get_ground_truth_repairs.sh

./gen_gnn_variable_mappings.sh
./get_baseline_mappings.sh
./get_gnn_based_repairs.sh
