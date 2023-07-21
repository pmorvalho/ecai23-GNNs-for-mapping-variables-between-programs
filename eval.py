import argparse
from sys import argv
import gzip
import pickle
from gnn import VariableMappingGNN
import torch
import time
import gzip

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

def load_model(model_location):
    device = "cpu"
    with gzip.open("types2int.pkl.gz", 'rb') as f:
        node_type_mapping = pickle.load(f)
        print(node_type_mapping)
        # find maximum index
        num_types = node_type_mapping['diff_types']
        print(num_types)

    gnn = VariableMappingGNN(num_types, device).to(device)

    gnn.load_state_dict(
        torch.load(model_location, map_location=torch.device('cpu')))

    return gnn

def predict(gnn_model, left_ast_file, right_ast_file):

    with gzip.open(left_ast_file, 'rb') as f:
        left_ast = pickle.load(f)

    with gzip.open(right_ast_file, 'rb') as f:
        right_ast = pickle.load(f)

    left_ast, right_ast = preprocess_data_test_time(left_ast, right_ast)

    op_var_dict, op_dist_dict = gnn_model.test_time_output((left_ast, right_ast))

    return op_var_dict, op_dist_dict

def save_var_maps(var_dict, p_name):
    fp=gzip.open(p_name,'wb')
    pickle.dump(var_dict,fp)
    fp.close()


def parser():
    parser = argparse.ArgumentParser(prog='prog_fixer.py', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-ia', '--inc_ast', help='Incorrect Program\'s AST.')
    parser.add_argument('-ca', '--cor_ast', help='Correct program\'s AST.')
    parser.add_argument('-m', '--var_map', help='Variable mapping Path.')
    parser.add_argument('-md', '--var_map_dist', help='Path for the each variable mapping distribution.')    
    parser.add_argument('-gm', '--gnn_model', help='GNN model to use.')
    parser.add_argument('-t', '--time', help='File where the time spent predicting the model will be written to.')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='Prints debugging information.')
    args = parser.parse_args(argv[1:])
    return args


if __name__ == "__main__":
    args = parser()
    
    model_location = args.gnn_model
    model = load_model(model_location)
    
    buggy_ast_file = args.inc_ast
    correct_ast_file = args.cor_ast

    time_0 = time.time()
    model_output, model_output_distributions = predict(model, buggy_ast_file, correct_ast_file)
    time_f = time.time()-time_0
    with open(args.time, 'w+') as writer:
        writer.writelines("Time: {t}".format(t=round(time_f,3)))
    
    print(model_output)
    save_var_maps(model_output, args.var_map)
    save_var_maps(model_output_distributions, args.var_map_dist)
    # TODO Use the {model_output_distributions} to sample
