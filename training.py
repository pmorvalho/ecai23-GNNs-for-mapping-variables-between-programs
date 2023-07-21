import numpy as np
import gzip
import pickle
from pathlib import Path
import torch
import random
from gnn import VariableMappingGNN
import argparse

data_dir="data"

def preprocess_data_test_time(left_ast, right_ast):
    left_edge_index_pairs = []
    left_edge_types = []
    for triple in left_ast['edges']:
        left_edge_index_pairs.append([triple[0], triple[1]])
        left_edge_types.append(triple[2])

    left_node_types = [left_ast['nodes2types'][k] for k in left_ast['nodes2types']]

    right_edge_index_pairs = []
    right_edge_types = []

    for triple in right_ast['edges']:
        right_edge_index_pairs.append([triple[0], triple[1]])
        right_edge_types.append(triple[2])

    right_node_types = [right_ast['nodes2types'][k] for k in right_ast['nodes2types']]

    # var_norm_index = {k: e for (e, k) in enumerate(left_ast['vars2id'])}
    # var_norm_index2 = {k: e for (e, k) in enumerate(right_ast['vars2id'])}

    left_node_types = torch.as_tensor(left_node_types)
    right_node_types = torch.as_tensor(right_node_types)

    left_edge_index_pairs = torch.as_tensor(left_edge_index_pairs)
    right_edge_index_pairs = torch.as_tensor(right_edge_index_pairs)

    left_edge_types = torch.as_tensor(left_edge_types)
    right_edge_types = torch.as_tensor(right_edge_types)

    return ((left_node_types, left_edge_index_pairs, left_edge_types, left_ast),
            (right_node_types, right_edge_index_pairs, right_edge_types, right_ast))

def preprocess_data(left_ast, right_ast, varmap, sample_spec):

    left_edge_index_pairs = []
    left_edge_types = []
    for triple in left_ast['edges']:

        if triple[2] in ablation_edges:
            left_edge_index_pairs.append([triple[0], triple[1]])
            left_edge_types.append(triple[2])

    max_node_described = -1
    for e in left_edge_index_pairs:
        if e[0] > max_node_described:
            max_node_described = e[0]

        if e[1] > max_node_described:
            max_node_described = e[1]

    left_node_types = [left_ast['nodes2types'][k] for k in left_ast['nodes2types']]

    right_edge_index_pairs = []
    right_edge_types = []

    for triple in right_ast['edges']:
        right_edge_index_pairs.append([triple[0], triple[1]])
        right_edge_types.append(triple[2])

    max_node_described = -1
    for e in right_edge_index_pairs:
        if e[0] > max_node_described:
            max_node_described = e[0]

        if e[1] > max_node_described:
            max_node_described = e[1]


    right_node_types = [right_ast['nodes2types'][k] for k in right_ast['nodes2types']]

    var_norm_index = {k: e for (e, k) in enumerate(left_ast['vars2id'])}
    var_norm_index2 = {k: e for (e, k) in enumerate(right_ast['vars2id'])}

    labels = []

    # TODO ATTENTION varmap needs to be reversed!

    varmap = {varmap[key]:key for key in varmap} # reversal
    for k in varmap:
        labels.append(var_norm_index2[varmap[k]])

    left_node_types = torch.as_tensor(left_node_types)
    right_node_types = torch.as_tensor(right_node_types)

    left_edge_index_pairs = torch.as_tensor(left_edge_index_pairs)
    right_edge_index_pairs = torch.as_tensor(right_edge_index_pairs)

    left_edge_types = torch.as_tensor(left_edge_types)
    right_edge_types = torch.as_tensor(right_edge_types)


    return ((left_node_types, left_edge_index_pairs, left_edge_types, left_ast), (right_node_types, right_edge_index_pairs, right_edge_types, right_ast), labels, sample_spec)


if __name__ == "__main__":
    torch.set_num_threads(20)
    parser = argparse.ArgumentParser(description='Train a model.')
    parser.add_argument('--error', type=str,
                        help='What bug we want to train on.')
    parser.add_argument('--gpu', type=str,
                        help='Which gpu to use')
    parser.add_argument('--expname', type=str,
                        help='Name of the experiment; defines where trained model is stored.')
    parser.add_argument('--samplecap', type=int,
                        help='How many samples to take from each folder.')
    parser.add_argument('--edgetypes', type=str, help='comma-separated list of which edgetypes to used')


    args = parser.parse_args()

    student_sample_cap = 1

    path = Path(f"{data_dir}/variable-alignment/mutilated_programs/year-1/lab02/")

    device = torch.device(f"cuda:{args.gpu}" if torch.cuda.is_available() else "cpu")
    
    # error = "wrong_comp_op"
    # error = "variable_misuse"
    # error = "expression_deletion"
    # error = "all"
    errorlist = ["wrong_comp_op", "variable_misuse", "expression_deletion", "all"]
    
    ablation_edges = [int(k) for k in args.edgetypes.split(",")]
    
    error = args.error
    if error not in errorlist:
        raise ValueError("This error is not supported, did you misspell? Use one of these: wrong_comp_op, variable_misuse, expression_deletion or all")
    expname = f"{args.expname}_{error}_cap{args.samplecap}"
    if error == "all":
        use_all_errors = True
    else:
        use_all_errors = False

    all_exercises = []
    for p in path.glob("*"):

        if p.is_dir():
            all_exercises.append(p)

    print(all_exercises)
    print(len(all_exercises))

    mut_paths = []
    for exercise in all_exercises:

        ex_path = Path(exercise)
        for p in ex_path.glob("*"):
            if p.is_dir():
                mut_paths.append(p)

    print(mut_paths)
    print(len(mut_paths))

    mutil_paths = []
    for mut in mut_paths:

        mut_path = Path(mut)
        for p in mut_path.glob("*"):
            if p.is_dir():
                if p.name == error or use_all_errors:
                    mutil_paths.append(p)

    print(mutil_paths)
    print(len(mutil_paths))

    student_paths = []

    for mutil in mutil_paths:

        mutil_path = Path(mutil)
        for p in mutil_path.glob("*"):
            if p.is_dir():

                student_paths.append(p)

    print(student_paths)
    print(len(student_paths))
    student_names = []
    for stu in student_paths:
        # print(stu.name)
        if not stu.name in student_names:
            student_names.append(stu.name)
    
    # make deterministic
    #student_names = sorted(student_names)

    print(len(student_names))
    # assert 2 > 3
    print(len(student_paths))
    student_paths = [k for k in student_paths if not "tmp_input_file" in str(k.absolute())]
    print(len(student_paths))
    # assert 2 > 3
    random.seed(18)
    student_names.remove("reference_implementation")
    #random.shuffle(sorted(student_names)) # sort first to ensure determinism 
    random.shuffle(student_names)
    no_stud = len(student_names)
    train_end = int(np.floor(0.8*no_stud))
    train_set = student_names[:train_end]
    val_set = student_names[train_end:]
    print(val_set)
    #valset used last
    #valset ['stu_002', 'stu_014', 'stu_009', 'stu_015', 'stu_008']
    #assert 2 > 3
    training_data = []
    val_data      = []
    for p in student_paths:
        print(p)
        assert "year-2" not in str(p.absolute())


    for p in student_paths:

        print(p.name)
        if p.name in train_set:
            print(f"{p.name} in train set")
            training_data.append(p)
        elif p.name in val_set:
            print(f"{p.name} in val set")
            val_data.append(p)
        else:
            print(f"{p.name} not found")


    # assert (len(val_data) + len(training_data)) == len(student_paths)
    # training_data = random.sample(training_data, k = 400)
    # val_data = random.sample(val_data, k=20)

    print(len(training_data))
    print(len(val_data))
    print(len(val_data) + len(training_data))
    #assert 2 > 3
    
    error_files = []

    train_samples = []
    for path in training_data:

        files_c = []
        files_ast = []
        files_varmap = []

        for p in path.rglob("*"):

            if p.name.startswith("var_map"):
                files_varmap.append(p)



        random.shuffle(files_varmap)

        for sample_specification in files_varmap[:student_sample_cap]:

            original_mutation_file = sample_specification.parents[0].name

            prefix = "var_map-"
            postfix = ".pkl.gz"

            tmp_str = str(sample_specification.name)[len(prefix):]
            tmp_str = tmp_str[:(len(tmp_str) - len(postfix))]

            left, right = tmp_str.split("_")


            if not all([k == '0' for k in right]):
                # if not (int(left) == 0 and int(right) == 0):
                left_ast_file = str(sample_specification.parents[0]) + "/" + "ast-" + right + postfix
                right_ast_file = str(sample_specification.parents[0]) + "/" + "ast-" + left + postfix

                student = str(right_ast_file).replace("mutilated_programs", "C-Pack-IPAs_blocks/correct_submissions")
                student = Path(student)
                student_stump = student.parents[0].parents[0].parents[0].parents[0].parents[0]
                student = Path(right_ast_file).parents[0].parents[0].name

                correct_file_path = str(student_stump.absolute()) + "/ast-" + student + ".pkl.gz"
                right_ast_file = correct_file_path
                # print(left_ast_file)
                # print(right_ast_file)
                # assert 2 > 3

                with gzip.open(sample_specification, 'rb') as f:
                    varmap = pickle.load(f)
                    print(varmap)

                with gzip.open(left_ast_file, 'rb') as f:
                    left_ast = pickle.load(f)

                with gzip.open(right_ast_file, 'rb') as f:
                    right_ast = pickle.load(f)

                # perhaps also add the right to left combo
                train_samples.append(preprocess_data(left_ast, right_ast, varmap, sample_specification))


    # assert 2 > 3
    val_samples = []
    for path in val_data:

        files_c = []
        files_ast = []
        files_varmap = []

        for p in path.rglob("*"):

            if p.name.startswith("var_map"):
                files_varmap.append(p)

        for sample_specification in files_varmap[:student_sample_cap]:
            print(sample_specification)
            # try:
            prefix = "var_map-"
            postfix = ".pkl.gz"

            tmp_str = str(sample_specification.name)[len(prefix):]
            tmp_str = tmp_str[:(len(tmp_str) - len(postfix))]

            left, right = tmp_str.split("_")

            print("Program Names: ")
            print(left, right)  #
            if not all([k == '0' for k in right]):
                left_ast_file = str(sample_specification.parents[0]) + "/" + "ast-" + right + postfix
                right_ast_file = str(sample_specification.parents[0]) + "/" + "ast-" + left + postfix

                student = str(right_ast_file).replace("mutilated_programs", "C-Pack-IPAs_blocks/correct_submissions")
                student = Path(student)
                student_stump = student.parents[0].parents[0].parents[0].parents[0].parents[0]
                student = Path(right_ast_file).parents[0].parents[0].name

                correct_file_path = str(student_stump.absolute()) + "/ast-" + student + ".pkl.gz"

                with gzip.open(sample_specification, 'rb') as f:
                    varmap = pickle.load(f)

                with gzip.open(left_ast_file, 'rb') as f:
                    left_ast = pickle.load(f)

                with gzip.open(right_ast_file, 'rb') as f:
                    right_ast = pickle.load(f)

                # perhaps also add the right to left combo
                val_samples.append(preprocess_data(left_ast, right_ast, varmap, sample_specification))

    # Some global information about which types of nodes exist
    with gzip.open("types2int.pkl.gz", 'rb') as f:
        node_type_mapping = pickle.load(f)
        print(node_type_mapping)
        # find maximum index
        num_types = node_type_mapping['diff_types']
        print(num_types)

    print(error_files)
    print(len(error_files))

    gnn = VariableMappingGNN(num_types, device).to(device)

    loss = torch.nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(gnn.parameters())


    print(len(training_data), len(train_samples))
    print(len(val_data), len(val_samples))
    assert 2>3

    acc_list = []
    fc_l = []

    from tqdm import tqdm

    for i in tqdm(range(20)):
        global_representation_list = []
        global_orig_sample_list = []
        ep_corr = 0
        ep_total = 0
        random.shuffle(train_samples)
        for j in tqdm(range(len(train_samples))):

            gnn.train_step(train_samples[j], loss, optimizer)

        random.shuffle(val_samples)
        fully_correct_list = []
        with torch.no_grad():
            for j in tqdm(range(len(val_samples))):

                corr, total, fully_correct = gnn.eval_step(val_samples[j], loss)

                ep_corr += corr
                ep_total += total
                fully_correct_list.append(fully_correct)

            print(f"Epoch Evaluation Accuracy: {ep_corr} / {ep_total}")
            print(f"Epoch Evaluation Samples Fully Correct: {np.mean(fully_correct_list) * 100} %")
            fc_l.append(np.mean(fully_correct_list) * 100)
            acc_list.append(float(ep_corr) / float(ep_total))

    torch.save(gnn.state_dict(), f"{data_dir}/{expname}.pt")

# Example command
# python -u training.py --error variable_misuse --gpu 0 --samplecap 1 --expname dev_cl
