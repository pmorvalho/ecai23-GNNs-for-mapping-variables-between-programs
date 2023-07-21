#!/usr/bin/python
#Title			: prog_fixer.py
#Usage			: python prog_fixer.py -h
#Author			: pmorvalho
#Date			: July 12, 2022
#Description	        : Module responsible for renaming the variables of the incorrect program with the variables of the correct program and to call the independent repair processes. 
#Notes			: 
#Python Version: 3.8.5
# (C) Copyright 2022 Pedro Orvalho.
#==============================================================================

import argparse
from sys import argv
import sys, os
from copy import deepcopy
import argparse
from shutil import copyfile
from itertools import product
from numpy import binary_repr
import pickle
import gzip
import pathlib
import numpy as np
import time

# This is not required if you've installed pycparser into
# your site-packages/ with setup.py
sys.path.extend(['.', '..'])

from pycparser import c_parser, c_ast, parse_file, c_generator
from helper import *

#-----------------------------------------------------------------

bin_ops_mirror = {"<" : ">", ">" : "<", "<=" : ">=", ">=" : "<=", "==" : "==", "!=" : "!="}
bin_ops_2_swap = {"<" : "<=", ">" : ">=", "<=" : "<", ">=" : ">", "==" : "=", "!=" : "=="}
bin_ops_2_fix = dict((v, k) for k, v in bin_ops_2_swap.items())
incr_decr_ops = {"p++" : "++", "++" : "p++", "--" : "p--", "p--" : "--"}
inc_decr_ops_2_fix = dict((v, k) for k, v in incr_decr_ops.items())

#-----------------------------------------------------------------
# A visitor that renames all the variables' IDs in a program with the variable mapping passed as input
class VariableRenamerVisitor(ASTVisitor):
    def __init__ (self, var_map):
        super().__init__()
        self.var_map = var_map

    def visit_Decl(self, node):
        #print('****************** Found Decl Node *******************')
        # print(node)
        if not isinstance(node.type, c_ast.TypeDecl):
            # print(node)
            # if node.init is not None:
            #     node.init = self.visit(node.init)
            # # because it can be other type of declaration. Like func declarations.
            # node.type = self.visit(node.type)
            return node

        if node.init != None:
            node.init=self.visit(node.init)

        if node.type.declname in self.var_map.keys():
            node.type.declname = self.var_map[node.type.declname]
            
        return node
    
    def visit_ID(self, node):
        #print('****************** Found ID Node *******************')
        if node.name in self.var_map.keys():
            node.name = self.var_map[node.name]
        return node

#-----------------------------------------------------------------

                 # WRONG COMPARISON OPERATOR

#-----------------------------------------------------------------
# A visitor that visit all the comparison operations and saves a list of interesting operations to fix
class CompOpVisitor(ASTVisitor):
    
    def __init__ (self):
        super().__init__()
        self.bin_ops_2_fix = list()
        self.binary_ops = dict()

    def visit_BinaryOp(self, node):
        # print('****************** Found Binary Operation *******************')
        # print(node.show())
        left = self.visit(node.left)
        right = self.visit(node.right)
        # if node.op in bin_ops_2_fix.keys():
        #     print(node.show())
        r_node = str(node.right) if not isinstance(node.right, c_ast.ID) else node.right.name
        l_node = str(node.left) if not isinstance(node.left, c_ast.ID) else node.left.name
        op = node.op
        if (l_node, r_node) in self.binary_ops.keys():
            self.binary_ops[(l_node, r_node)].append([op, node_id(node.coord)])
        else:
            self.binary_ops[(l_node, r_node)] = list([[op, node_id(node.coord)]])
        if "p++" in l_node or "p--" in l_node or "p++" in r_node or "p--" in r_node:
            l_node = l_node.replace("p++","++") if "p++" in l_node else l_node.replace("p--","--")
            r_node = r_node.replace("p++","++") if "p++" in r_node else r_node.replace("p--","--")
            if (l_node, r_node) in self.binary_ops.keys():
                self.binary_ops[(l_node, r_node)].append([op, node_id(node.coord)])
            else:
                self.binary_ops[(l_node, r_node)] = list([[op, node_id(node.coord)]])

        return c_ast.BinaryOp(node.op, left, right, node.coord)

#-----------------------------------------------------------------
# A visitor that tries to fix the wrong comparison operator bug
class WrongCompOpFixerVisitor(ASTVisitor):
    
    def __init__ (self, inc_prog_bin_ops, correct_prog_bin_ops):
        super().__init__()
        self.possible_fixes = list()
        for k in correct_prog_bin_ops.keys():
            if k in inc_prog_bin_ops.keys():
                inc_prog_ops, cor_prog_ops = inc_prog_bin_ops[k], correct_prog_bin_ops[k]
                for o, _ in cor_prog_ops:
                    if o not in inc_prog_ops or inc_prog_ops.count(o) < cor_prog_ops.count(o):
                        for o2, i in inc_prog_ops:
                            if o == o2:
                                continue
                            fix = [i, o, k]
                            if fix not in self.possible_fixes:
                                self.possible_fixes.append(fix)
                        if o == '==':
                            self.possible_fixes.append([None, '==', k[0], k[1]])

            else:
                inv_k=k[::-1]
                if inv_k in inc_prog_bin_ops:
                    for o, _ in correct_prog_bin_ops[k]:
                        inc_prog_ops, cor_prog_ops = inc_prog_bin_ops[inv_k], correct_prog_bin_ops[k]
                        if o not in bin_ops_mirror.keys():
                            continue
                        inv_o=bin_ops_mirror[o]
                        if inv_o not in inc_prog_ops or inc_prog_ops.count(inv_o) < cor_prog_ops.count(o):
                            for o2, i in inc_prog_ops:
                                if inv_o == o2:
                                    continue
                                fix = [i, inv_o, inv_k]
                                if fix not in self.possible_fixes:
                                    self.possible_fixes.append(fix)
                            if o == '==':
                                self.possible_fixes.append([None, '==', inv_k[0], inv_k[1]])
                for o, _ in correct_prog_bin_ops[k]:
                    if o == '==':
                        self.possible_fixes.append([None, '==', k[0], k[1]])
                        self.possible_fixes.append([None, '==', k[1], k[0]])
                        
    def next_repair(self):
        if len(self.possible_fixes) > 0:
            self.possible_fixes.pop(0)

    def visit_Assignment(self, node):
        # print('****************** Found Assignment Node *******************')
        prv_pn = self.pn # parent node, declared in ASTVisitor 
        self.pn = self.get_node_name(node)
        n_str = str(node)
        r_node = str(node.rvalue) if not isinstance(node.rvalue, c_ast.ID) else node.rvalue.name
        l_node = str(node.lvalue) if not isinstance(node.lvalue, c_ast.ID) else node.lvalue.name

        if len(self.possible_fixes) > 0:
            if self.possible_fixes[0][0] is None:
                _, op, lv, rv = self.possible_fixes[0]
                if lv == l_node and rv == r_node:
                    node.op = op
                    self.pn = prv_pn
                    return node
        node.rvalue = self.visit(node.rvalue)
        node.lvalue = self.visit(node.lvalue)
        self.pn = prv_pn
        return node
    
    def visit_BinaryOp(self, node):
        # print('****************** Found Binary Operation *******************')
        # print(node.show())
        prv_pn = self.pn # parent node, declared in ASTVisitor 
        self.pn = self.get_node_name(node)
        left = self.visit(node.left)
        right = self.visit(node.right)
        r_node = str(node.right) if not isinstance(node.right, c_ast.ID) else node.right.name
        l_node = str(node.left) if not isinstance(node.left, c_ast.ID) else node.left.name
        n_id = node_id(node.coord)
        if len(self.possible_fixes) > 0:
            if n_id == self.possible_fixes[0][0] and (l_node,r_node) == self.possible_fixes[0][2]:
                node.op = self.possible_fixes[0][1] # the fixed comparison operator

        self.pn = prv_pn
        return c_ast.BinaryOp(node.op, left, right, node.coord)
    
#-----------------------------------------------------------------

                 # VARIABLE MISUSE

#-----------------------------------------------------------------
# A visitor that visits all the ID nodes and saves the info for every variable in the AST
# the idea is in the future to keep also the information about the parent node for each ID node.
class VarInfoVisitor(ASTVisitor):
    
    def __init__ (self):
        super().__init__()
        self.var_usage = dict()
        self.var_node_ids = dict()

    def visit_Decl(self, node):
        #print('****************** Found Decl Node *******************')
        if not isinstance(node.type, c_ast.TypeDecl):
            return node
        if node.init != None:
            node.init=self.visit(node.init)

        v_id = node.type.declname
        if v_id in self.var_usage.keys():
            self.var_usage[v_id] += 1
            # self.var_node_ids[v_id].append(node_id(node.coord))
        else:
            self.var_usage[v_id] = 0
            self.var_node_ids[v_id] = list() # [node_id(node.coord)]
        return node
    
    def visit_ID(self, node):
        #print('****************** Found ID Node *******************')
        v_id = node.name
        if v_id in self.var_usage.keys():
            self.var_usage[v_id] += 1
            self.var_node_ids[v_id].append(node_id(node.coord))            
        else:
            self.var_usage[v_id] = 1
            self.var_node_ids[v_id] = [node_id(node.coord)]            

        return node

#-----------------------------------------------------------------
# A visitor that tries to fix the bug of variable misuse
class VarMisuseFixerVisitor(ASTVisitor):
    
    def __init__ (self, inc_prog_var_usage, cor_prog_var_usage, inc_prog_vars_ids, cor_prog_vars_ids):
        super().__init__()
        self.inc_prog_vars_ids = inc_prog_vars_ids
        self.cor_prog_vars_ids = cor_prog_vars_ids
        self.var_2_del = None
        self.var_2_insert = None
        for k in inc_prog_var_usage.keys():
            if k in cor_prog_var_usage.keys():
                v_i, v_c = inc_prog_var_usage[k], cor_prog_var_usage[k]
                if v_i == v_c:
                    continue
                if v_i < v_c:
                    self.var_2_insert = k
                else:
                    self.var_2_del = k

        
        self.var_2_del_ids = self.inc_prog_vars_ids[self.var_2_del] if self.var_2_del is not None else []

    def next_repair(self):
        if len(self.var_2_del_ids) > 0:
            self.var_2_del_ids.pop(0)

    def visit_Decl(self, node):
        #print('****************** Found Decl Node *******************')
        if not isinstance(node.type, c_ast.TypeDecl):
            return node
        if node.init != None:
            node.init=self.visit(node.init)

        v_id = node.type.declname
        if len(self.var_2_del_ids) > 0 and v_id == self.var_2_del:
            if self.var_2_del_ids[0] == node_id(node.coord):
                node.type.declname = self.var_2_insert
        
        return node
    
    def visit_ID(self, node):
        #print('****************** Found ID Node *******************')
        v_id = node.name
        if len(self.var_2_del_ids) > 0 and v_id == self.var_2_del:
            if self.var_2_del_ids[0] == node_id(node.coord):
                node.name = self.var_2_insert
                
        return node

#-----------------------------------------------------------------

                 # EXPRESSION DELETION

#-----------------------------------------------------------------
# A visitor that visits all the assignment nodes and saves their info
class AssignmentVisitor(ASTVisitor):
    
    def __init__ (self):
        super().__init__()
        self.assignments = dict()

    def visit_Assignment(self, node):
        # print('****************** Found Assignment Node *******************')
        prv_pn = self.pn # parent node, declared in ASTVisitor 
        self.pn = self.get_node_name(node)
        n_str = str(node)+"-"+prv_pn
        
        if n_str not in self.assignments.keys():
            self.assignments[n_str] = {"pn":prv_pn, "cnt": 1, "obj": deepcopy(node)}
        else:
            self.assignments[n_str] = {"pn":prv_pn, "cnt": self.assignments[n_str]["cnt"]+1, "obj": deepcopy(node)}

        node.rvalue = self.visit(node.rvalue)
        node.lvalue = self.visit(node.lvalue)
        self.pn = prv_pn
        return node

#-----------------------------------------------------------------
# A visitor that finds possible places to insert assignment expressions
class Places4AssignmentsVisitor(ASTVisitor):
    
    def __init__ (self, asg_2_ins):
        super().__init__()
        self.parents_names = dict()
        for x,y in asg_2_ins:
            if x not in self.parents_names.keys():
                self.parents_names[x] = [y]
            else:
                self.parents_names[x].append(y)
                
        self.possible_places = list()

    def get_possible_places(self):
        return self.possible_places

    def visit_FileAST(self, node):
        #print('****************** Found FileAST Node with Parent Node ****************')
        n_ext = []
        fakestart_pos = -1 #for the case of our injected function which do not have the fakestart function in their ast
        prv_pn = self.pn
        self.pn = self.get_node_name(node)        
        for e in range(len(node.ext)):
            x = node.ext[e]
            # n_ext.append(self.visit(x, node_id(x.coord)))
            if isinstance(x, c_ast.FuncDef) and "fakestart" in x.decl.type.type.declname:
                fakestart_pos=e

        for e in range(fakestart_pos+1, len(node.ext)):
            x = node.ext[e]
            n_ext.append(self.visit(x))

        self.pn = prv_pn
        n_file_ast = c_ast.FileAST(n_ext)
        return n_file_ast
    
    def visit_ExprList(self, node):
        #print('****************** Found ExprList Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        coord = node.coord
        if self.pn in self.parents_names.keys():
            if node.exprs:
                for a in self.parents_names[self.pn]:
                    self.possible_places = self.possible_places + [[node_id(coord), i, a] for i in range(len(self.exprs)+1)]
        for e in node.exprs:
            e = self.visit(e)
        self.pn = prv_pn
        return node

    def visit_TernaryOp(self, node):
        #print('****************** Found TernaryOp Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        coord = node.coord
        n_cond = self.visit(node.cond)
        if self.pn in self.parents_names.keys() and (n_cond is None or isinstance(n_cond, c_ast.EmptyStatement)):
            for a in self.parents_names[self.pn]:
                self.possible_places.append([node_id(coord), 0, a])
            
        n_iftrue = self.visit(node.iftrue)
        n_iffalse = node.iffalse
        if node.iffalse:
            n_iffalse = self.visit(node.iffalse)
        #print('****************** New Cond Node with Parent Node '+self.pn+'****************')
        n_ternary = c_ast.TernaryOp(n_cond, n_iftrue, n_iffalse, node.coord)
        self.pn = prv_pn
        return n_ternary

    def visit_Compound(self, node):
        #print('****************** Found Compound Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        block_items = node.block_items
        coord = node.coord
        n_block_items = []
        idx_last_decl = 0
        if self.pn in self.parents_names.keys():
            if block_items is not None:
                for i in range(len(block_items)):
                    x = block_items[i]
                    if isinstance(x, c_ast.Decl):
                        idx_last_decl=i+1
                        continue
                    else:
                        break
                
            for a in self.parents_names[self.pn]:
                if block_items is None:
                    self.possible_places.append([node_id(coord), 0, a])
                else:
                    self.possible_places = self.possible_places + [[node_id(coord), i, a] for i in range(idx_last_decl, len(block_items)+1)]

        if "For" in self.parents_names.keys():
            if block_items is not None:
                for i in range(len(block_items)):
                    x = block_items[i]
                    if isinstance(x, c_ast.Decl):
                        idx_last_decl=i+1
                        continue
                    else:
                        break
                
            for a in self.parents_names["For"]:
                if block_items is not None:
                    for i in range(idx_last_decl,len(block_items)):
                        x = block_items[i]
                        if isinstance(x, c_ast.While):
                            self.possible_places.append([node_id(coord), i, a])
                    self.possible_places.append([node_id(coord), len(block_items), a])
        
        if block_items is not None:
            for x in block_items:
                n_block_items.append(self.visit(x))

        n_compound_ast = c_ast.Compound(n_block_items, coord)
        self.pn = prv_pn
        return n_compound_ast

    def visit_If(self, node):
        #print('****************** Found IF Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        coord = node.coord
        n_cond = self.visit(node.cond)
        if self.pn in self.parents_names.keys() and (n_cond is None or isinstance(n_cond, c_ast.EmptyStatement)):
            for a in self.parents_names[self.pn]:
                self.possible_places.append([node_id(coord), 0, a])
        n_iftrue = self.visit(node.iftrue)
        n_iffalse = node.iffalse
        if node.iffalse:
            n_iffalse = self.visit(node.iffalse)
        #print('****************** New Cond Node with Parent Node '+self.pn+'****************')
        n_if = c_ast.If(n_cond, n_iftrue, n_iffalse, node.coord)
        self.pn = prv_pn
        return n_if

    def visit_For(self, node):
        #print('****************** Found For Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        coord = node.coord
        n_init = self.visit(node.init)
        if self.pn in self.parents_names.keys() and (n_init is None or isinstance(n_init, c_ast.EmptyStatement)):
            for a in self.parents_names[self.pn]:
                self.possible_places.append([node_id(coord), 0, a])
        n_cond = self.visit(node.cond)
        if self.pn in self.parents_names.keys() and (n_cond is None or isinstance(n_cond, c_ast.EmptyStatement)):
            for a in self.parents_names[self.pn]:            
                self.possible_places.append([node_id(coord), 1, a])
        n_stmt = self.visit(node.stmt)
        n_next = node.next
        if self.pn in self.parents_names.keys() and (n_next is None or isinstance(n_next, c_ast.EmptyStatement)):
            for a in self.parents_names[self.pn]:
                self.possible_places.append([node_id(coord), 2, a])
        if n_next is not None:
            n_next = self.visit(node.next)
            

        n_for = c_ast.For(n_init, n_cond, n_next, n_stmt, node.coord)
        self.pn = prv_pn
        return n_for

    def visit_While(self, node):
        #print('****************** Found While Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        coord = node.coord
        n_cond = self.visit(node.cond)
        if self.pn in self.parents_names.keys() and (n_cond is None or isinstance(n_cond, c_ast.EmptyStatement)):
            for a in self.parents_names[self.pn]:
                self.possible_places.append([node_id(coord), 0, a])
        n_stmt = self.visit(node.stmt)
        n_while = c_ast.While(n_cond, n_stmt, node.coord)
        self.pn = prv_pn
        return n_while

    def visit_DoWhile(self, node):
        #print('****************** Found DoWhile Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        coord = node.coord
        n_cond = self.visit(node.cond)
        if self.pn in self.parents_names.keys() and (n_cond is None or isinstance(n_cond, c_ast.EmptyStatement)):
            for a in self.parents_names[self.pn]:
                self.possible_places.append([node_id(coord), 0, a])
        n_stmt = self.visit(node.stmt)
        n_dowhile = c_ast.DoWhile(n_cond, n_stmt, node.coord)
        self.pn = prv_pn
        return n_dowhile

    
#-----------------------------------------------------------------
# A visitor that finds possible places to insert assignment expressions
class AssignmentInsertionVisitor(ASTVisitor):
    
    def __init__ (self, ast, assigns_inc_prog, assigns_cor_prog):
        super().__init__()
        self.asg_2_ins = list() # list of assignments that can be inserted
        self.possible_fixes = list()
        for k in assigns_cor_prog:
            if (k not in assigns_inc_prog) or (k in assigns_inc_prog and assigns_cor_prog[k]["cnt"] > assigns_inc_prog[k]["cnt"]):
                self.asg_2_ins.append([assigns_cor_prog[k]["pn"], assigns_cor_prog[k]["obj"]]) # a tuple with the parent node name and the object of the assignment to use as replacement

        l4p = Places4AssignmentsVisitor(self.asg_2_ins)
        l4p.visit(ast)
        self.possible_fixes = l4p.get_possible_places()
        # print(self.possible_fixes)
        if self.possible_fixes is not None and len(self.possible_fixes) > 0:
            self.n_id, self.idx, self.asg = self.possible_fixes[0]

    def next_repair(self):
        self.possible_fixes.pop(0)
        if len(self.possible_fixes) > 0:
            self.n_id, self.idx, self.asg = self.possible_fixes[0]
                
    def visit_ExprList(self, node):
        #print('****************** Found ExprList Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        n_id = node_id(node.coord)
        if n_id == self.n_id:
            node.exprs.insert(self.idx, self.asg)
            self.pn = prv_pn
            return node
        for e in node.exprs:
            e = self.visit(e)
        self.pn = prv_pn
        return node

    def visit_TernaryOp(self, node):
        #print('****************** Found TernaryOp Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        n_id = node_id(node.coord)
        if n_id == self.n_id and self.idx == 0:
            node.cond = self.asg
            self.pn = prv_pn
            return node
        n_cond = self.visit(node.cond)
        n_iftrue = self.visit(node.iftrue)
        n_iffalse = node.iffalse
        if node.iffalse:
            n_iffalse = self.visit(node.iffalse)
        #print('****************** New Cond Node with Parent Node '+self.pn+'****************')
        n_ternary = c_ast.TernaryOp(n_cond, n_iftrue, n_iffalse, node.coord)
        self.pn = prv_pn
        return n_ternary

    def visit_Compound(self, node):
        #print('****************** Found Compound Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        block_items = node.block_items
        coord = node.coord
        n_id = node_id(node.coord)                
        
        n_block_items = []
        if block_items is not None:
            if n_id == self.n_id:
                node.block_items.insert(self.idx, self.asg)
                self.pn = prv_pn
                return node
            for x in block_items:
                n_block_items.append(self.visit(x))
        else:
            if n_id == self.n_id:
                node.block_items=[self.asg]
                self.pn = prv_pn
                return node
        n_compound_ast = c_ast.Compound(n_block_items, coord)
        self.pn = prv_pn
        return n_compound_ast

    def visit_If(self, node):
        #print('****************** Found IF Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        n_cond = self.visit(node.cond)
        n_id = node_id(node.coord)
        if n_id == self.n_id and self.idx == 0:
            node.cond = self.asg
            self.pn = prv_pn
            return node
        n_iftrue = self.visit(node.iftrue)
        n_iffalse = node.iffalse
        if node.iffalse:
            n_iffalse = self.visit(node.iffalse)
        #print('****************** New Cond Node with Parent Node '+self.pn+'****************')
        n_if = c_ast.If(n_cond, n_iftrue, n_iffalse, node.coord)
        self.pn = prv_pn
        return n_if

    def visit_For(self, node):
        #print('****************** Found For Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        n_id = node_id(node.coord)
        n_init = self.visit(node.init)        
        if n_id == self.n_id and self.idx == 0:
            node.init = self.asg
            self.pn = prv_pn
            return node                
        n_cond = self.visit(node.cond)
        if n_id == self.n_id and self.idx == 1:
            node.cond = self.asg
            self.pn = prv_pn
            return node        
        n_stmt = self.visit(node.stmt)
        n_next = node.next
        if n_next is not None:                
            n_next = self.visit(node.next)
        elif n_id == self.n_id and self.idx == 2:
            node.next = self.asg
            self.pn = prv_pn
            return node

        n_for = c_ast.For(n_init, n_cond, n_next, n_stmt, node.coord)
        self.pn = prv_pn
        return n_for

    def visit_While(self, node):
        #print('****************** Found While Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        n_id = node_id(node.coord)        
        n_cond = self.visit(node.cond)
        if n_id == self.n_id and self.idx == 0:
            node.cond = self.asg
            self.pn = prv_pn
            return node                
        n_stmt = self.visit(node.stmt)
        n_while = c_ast.While(n_cond, n_stmt, node.coord)
        self.pn = prv_pn
        return n_while

    def visit_DoWhile(self, node):
        #print('****************** Found DoWhile Node with Parent Node '+self.pn+'****************')
        prv_pn = self.pn
        self.pn = self.get_node_name(node)
        n_id = node_id(node.coord)
        n_cond = self.visit(node.cond)
        if n_id == self.n_id and self.idx == 0:
            node.cond = self.asg
            self.pn = prv_pn
            return node                
        n_stmt = self.visit(node.stmt)
        n_dowhile = c_ast.DoWhile(n_cond, n_stmt, node.coord)
        self.pn = prv_pn
        return n_dowhile

    
#-----------------------------------------------------------------
   
def load_dict(vm):
    fp=gzip.open(vm,'rb') # This assumes that primes.data is already packed with gzip
    var_map=pickle.load(fp)
    fp.close()
    return var_map

def softmax(x):
    """Compute softmax values for each sets of scores in x."""
    return np.exp(x) / np.sum(np.exp(x), axis=0)


def variables_distributions(d):
    # given a dictionary with a non-normalized distribution per variable, this function normalizes the distribution ['distribution'] considering the possible mappings ['mapped_to']
    dists=dict()
    for k in d.keys():
        dists[k] = dict()
        dst = d[k][0][0]
        # dst = softmax(dst)
        # dists[k]['distribution'] = [i/sum(dst) for i in dst]
        dists[k]['distribution'] = softmax(dst)
        dists[k]['mapped_to'] = d[k][1]
    return dists

def baseline_distributions(d):
    # given a dictionary with a non-normalized distribution per variable, this function returns a random distribution from a variable to any other variable
    dists=dict()
    for k in d.keys():
        dists[k] = dict()
        dst = d[k][0][0]
        dists[k]['mapped_to'] = d[k][1]        
        dists[k]['distribution'] = [1/len( dists[k]['mapped_to']) for _ in dst]

    return dists


def get_next_mapping():
    used_mappings.append(var_map)    
    while True:
        d = dict()
        for k in vars_dists.keys():
            d[k] = np.random.choice(vars_dists[k]['mapped_to'], 1, p=vars_dists[k]['distribution'])[0]
        if d not in used_mappings:
            return d
        
def save_fixed_program(ast, c_gen, sincludes, var_map):
    inv_map = dict((v, k) for k, v in var_map.items())
    v = VariableRenamerVisitor(inv_map)
    v.visit(ast)
    write_program(ast, c_gen, args.output_prog+".c", sincludes)
    if args.verbose:
        print("#Tries:", num_of_tries)
        print("#Mappings used:", len(used_mappings)+1)
        print("Last variable mapping:", var_map)
        print("\n\nFixed Program:")
        cu = CleanUpVisitor()
        ast_cleaned = cu.visit(ast)
        print(c_gen.visit(ast_cleaned))
        print("\nFIXED")
    else:
        print("FIXED")

    os.system("rm -rf "+args.output_prog)
    return True    
    
def enumerate_repairs(v, possible_fixes, ast, c_gen, sincludes, var_map):
    global num_of_tries
    original_ast = deepcopy(ast)
    fixed=False
    for _ in range(len(possible_fixes)):
        v.visit(ast)

        if program_checker(ast, c_gen, sincludes, args.ipa):
            fixed=True
            break

        ast = deepcopy(original_ast)
        v.next_repair()

        num_of_tries += 1

    if fixed:
        return save_fixed_program(ast, c_gen, sincludes, var_map)
    
    return False
    
def instrument_file(incorrect_program, correct_program, output_prog, var_map):
    output_file, sincludes, includes = make_output_dir(incorrect_program, output_prog)#, logfilename, loglibpath)
    try:
        ast = parse_file(output_file, use_cpp=True,
            cpp_path='gcc',
            cpp_args=['-E', '-Iutils/fake_libc_include'])
    except:
        print("Error while comoiling ", output_file)
        os.system("echo {p} >> repairing_programs_compilations_errs.txt".format(p=output_file))
        return 0

    try:
        correct_ast = parse_file(correct_program, use_cpp=True,
            cpp_path='gcc',
            cpp_args=['-E', '-Iutils/fake_libc_include'])
    except:
        print("Error while compiling ", correct_program)
        os.system("echo {p} >> repairing_programs_compilations_errs.txt".format(p=correct_program))
        return 0

    # print('******************** INPUT FILE: ********************')
    c_gen = c_generator.CGenerator()
    v = c_ast.NodeVisitor()
    v.visit(ast)
    if args.verbose:
        print("\n\nIncorrect submission's AST")
        cu = CleanUpVisitor()
        ast_aux = deepcopy(ast)
        ast_cleaned = cu.visit(ast_aux)
        print(c_gen.visit(ast_cleaned))
    # ast.show()
    
    untouched_ast = deepcopy(ast)
    while True:
        if args.verbose:            
            print("Using variable mapping:", var_map)
            print("\n\nIncorrect submission's AST")
            cu = CleanUpVisitor()
            ast_aux = deepcopy(ast)
            ast_cleaned = cu.visit(ast_aux)
            print(c_gen.visit(ast_cleaned))
        v = VariableRenamerVisitor(var_map)
        v.visit(ast)
        original_ast = deepcopy(ast)
        # ast.show()
        # return
        if program_checker(ast, c_gen, sincludes, args.ipa):
            return save_fixed_program(ast, c_gen, sincludes, var_map)
    
        if args.all or args.wco:
            cov = CompOpVisitor()
            cov.visit(ast)
            inc_prog_bin_ops = cov.binary_ops
            cov = CompOpVisitor()
            cov.visit(correct_ast)
            cor_prog_bin_ops = cov.binary_ops
            if args.verbose:
                print("Incorrect program binary operations:\n", inc_prog_bin_ops)
                print("\nCorrect program binary operations:\n", cor_prog_bin_ops)
                print()

            # Dealing with wrong comparison operator 
            wco = WrongCompOpFixerVisitor(inc_prog_bin_ops, cor_prog_bin_ops)
            if args.verbose:
                print("Possible fixes:", wco.possible_fixes)

            original_ast = deepcopy(ast)
            if enumerate_repairs(wco, wco.possible_fixes, ast, c_gen, sincludes, var_map):
                return True

        if args.all or args.vm:
            ast = deepcopy(original_ast)
            # Dealing with the bug of variable misused
            vi = VarInfoVisitor()
            vi.visit(ast)
            inc_prog_var_usage = vi.var_usage
            inc_prog_var_ids = vi.var_node_ids
            vi = VarInfoVisitor()
            vi.visit(correct_ast)
            cor_prog_var_usage = vi.var_usage
            cor_prog_var_ids = vi.var_node_ids    
            if args.verbose:
                print("\n\nIncorrect program variable usage:\n", inc_prog_var_usage)
                print("\nCorrect program variable usage:\n", cor_prog_var_usage)
                print()

            # ast = deepcopy(original_ast)
            vm = VarMisuseFixerVisitor(inc_prog_var_usage, cor_prog_var_usage, inc_prog_var_ids, cor_prog_var_ids)
            if args.verbose:
                print("Possible fix: replace {v1} with {v2}".format(v1=vm.var_2_del, v2=vm.var_2_insert))
                print("Possible places:", len(vm.var_2_del_ids))
                print(vm.var_2_del_ids)

            if enumerate_repairs(vm, vm.var_2_del_ids, ast, c_gen, sincludes, var_map):
                return True

        if args.all or args.ed:
            # Dealing with the bug of expression deletion
            ast = deepcopy(original_ast)
            ev = AssignmentVisitor()
            ev.visit(ast)
            ev2 = AssignmentVisitor()
            ev2.visit(correct_ast)
            if args.verbose:
                print("\n\nIncorrect program's assignments:\n", ev.assignments)
                print("\nCorrect program's assignments:\n", ev2.assignments)
                print()

            # ast = deepcopy(original_ast)
            aiv = AssignmentInsertionVisitor(ast, ev.assignments, ev2.assignments)
            if args.verbose:
                print("Possible fixes")
                # print(aiv.possible_fixes)

            if enumerate_repairs(aiv, aiv.possible_fixes, ast, c_gen, sincludes, var_map):
                return True

        ast = deepcopy(untouched_ast)
        var_map = get_next_mapping()
        
    if args.verbose:
        print("Program not fixed after {a} attempts!\nFAILED".format(a=num_of_tries))
    else:
        print("FAILED")

    return False
    
def parser():
    parser = argparse.ArgumentParser(prog='prog_fixer.py', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-ip', '--inc_prog', help='Program to be repaired.')
    parser.add_argument('-cp', '--cor_prog', help='Correct program to be used by the repair process.')
    parser.add_argument('-m', '--var_map', help='Variable mapping, where each incorrect program\'s variable has a corresponding variable identifier of the correct program.')
    parser.add_argument('-md', '--var_map_dist', help='Path for the each variable mapping distribution.')
    parser.add_argument('-b', '--baseline', action='store_true', default=False, help='Uses the baseline i.e. random mapping between the incorrect/correct programs\' variables.')        
    parser.add_argument('-wco', '--wco', action='store_true', default=False, help='Tries to fix bugs of wrong comparison operators.')
    parser.add_argument('-vm', '--vm', action='store_true', default=False, help='Tries to fix bugs of variable misuse.')
    parser.add_argument('-ed', '--ed', action='store_true', default=False, help='Tries to fix bugs of expression deletion (assignments).')    
    parser.add_argument('-a', '--all', action='store_true', default=False, help='Tries to fix all the mutilations above.')    
    parser.add_argument('-e', '--ipa', help='Name of the lab and exercise (IPA) so we can check the IO tests.')
    parser.add_argument('-o', '--output_prog', nargs='?', help='Output program (program fixed).')
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='Prints debugging information.')
    args = parser.parse_args(argv[1:])
    return args

if __name__ == '__main__':
    args = parser()
    var_map = load_dict(args.var_map)
    # var_map = {'cont': 'maior', 'i': 'i', 'maior': 'maior'}
    used_mappings = list()
    vars_dists = variables_distributions(load_dict(args.var_map_dist))

    if args.baseline:
        vars_dists = baseline_distributions(load_dict(args.var_map_dist))
        var_map=dict()
        var_map=get_next_mapping()
        used_mappings=list()
    # print(args)
    # for k in var_map.keys():
        # var_map[k] = var_map[k]+"_mod"

    
    if args.verbose:
        print("Program Fixer")
        print("Incorrect Program:", args.inc_prog)
        # print("Correct Program:", args.cor_prog)
        print("Using variable mapping:", var_map)

    fixed = False
    num_of_tries=0
    while not fixed:
        try:
            fixed = instrument_file(args.inc_prog, args.cor_prog, args.output_prog, var_map)
        except:
            print("ERROR")
            print(var_map)
            print("#Mappings:", len(used_mappings)+1)                    
            var_map = get_next_mapping()

    # instrument_file(args.inc_prog, args.cor_prog, args.output_prog, var_map)
