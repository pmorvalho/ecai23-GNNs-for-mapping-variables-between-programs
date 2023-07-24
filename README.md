# ECAI 2023 - Graph Neural Networks For Mapping Variables Between Programs

This repository contains the code and data used for the paper "*Graph Neural Networks For Mapping Variables Between Programs*", accepted at ECAI 2023.

We present a novel graph program representation that is agnostic to the names of the variables and for each variable in the program contains a representative variable node that is connected to all the variable's occurrences. Furthermore, we use GNNs for mapping variables between programs based on our program representation, ignoring the variables' identifiers;
We represent each program as a graph using the script gen_progs_repr.py, as explained in [1, 2].

To understand the entire pipeline, from the dataset generation to the repair process, the interested reader is refered to our main script 'run_all.sh'.

The generation of the datasets (training, validation and evaluation) and the training of our GNN has been commented since it takes a few hours to compute. Only the mapping computations and the program repair tasks were left uncommented. In this repo only the evaluation dataset is available.

- How to execute:

```
chmod +x run_all.sh
bash run_all.sh
```

## Installation Requirements

The following script creates a new conda environment named 'gnn_env' and installs all the required dependencies in it.

```
chmod +x config_gnn.sh
bash config_gnn.sh
```

## Introductory Programming Assignments (IPAs) Dataset


To generate our evaluation set of C programs we used [MultIPAs](https://github.com/pmorvalho/MultIPAs) [3], which is a program transformation framework, to augment our dataset of IPAs, [C-Pack-IPAs](https://github.com/pmorvalho/C-Pack-IPAs) [4]. 

## References

[1] Pedro Orvalho, Jelle Piepenbrock, Mikoláš Janota, and Vasco Manquinho. Graph Neural Networks For Mapping Variables Between Programs. ECAI 2023. [PDF](). *[Accepted for Publication]*

[2] Pedro Orvalho, Jelle Piepenbrock, Mikoláš Janota, and Vasco Manquinho. Project Proposal: Learning Variable Mappings to Repair Programs. AITP 2022. [PDF](http://aitp-conference.org/2022/abstract/AITP_2022_paper_15.pdf).

[3] Pedro Orvalho, Mikoláš Janota, and Vasco Manquinho. MultIPAs: Applying Program Transformations to Introductory Programming Assignments for Data Augmentation. In 30th ACM Joint European Software Engineering Conference and Symposium on the Foundations of Software Engineering, ESEC/FSE 2022. [PDF](https://dl.acm.org/doi/10.1145/3540250.3558931).

[4] Pedro Orvalho, Mikoláš Janota, and Vasco Manquinho. C-Pack of IPAs: A C90 Program Benchmark of Introductory Programming Assignments. 2022. [PDF](https://arxiv.org/pdf/2206.08768.pdf).
