#!/usr/bin/python
#Title			: gen_progs_repr.py
#Usage			: python gen_progs_repr.py -h
#Author			: pmorvalho
#Date			: May 02, 2022
#Description     	: ProgReprGNNVisitor tries to represent a program as a list of edges of the AST's nodes, each node has a type and each variable is represented by a unique id (the id of the node where the variable first appeared)
#Notes			: 
#Python Version: 3.8.5
# (C) Copyright 2022 Pedro Orvalho.
#==============================================================================

import argparse
from sys import argv
from helper import *
from numpy import binary_repr
import pickle
import gzip
import pathlib
import random


# Edge types: 0: AST, 1: children order
# AST edges are the edges one can encounter in the AST
AST_EDGE=0
# Child edges establish an order between the children of an AST node.
CHILD_EDGE=1
# Write edges are connections between an ID node and its variable node. This edge indicates that the variable is being written.
WRITE_EDGE=2
# Read edges are connections between an ID node and its variable node. This edge indicates that the variable is being read.
READ_EDGE=3
# Chrono edges to establish an order between all the ID nodes connected to some variable
CHRONO_EDGE=4

incr_decr_ops = ["p++", "++", "--", "p--"]

#-----------------------------------------------------------------
# A visitor that represents a program as a list of lists of edges in the AST, a dictionary connecting each node to its type and a mapping between variables and the node_id that represents each variable.
class ProgReprGNNVisitor(c_ast.NodeVisitor):

    def __init__ (self):
        super().__init__()
        self.edge_list = list()
        self.type_map = dict()
        self.var_ids = dict()
        self.var_nodes = dict() # We are going to save all nodes where a given variable appears, at the end we are going to replace all of these nodes by the same node id.
        self.write_IDs = list()
        self.read_IDs = list()
        self.node_IDs_ordered = dict()        
                        
    
    def _repr_node(self, n_id, n_type):
        self.type_map[n_id] = get_type_id(n_type)
        if args.verbose:
            print("Node id:{i} of type {t}".format(i=n_id, t=n_type))

    def add_variable_edge(self, id_node):
        if id_node in self.var_nodes.keys():
            v_id = self.var_ids[self.var_nodes[id_node]]
            del self.var_nodes[id_node]
            if id_node in self.write_IDs and id_node in self.read_IDs:
                if args.verbose: 
                    print("variable edge (write and read) added: ", id_node, v_id)
                return [[id_node, v_id, AST_EDGE],[v_id, id_node, AST_EDGE], [id_node, v_id, WRITE_EDGE], [v_id, id_node, READ_EDGE]]
            elif id_node in self.write_IDs:
                if args.verbose: 
                    print("variable edge (write) added: ", id_node, v_id)
                return [[id_node, v_id, AST_EDGE],[v_id, id_node, AST_EDGE], [id_node, v_id, WRITE_EDGE]]
            else:
                if args.verbose: 
                    print("variable edge (read) added: ", id_node, v_id)
                return [[id_node, v_id, AST_EDGE],[v_id, id_node, AST_EDGE], [v_id, id_node, READ_EDGE]]                
        return []
        
    def connect_variable_nodes(self):
        double_edges = []
        id_2_var_edges = []
        for e in range(len(self.edge_list)):
            n1, n2, t = self.edge_list[e]
            id_2_var_edges += self.add_variable_edge(n1) + self.add_variable_edge(n2)
            if t == AST_EDGE:
                double_edges.append([n2, n1, t])
                
        self.edge_list += double_edges
        self.edge_list += id_2_var_edges

    def add_chrono_edges(self):
        for v in self.node_IDs_ordered.keys():
            id_nodes = self.node_IDs_ordered[v]
            for n1 in range(len(id_nodes)-1):
                id_1 = id_nodes[n1]
                id_2 = id_nodes[n1+1]
                if args.verbose:
                    print("Adding CHRONO edges:", id_1, id_2)
                self.edge_list.append([id_1, id_2, CHRONO_EDGE])
        
    _method_cache = None

    def visit(self, node, n_id):
        """ Visit a node.
        """

        if self._method_cache is None:
            self._method_cache = {}

        visitor = self._method_cache.get(node.__class__.__name__, None)
        if visitor is None:
            method = 'visit_' + node.__class__.__name__
            visitor = getattr(self, method, self.generic_visit)
            self._method_cache[node.__class__.__name__] = visitor

        return visitor(node, n_id)

    def visit_FileAST(self, node, n_id):
        #print('****************** Found FileAST Node *******************')
        n_ext = []
        fakestart_pos = -1 #for the case of our injected function which do not have the fakestart function in their ast
        for e in range(len(node.ext)):
            x = node.ext[e]
            # n_ext.append(self.visit(x, node_id(x.coord)))
            if isinstance(x, c_ast.FuncDef) and "fakestart" in x.decl.type.type.declname:
                fakestart_pos=e

        id_prev_child = -1
        for e in range(fakestart_pos+1, len(node.ext)):
            x = node.ext[e]
            n_ext.append(self.visit(x, node_id(x.coord)))
            if id_prev_child != -1:
                self.edge_list.append([id_prev_child, node_id(node.coord), CHILD_EDGE])
                id_prev_child = node_id(node.coord)
            
        n_file_ast = c_ast.FileAST(n_ext)

        self.connect_variable_nodes()
        self.add_chrono_edges()        

        
        return n_file_ast

    def visit_Decl(self, node, n_id):
        # print('****************** Found Decl Node *******************')
        self._repr_node(n_id, "Decl")
        id_prev_child=-1
        if node.name not in self.var_ids.keys() and isinstance(node.type, c_ast.TypeDecl):
            id_prev_child = node_id(node.coord, t="-decl-var")
            self.edge_list.append([n_id, id_prev_child, AST_EDGE])
            self.var_ids[node.name] = id_prev_child
            self._repr_node(id_prev_child, "Var-"+node.type.type.names[0])
        elif isinstance(node.type, c_ast.ArrayDecl):
            id_prev_child = node_id(node.type.coord, t="-decl-array")
            self.edge_list.append([n_id, id_prev_child, AST_EDGE])            
            self.type = self.visit(node.type, id_prev_child)
        # else:
        #     id_prev_child = node_id(node.coord, t="-decl-var")
        #     self.var_ids[node.name] = id_prev_child
        #     self.edge_list.append([n_id, self.var_ids[node.name], AST_EDGE])

        if not isinstance(node.type, c_ast.TypeDecl) and not isinstance(node.type, c_ast.ArrayDecl):
            if node.init is not None:
                new_child = node_id(node.init.coord, t="-decl-init")
                if id_prev_child != -1:                   
                    self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])

                self.edge_list.append([n_id, new_child, AST_EDGE])
                node.init = self.visit(node.init, new_child)
                id_prev_child=new_child

            # because it can be other type of declaration. Like func declarations.
            new_child = node_id(node.type.coord, t="decl-type")
            if id_prev_child != -1:                   
                self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])
            self.edge_list.append([n_id, new_child, AST_EDGE])        
            node.type = self.visit(node.type, new_child)
            return node

        if node.init is not None:
            new_child = node_id(node.init.coord, t="-decl-init")
            if id_prev_child != -1:                   
                self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])
            self.edge_list.append([n_id, new_child, AST_EDGE])
            node.init = self.visit(node.init, new_child)
            
        return node

    def visit_TypeDecl(self, node, n_id):
        # print('****************** Found Type Decl Node *******************')
        # attrs: declname, quals, align, type
        self._repr_node(n_id, "TypeDecl")
        if node.declname not in self.var_ids.keys():
            # id_prev_child = node_id(node.coord, t="TypeDecl-"+node.type.names[0])
            self.var_ids[node.declname] = n_id
        else:
            id_prev_child = self.var_ids[node.declname]
            self.edge_list.append([n_id, id_prev_child, AST_EDGE])        
        # self.type = self.visit(node.type)
        return node
    
    def visit_ArrayDecl(self, node, n_id):
        # print('****************** Found Array Decl Node *******************')
        self._repr_node(n_id, "ArrayDecl")
        child_id = node_id(node.type.coord, t="ptr-decl")
        self.edge_list.append([n_id, child_id, AST_EDGE])
        node.type = self.visit(node.type, child_id)
        # return node
        # if node.type.declname not in self.var_ids.keys():
        #     id_prev_child = node_id(node.coord, t="Array-"+node.type.type.names[0])
        #     self.var_ids[node.type.declname] = id_prev_child
        # else:
        #     id_prev_child = self.var_ids[node.type.declname]
        # self.edge_list.append([n_id, id_prev_child, AST_EDGE])        
        # self._repr_node(id_prev_child, "Array-"+node.type.type.names[0])
        id_prev_child = child_id
        if node.dim is not None:
            new_child = node_id(node.dim.coord, t="-array-dim")
            self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])
            self.edge_list.append([n_id, new_child, AST_EDGE])
            node.dim = self.visit(node.dim, new_child)
        return node

    def visit_PtrDecl(self, node, n_id):
        #print('****************** Found Pointer Decl Node *******************')
        self._repr_node(n_id, "PtrDecl")
        child_id = node_id(node.type.coord, t="ptr-decl")
        self.edge_list.append([n_id, child_id, AST_EDGE])
        node.type = self.visit(node.type, child_id)
        return node

    def visit_ArrayRef(self, node, n_id):
        #print('****************** Found Array Ref Node *******************')
        self._repr_node(n_id, "ArrayRef")
        id_prev_child = node_id(node.name.coord, t="array-name")
        self.edge_list.append([n_id, id_prev_child, AST_EDGE])
        node.name = self.visit(node.name, id_prev_child)
        new_child = node_id(node.subscript.coord, t="array-sub")
        self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])
        self.edge_list.append([n_id, new_child, AST_EDGE])
        node.subscript = self.visit(node.subscript, new_child)
        return node

    def visit_Assignment(self, node, n_id):
        # print('****************** Found Assignment Node *******************')
        self._repr_node(n_id, "Assignment")
        id_prev_child = node_id(node.rvalue.coord, t="-rvalue")
        self.edge_list.append([n_id, id_prev_child, AST_EDGE])
        node.rvalue = self.visit(node.rvalue, id_prev_child)
        new_child =  node_id(node.lvalue.coord, t="-lvalue")
        self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])
        self.edge_list.append([n_id, new_child, AST_EDGE])
        node.lvalue = self.visit(node.lvalue, new_child)
        if isinstance(node.lvalue, c_ast.ID):
            if args.verbose:
                print("Writing to variable in assignment in", new_child)
            self.write_IDs.append(new_child)
            self.read_IDs.remove(new_child)
        return node

    def visit_ID(self, node, n_id):
        #print('****************** Found ID Node *******************')
        self._repr_node(n_id, "ID")
        # the following is always true assuming that the variable is declared before being used
        if node.name in self.var_ids.keys():
            self.var_nodes[n_id] = node.name
        else:
            child_id = node_id(node.coord, t="-decl-var")
            # self.edge_list.append([n_id, child_id, AST_EDGE])
            self.var_ids[node.name] = child_id
        # append every Id node that uses variable "name"
        if node.name in self.node_IDs_ordered.keys():
            self.node_IDs_ordered[node.name].append(n_id)
        else:
            self.node_IDs_ordered[node.name] = [n_id]
        # every ID is considered a read node, in case of assignment and & operators this read node will be removed afterwards
        self.read_IDs.append(n_id)
        return node

    def visit_Constant(self, node, n_id):
        #print('****************** Found Constant Node *******************')
        self._repr_node(n_id, "Constant-"+str(node.value))
        return node
    
    def visit_ExprList(self, node, n_id):
        # print('****************** Found ExprList Node *******************')
        self._repr_node(n_id, "ExprList")
        id_prev_child=-1
        for e in node.exprs:
            new_child = node_id(e.coord, t="-exp")
            if id_prev_child != -1:
                self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])
            self.edge_list.append([n_id, new_child, AST_EDGE])
            e = self.visit(e, new_child)
            id_prev_child = new_child
        return node

    def visit_ParamList(self, node, n_id):
        # print('****************** Found ParamList Node *******************')
        self._repr_node(n_id, "ParamList")
        id_prev_child=-1
        for e in node.params:
            new_child = node_id(e.coord, t="-param")
            if id_prev_child != -1:
                self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])
            self.edge_list.append([n_id, new_child, AST_EDGE])
            e = self.visit(e, new_child)
            id_prev_child = new_child
        return node
    
    def visit_Cast(self, node, n_id):
        #print('******************** Found Cast Node *********************')
        self._repr_node(n_id, "Cast")
        child_id = node_id(node.expr.coord, t="-exp-cast")
        self.edge_list.append([n_id, child_id, AST_EDGE])
        node.expr = self.visit(node.expr, child_id)
        return node

    def visit_UnaryOp(self, node, n_id):
        #print('****************** Found Unary Operation *******************')
        self._repr_node(n_id, "UnaryOp-"+node.op)
        child_id = node_id(node.expr.coord, t="-exp"+node.op)
        self.edge_list.append([n_id, child_id, AST_EDGE])
        node.expr = self.visit(node.expr, child_id)
        if (node.op == "&" or node.op in incr_decr_ops) and isinstance(node.expr, c_ast.ID):
            if args.verbose:
                print("Writing to variable with ", node.op," operator in", child_id)
            self.write_IDs.append(child_id)
            if node.op == "&":
                self.read_IDs.remove(child_id)
        return node

    def visit_BinaryOp(self, node, n_id):
        #print('****************** Found Binary Operation *******************')
        self._repr_node(n_id, "BinaryOp-"+node.op)
        left_id = node_id(node.left.coord, t="-left"+node.op)
        self.edge_list.append([n_id, left_id, AST_EDGE])
        left = self.visit(node.left, left_id)
        right_id = node_id(node.right.coord, t="-right"+node.op)
        self.edge_list.append([left_id, right_id, CHILD_EDGE])
        self.edge_list.append([n_id, right_id, AST_EDGE])
        right = self.visit(node.right, right_id)
        return c_ast.BinaryOp(node.op, left, right, node.coord)

    def visit_TernaryOp(self, node, n_id):
        #print('****************** Found TernaryOp Node *******************')
        self._repr_node(n_id, "TernaryOp")
        id_prev_child=node_id(node.cond.coord, t="-cond")
        self.edge_list.append([n_id, id_prev_child, AST_EDGE])
        n_cond = self.visit(node.cond, id_prev_child)
        new_child = node_id(node.iftrue.coord, t="-iftrue")
        self.edge_list.append([n_id, new_child, AST_EDGE])
        self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])
        if isinstance(node.iftrue, c_ast.Compound):
            n_iftrue = self.visit(node.iftrue, new_child)
        else:
            n_iftrue = self.visit(c_ast.Compound([node.iftrue], node.iftrue.coord), new_child)        
        id_prev_child = new_child
        n_iffalse = node.iffalse
        if node.iffalse is not None and not isinstance(node.iffalse, c_ast.Compound):
            node.iffalse = c_ast.Compound([node.iffalse], node.iffalse.coord)
        if node.iffalse:
            new_child = node_id(node.iffalse.coord, t="-iffalse")
            self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])
            self.edge_list.append([n_id, new_child, AST_EDGE])
            n_iffalse = self.visit(node.iffalse, new_child)
        #print('****************** New Cond Node *******************')
        n_ternary = c_ast.TernaryOp(n_cond, n_iftrue, n_iffalse, node.coord)
        return n_ternary

    def visit_DeclArgs(self, node, parent_id):
        #print('****************** Found Declaration/Definition Parameters *******************')
        # deals with args in the declarations and definitions of functions
        child_id=None
        if node.args:
            child_id=node_id(node.args.coord, t="-larg")
            self.edge_list.append([parent_id, child_id, AST_EDGE])
            node.args = self.visit(node.args, child_id)
                
        return node, child_id

    def visit_FuncDecl(self, node, n_id):
        #print('****************** Found FuncDecl Node *******************')
        self._repr_node(n_id, "FuncDecl")
        node, _ = self.visit_DeclArgs(node, n_id)
        return node

    def visit_FuncDef(self, node, n_id):
        #print('****************** Found FuncDef Node *******************')
        self._repr_node(n_id, "FuncDef")
        decl = node.decl
        param_decls = node.param_decls
        id_prev_child=-1
        if node.param_decls:
            id_prev_child=node_id(node.param_decls.coord, t="-param")
            self.edge_list.append([n_id, id_prev_child, AST_EDGE])
            param_decls = self.visit(node.param_decls, id_prev_child)
        if "main" != node.decl.name and "fakestart" != node.decl.name: #ignore main function
            # if the function has parameters add them to the scope
            decl, child_id = self.visit_DeclArgs(decl.type, n_id)
            if child_id != None:
                if id_prev_child != -1:
                    self.edge_list.append([id_prev_child, child_id, CHILD_EDGE])
                id_prev_child=child_id
                
        body = node.body
        coord = node.coord
        new_child = node_id(node.body.coord, t="-body")
        if id_prev_child != -1:
            self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])
        self.edge_list.append([n_id, new_child, AST_EDGE])
        n_body_1 = self.visit(body, new_child)
        n_func_def_ast = c_ast.FuncDef(decl, param_decls, n_body_1, coord)

        return n_func_def_ast

    def visit_FuncCall(self, node, n_id):
        #print('****************** Found FuncCall Node *******************')
        self._repr_node(n_id, "FuncCall")
        if node.args:
            child_id = node_id(node.args.coord, t="-args")
            self.edge_list.append([n_id, child_id, AST_EDGE])
            node.args = self.visit(node.args, child_id)
        return c_ast.FuncCall(node.name, node.args, node.coord)
    
    def visit_Compound(self, node, n_id):
        #print('****************** Found Compound Node *******************')
        self._repr_node(n_id, "Block")

        block_items = node.block_items
        coord = node.coord
        n_block_items = []
        id_prev_child=-1
        if block_items is not None:
            for x in block_items:
                new_child=node_id(x.coord, t="-inst")
                if id_prev_child != -1:
                    self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])
                self.edge_list.append([n_id, new_child, AST_EDGE])
                n_block_items.append(self.visit(x, new_child))
                id_prev_child = new_child

        n_compound_ast = c_ast.Compound(n_block_items, coord)
        return n_compound_ast

    def visit_If(self, node, n_id):
        #print('****************** Found IF Node *******************')
        self._repr_node(n_id, "If")
        id_prev_child=node_id(node.cond.coord, t="-cond")
        self.edge_list.append([n_id, id_prev_child, AST_EDGE])
        n_cond = self.visit(node.cond, id_prev_child)
        new_child = node_id(node.iftrue.coord, t="-iftrue")
        self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])
        self.edge_list.append([n_id, new_child, AST_EDGE])        
        n_iftrue = self.visit(node.iftrue, new_child)
        if isinstance(node.iftrue, c_ast.Compound):
            n_iftrue = self.visit(node.iftrue, new_child)
        else:
            n_iftrue = self.visit(c_ast.Compound([node.iftrue], node.iftrue.coord), new_child)
        
        id_prev_child = new_child
        n_iffalse = node.iffalse
        if node.iffalse is not None and not isinstance(node.iffalse, c_ast.Compound):
            node.iffalse = c_ast.Compound([node.iffalse], node.iffalse.coord)
        if node.iffalse:
            new_child = node_id(node.iffalse.coord, t="-iffalse")
            self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])
            self.edge_list.append([n_id, new_child, AST_EDGE])        
            n_iffalse = self.visit(node.iffalse, new_child)
        #print('****************** New Cond Node *******************')
        n_if = c_ast.If(n_cond, n_iftrue, n_iffalse, node.coord)
        return n_if

    def visit_For(self, node, n_id):
        #print('****************** Found For Node *******************')
        self._repr_node(n_id, "For")
        id_prev_child = -1
        if node.init is not None:
            id_prev_child = node_id(node.init.coord, t="-init")
            self.edge_list.append([n_id, id_prev_child, AST_EDGE])
        n_init = self.visit(node.init, id_prev_child)
        new_child = node_id(node.cond.coord, t="-cond")
        if id_prev_child != -1:
            self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])
        self.edge_list.append([n_id, new_child, AST_EDGE])
        n_cond = self.visit(node.cond, new_child)
        id_prev_child = new_child
        if not isinstance(node.stmt, c_ast.Compound):
            node.stmt = c_ast.Compound([node.stmt], node.stmt.coord)
        new_child = node_id(node.stmt.coord, t="-stmt")
        self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])
        self.edge_list.append([n_id, new_child, AST_EDGE])
        n_stmt = self.visit(node.stmt, new_child)
        id_prev_child = new_child
        n_next = node.next
        if n_next is not None:
            new_child = node_id(node.next.coord, t="-next")
            self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])
            self.edge_list.append([n_id, new_child, AST_EDGE])
            n_next = self.visit(node.next, new_child)
        # We dont need to put a scope_info at the end of the for because the compound node already does that
        n_for = c_ast.For(n_init, n_cond, n_next, n_stmt, node.coord)
        return n_for

    def visit_While(self, node, n_id):
        #print('****************** Found While Node *******************')
        self._repr_node(n_id, "While")
        child_id = node_id(node.cond.coord, t="-cond")
        self.edge_list.append([n_id, child_id, AST_EDGE])
        n_cond = self.visit(node.cond, child_id)
        if not isinstance(node.stmt, c_ast.Compound):
            node.stmt = c_ast.Compound([node.stmt], node.stmt.coord)
        new_child = node_id(node.stmt.coord, t="-stmt")
        self.edge_list.append([child_id, new_child, CHILD_EDGE])
        self.edge_list.append([n_id, new_child, AST_EDGE])
        n_stmt = self.visit(node.stmt, new_child)
        n_while = c_ast.While(n_cond, n_stmt, node.coord)
        return n_while

    def visit_DoWhile(self, node, n_id):
        #print('****************** Found DoWhile Node *******************')
        self._repr_node(n_id, "DoWhile")
        child_id = node_id(node.cond.coord, t="-cond")
        self.edge_list.append([n_id, child_id, AST_EDGE])
        n_cond = self.visit(node.cond, child_id)
        if not isinstance(node.stmt, c_ast.Compound):
            node.stmt = c_ast.Compound([node.stmt], node.stmt.coord)
        new_child = node_id(node.stmt.coord, t="-stmt")
        self.edge_list.append([child_id, new_child, CHILD_EDGE])
        self.edge_list.append([n_id, new_child, AST_EDGE])
        n_stmt = self.visit(node.stmt, new_child)
        n_dowhile = c_ast.DoWhile(n_cond, n_stmt, node.coord)
        return n_dowhile

    def visit_Switch(self, node, n_id):
        #print('****************** Found Switch Node *******************')
        self._repr_node(n_id, "Switch")
        child_id = node_id(node.cond.coord, t="-cond")
        self.edge_list.append([n_id, child_id, AST_EDGE])
        n_cond = self.visit(node.cond, child_id)
        if not isinstance(node.stmt, c_ast.Compound):
            node.stmt = c_ast.Compound([node.stmt], node.stmt.coord)
        new_child = node_id(node.stmt.coord, t="-stmt")
        self.edge_list.append([child_id, new_child, CHILD_EDGE])
        self.edge_list.append([n_id, new_child, AST_EDGE])        
        n_stmt = self.visit(node.stmt, new_child)
        n_switch = c_ast.Switch(n_cond, n_stmt, node.coord)
        return n_switch

    def visit_Return(self, node, n_id):
        #print('****************** Found Return Node *******************')
        self._repr_node(n_id, "Return")
        if node.expr:
            child_id = node_id(node.expr.coord, t="-expr")
            self.edge_list.append([n_id, child_id, AST_EDGE])
            node.expr = self.visit(node.expr, child_id)
        return node

    def visit_Break(self, node, n_id):
        #print('****************** Found Break Node *******************')
        self._repr_node(n_id, "Break")
        return node

    def visit_Continue(self, node, n_id):
        #print('****************** Found Continue Node *******************')
        self._repr_node(n_id, "Continue")
        return node

    def visit_Case(self, node, n_id):
        #print('****************** Found Case Node *******************')
        self._repr_node(n_id, "Case")
        n_stmts_1 = []
        id_prev_child = -1                
        for x in node.stmts:
            new_child = node_id(x.coord, t="-stmt")
            if id_prev_child != -1:
                self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])
            self.edge_list.append([n_id, new_child, AST_EDGE])
            n_stmts_1.append(self.visit(x, new_child))
            id_prev_child = new_child
            
        n_stmts_2 = c_ast.Compound (n_stmts_1, node.coord)
        return c_ast.Case(node.expr, n_stmts_2, node.coord)

    def visit_Default(self, node, n_id):
        #print('****************** Found Default Node *******************')
        self._repr_node(n_id, "Default")
        n_stmts_1 = []
        id_prev_child = -1                
        for x in node.stmts:
            new_child = node_id(x.coord, t="-stmt")
            if id_prev_child != -1:
                self.edge_list.append([id_prev_child, new_child, CHILD_EDGE])
            self.edge_list.append([n_id, new_child, AST_EDGE])
            n_stmts_1.append(self.visit(x, new_child))
            id_prev_child = new_child
            
        n_stmts_2 = c_ast.Compound(n_stmts_1, node.coord)
        return c_ast.Default(n_stmts_2, node.coord)

    def visit_EmptyStatement(self, node, n_id):
        #print('****************** Found EmptyStatement Node *******************')
        self._repr_node(n_id, "EmptyStatement")
        return node

    def generic_visit(self, node, n_id):
        #print('******************  Something else ************')
        return node

#-----------------------------------------------------------------

def load_types_dict():
    dict_name = "types2int.pkl.gz"
    if not os.path.exists(dict_name):
        types2int = dict()
        types2int["diff_types"] = 0
    else:
        fp=gzip.open(dict_name,'rb') # This assumes that primes.data is already packed with gzip
        types2int=pickle.load(fp)
        fp.close()

    return types2int

def save_types_dict():
    dict_name = "types2int.pkl.gz"
    fp=gzip.open(dict_name,'wb')
    pickle.dump(types2int,fp)
    fp.close()

def get_type_id(t):
    global types2int
    if t in types2int.keys():
        return types2int[t]
    else:
        cur_cnt = types2int["diff_types"]
        types2int[t] = cur_cnt
        types2int["diff_types"] = cur_cnt+1
        return cur_cnt
        
def save_progs_repr(p_dict, p_dir, p, rep):
    stu=str(p).split("/")[-1].replace(".c","")
    file_name = p_dir+"/{r}-{s}.pkl.gz".format(s=stu, r=rep)
    fp=gzip.open(file_name,'wb')
    pickle.dump(p_dict,fp)
    fp.close()
    
#-----------------------------------------------------------------

def gen_program_repr_gnn(progs_dir):
    reprs = []
    progs = list(pathlib.Path(progs_dir).glob('*.c'))
    
    for p in progs:
        prog_repr = dict()
        tmp_dir = "/tmp/tmp-{n}".format(n=int(random.random()*100000000))
        inst_file, sincludes, includes = make_output_dir(p, tmp_dir)
        try:
            ast = parse_file(inst_file, use_cpp=True,
            cpp_path='gcc',
            cpp_args=['-E', '-Iutils/fake_libc_include'])
        except:
            print("Error on compiling program:", p)
            os.system("echo {p} >> programs_generations_err-programs-compilation-errors.txt".format(p=p))
            continue

        reset_ids()
        v = ProgReprGNNVisitor()
        n_ast = v.visit(ast, 0)
        # n_ast.show()
        prog_repr["edges"] = v.edge_list
        prog_repr["nodes2types"] = v.type_map
        prog_repr["vars2id"] = v.var_ids
        if args.verbose:
            print("Edge list with {e} edges:".format(e=len(v.edge_list)))
            print(v.edge_list)
            print("Type map with {v} nodes:".format(v=len(v.type_map.keys())))
            print(v.type_map)
            print("Var map with {v} variables:".format(v=len(v.var_ids.keys())))
            print(v.var_ids)
            print("General type dict with {t} types:".format(t=len(types2int.keys())-1))
            print(types2int)
        try:
            max_node = max(v.type_map.keys())+1
            assert(len(v.type_map.keys()) == max_node)
            for e in v.edge_list:
                assert(max(e) <= max_node)
        except:
            print("ERROR Unvisited Nodes in {p}!!".format(p=p))
            os.system("echo {p} >> programs_generations_err-unvisited_nodes.txt".format(p=p))
        # exit() # considers only one program for now
        os.system("rm -rf {t}".format(t=tmp_dir))
        save_progs_repr(prog_repr, progs_dir, p, "ast")

#-----------------------------------------------------------------

def parser():
    parser = argparse.ArgumentParser(prog='gen_progs_repr.py', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-d', '--input_dir', help='Name of the input directory.')
    # parser.add_argument('-o', '--output_dir', help='Name of the output directory.')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='Prints debugging information.')
    args = parser.parse_args(argv[1:])
    return args

if __name__ == "__main__":
    args = parser()
    if len(sys.argv) >= 2:
        progs_dir = args.input_dir
        types2int = load_types_dict()
        gen_program_repr_gnn(progs_dir)
        # the following is commented so we can run this script in parallel. This only works if the dictionary was already previously computed.
        # save_types_dict() 
    else:
        print('python {0} -h'.format(sys.argv[0]))
        
