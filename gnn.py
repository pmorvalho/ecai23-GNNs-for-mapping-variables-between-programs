from torch_geometric.data import Data
from torch_geometric.nn import RGCNConv
import torch

class VariableMappingGNN(torch.nn.Module):

    def __init__(self, num_types, device, message_passing_rounds=5, channels=32):
        super().__init__()

        self.device = device
        self.num_types = num_types
        self.channels = channels
        self.message_passing_rounds = message_passing_rounds

        self.left_conv = RGCNConv(in_channels=self.channels, out_channels=self.channels, num_relations=5, aggr="mean")
        self.right_conv = RGCNConv(in_channels=self.channels, out_channels=self.channels, num_relations=5, aggr="mean")

        self.node_embeddings = torch.nn.Parameter(torch.randn(num_types, self.channels), requires_grad=True)

        self.var_projector = torch.nn.Sequential(torch.nn.Linear(self.channels, self.channels), torch.nn.ReLU(), torch.nn.Linear(self.channels, self.channels))

        self.relu = torch.nn.ReLU()
        self.ln = torch.nn.LayerNorm(self.channels)

    def initial_embedding(self, indices):

        return torch.index_select(self.node_embeddings, 0, torch.as_tensor(indices, device=self.device))

    def message_passing(self, left_data, right_data):

        left_x = left_data.x
        right_x = right_data.x

        for i in range(self.message_passing_rounds):
            # print(left_x)
            # print(left_x.shape)
            # print(left_data.edge_index)
            left_x = self.left_conv.forward(left_x, left_data.edge_index, left_data.edge_attr)
            left_x = self.ln(left_x)

            left_x = self.relu(left_x)
            right_x = self.right_conv.forward(right_x, right_data.edge_index, right_data.edge_attr)
            right_x = self.ln(right_x)
            right_x = self.relu(right_x)

        return left_x, right_x


    def forward(self, left_ast, right_ast, left_data, right_data):


        left_mp_output, right_mp_output = self.message_passing(left_data, right_data)

        varindex1 = torch.as_tensor([left_ast['vars2id'][k] for k in left_ast['vars2id']], device=self.device)
        varindex2 = torch.as_tensor([right_ast['vars2id'][k] for k in right_ast['vars2id']], device=self.device)

        vars1 = torch.index_select(left_mp_output, 0, varindex1)

        # vars1 = vars1 + vars1.mean(axis=0)
        vars2 = torch.index_select(right_mp_output, 0, varindex2)
        # vars2 = vars2 + vars2.mean(axis=0)

        # vars1 = self.var_projector(vars1)
        # vars2 = self.var_projector(vars2)
        dot_products = torch.einsum('in, jn->ij', vars1, vars2)

        # probability_distributions = torch.softmax(dot_products, dim=1)

        num_vars_left_program = len(left_ast['vars2id'])
        num_vars_right_program = len(right_ast['vars2id'])

        split_res = torch.tensor_split(dot_products, num_vars_left_program)

        return split_res, left_mp_output


    def test_time_output(self, sample):

        left_sample, right_sample = sample
        l_data = Data(x=self.initial_embedding(left_sample[0]), edge_index=left_sample[1].t().contiguous(),
                      edge_attr=left_sample[2]).to(self.device)

        r_data = Data(x=self.initial_embedding(right_sample[0]), edge_index=right_sample[1].t().contiguous(),
                      edge_attr=right_sample[2]).to(self.device)
        output, leftmean = self.forward(left_sample[3], right_sample[3], l_data, r_data)

        # convert back to strings from id
        vars_left = left_sample[3]['vars2id']
        vars_right = right_sample[3]['vars2id']

        # print(vars_left)
        # print(vars_right)
        # print(output)
        indices = [torch.argmax(k) for k in output]
        distributions = [k.tolist() for k in output]

        vars_left_list = [k for k in vars_left]
        vars_right_list = [k for k in vars_right]

        varmap_result = {}
        varmap_dist = {}
        for e, o in enumerate(indices):
            varmap_result[vars_left_list[e]] = vars_right_list[int(indices[e].item())]
        # print(varmap_result)

        # assert 2 > 3
        for e, o in enumerate(distributions):
            varmap_dist[vars_left_list[e]] = (distributions[e], vars_right_list)

        return varmap_result, varmap_dist

    def train_step(self, sample, loss_function, optimizer):
        optimizer.zero_grad()
        left_sample, right_sample, labels, orig_spec = sample

        l_data = Data(x=self.initial_embedding(left_sample[0]), edge_index=left_sample[1].t().contiguous(),
                    edge_attr=left_sample[2]).to(self.device)

        r_data = Data(x=self.initial_embedding(right_sample[0]), edge_index=right_sample[1].t().contiguous(),
                      edge_attr=right_sample[2]).to(self.device)
        output, leftmean = self.forward(left_sample[3], right_sample[3], l_data, r_data)
        # global_orig_sample_list.append(orig_spec.parents[0])
        # global_representation_list.append(torch.mean(leftmean, dim=0).detach().cpu().numpy())
        total_loss = 0
        # print(labels)
        # print(len(labels))
        for lab, spl in zip(labels, output):
            # print(lab)
            # print(torch.softmax(spl, dim=1))

            l = loss_function(spl.reshape(1, -1), torch.tensor(lab, device=self.device).reshape(1))
            # print(l.item())
            total_loss += l
        # print(total_loss.item())
        # print()
        total_loss = total_loss / len(labels)
        total_loss.backward()
        #
        optimizer.step()

    def eval_step(self, sample, loss_function):

        left_sample, right_sample, labels, _ = sample

        l_data = Data(x=self.initial_embedding(left_sample[0]), edge_index=left_sample[1].t().contiguous(),
                      edge_attr=left_sample[2]).to(self.device)

        r_data = Data(x=self.initial_embedding(right_sample[0]), edge_index=right_sample[1].t().contiguous(),
                      edge_attr=right_sample[2]).to(self.device)
        output, leftmean = self.forward(left_sample[3], right_sample[3], l_data, r_data)

        total_loss = 0
        #
        corr = 0
        total = 0
        for lab, spl in zip(labels, output):
            # print(lab)
            # print(torch.softmax(spl, dim=1))

            # print(lab, torch.argmax(spl).item())
            if lab == torch.argmax(spl).item():

                corr += 1

            l = loss_function(spl.reshape(1, -1), torch.tensor(lab, device=self.device).reshape(1))
            # print(l.item())
            total_loss += l

            total += 1

        if total == corr:
            fully_correct = 1
        else:
            fully_correct = 0
        # print(total_loss.item())

        # print(f"Eval: {corr} / {total}")


        return corr, total, fully_correct