#!/usr/bin/python
#Title			: gen_eval_dataset.py
#Usage			: python gen_eval_dataset.py -h
#Author			: pmorvalho
#Date			: July 25, 2022
#Description	        : For each program mutation and mutilation configuration (input dir), this script chooses randomly a mutilated program for each student and guarantes that this program is semantically incorrect.
#Notes			: 
#Python Version: 3.8.5
# (C) Copyright 2022 Pedro Orvalho.
#==============================================================================

import argparse
from sys import argv
import os
import random

from helper import *


def choose_incorrect_programs(input_dir, output_dir):
    subfolders = [f.path for f in os.scandir(input_dir) if f.is_dir()]
    for sf in subfolders:
        stu_id = str(sf).split("/")[-1]
        # print(sf+"/")
        muts = list(pathlib.Path(sf+"/").glob('*/')) # mutations directories
        prog_found = False
        while len(muts) > 0 and not prog_found:
            mut = random.sample(muts, 1)[0]
            muts.remove(mut)
            m = int(str(mut).split("/")[-1].replace("-",""))
            if m == 0: # ignoring programs that were not mutated (index 0, 00, 000). E.g. programs that have a for-loop and are inside the for2while directory.
                print("Ignoring ", mut)
                continue
            progs = list(pathlib.Path("{d}".format(d=mut)).glob('*.c')) # mutilated programs
            while len(progs) > 0:
                p = random.sample(progs, 1)[0]
                progs.remove(p)
                p = str(p)
                if not check_program(p, args.ipa):
                    prog_found=True
                    if args.verbose:
                        print("Program ",p, " has been chosen.")
                    p=p.split("/")[-1][:-2]
                    os.system("cp {d}/{p}.c {o}/{s}.c".format(d=mut, p=p, o=args.output_dir, s=stu_id))
                    os.system("cp {d}/ast-{p}.pkl.gz {o}/ast-{s}.pkl.gz".format(d=mut, p=p, o=args.output_dir, s=stu_id))
                    os.system("cp {d}/bug_map-{z}-{p}.pkl.gz {o}/bug_map-{s}.pkl.gz".format(d=mut, z="0"*len(p),p=p, o=args.output_dir, s=stu_id))
                    os.system("cp {d}/var_map-{z}_{p}.pkl.gz {o}/var_map-{s}.pkl.gz".format(d=mut, z="0"*len(p),p=p, o=args.output_dir, s=stu_id))
                    os.system("rm {d}/*.o".format(d=mut))
                    break
            # os.system("rm {d}/*.o".format(d=mut))
            

def parser():
    parser = argparse.ArgumentParser(prog='gen_eval_dataset.py', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-d', '--input_dir', nargs='?',help='input directory.')
    parser.add_argument('-e', '--ipa', help='Name of the lab and exercise (IPA) so we can check the IO tests.')    
    parser.add_argument('-i', '--ignore', action='store_true', default=False, help='ignores...')
    parser.add_argument('-o', '--output_dir', nargs='?', help='the name of the output dir.')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='Prints debugging information.')
    args = parser.parse_args(argv[1:])
    return args

if __name__ == '__main__':
    args = parser()
    choose_incorrect_programs(args.input_dir, args.output_dir)
