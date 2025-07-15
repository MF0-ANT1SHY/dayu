import typing

from decompile.ir.lexenv import LexEnv
from decompile.ir.nac import NAddressCode
from pandasm.insn import PandasmInsnArgument


class IRMethodContext:
    def __init__(self, method):
        self.method = method
        # lexical environments (lexenvs)
        self.lexenvs: typing.List[LexEnv] = []
        self.top_level_lexenv = None

    def parse_newlexenvwithname(self, lexenvwithname_arg):
        # newlexenvwithname 0x2, { 5 [ i32:2, string:"4newTarget", i32:0, string:"this", i32:1, ]}
        lexenvwithname_arg = lexenvwithname_arg.split('[')[1].split(']')[0].strip()  # i32:2, string:"4newTarget", i32:0, string:"this", i32:1,

        # first element is the total number of subsequent name-index pairs, skip this element
        lexenvwithname_arg = ','.join(lexenvwithname_arg.split(',')[1:])  # string:"4newTarget", i32:0, string:"this", i32:1,

        # `lexenvwithname_arg` is an array of alternating names and indices, keep a variable so we know we're dealing with a name or an index as we go
        name_or_index = 'name'
        is_inside_quotes, is_after_comma = False, False
        cur_str = ''
        names, indices = [], []
        for ch in lexenvwithname_arg:
            if ch == '"':
                is_inside_quotes = not is_inside_quotes
            elif ch == ',':
                if not is_inside_quotes:
                    if name_or_index == 'name':
                        name_or_index = 'index'
                        names.append(cur_str)
                    elif name_or_index == 'index':
                        key_or_value = 'name'
                        indices.append(cur_str)
                    cur_str = ''
                    is_after_comma = True
                else:
                    cur_str += ch
            elif ch == ' ':
                if is_after_comma:
                    is_after_comma = False
                else:
                    cur_str += ch
            else:
                cur_str += ch

        # strip the type tag: {"4newTarget":0, "this":1}
        names = [':'.join(k.split(':')[1:]) for k in names]
        indices = [':'.join(v.split(':')[1:]) for v in indices]

        return names

    def parse_defineclasswithbuffer(self, target_class, methods_arg):
        # { 7 [ string:"init", method:init, method_affiliate:0, string:"getInstance", method:getInstance, method_affiliate:0, i32:1, ]}

        methods = []
        methods_arg = methods_arg.split('[')[1].split(']')[0].strip()  # string:"init", method:init, method_affiliate:0, string:"getInstance", method:getInstance, method_affiliate:0, i32:1,

        for methods_arg_split in methods_arg.split(','):
            if methods_arg_split.strip().startswith('method:'):
                method_name = methods_arg_split.split(':')[1]
                methods.append(target_class.get_method_by_name(method_name))

        return methods

    def collect_lexenv(self, parent_lexenv):
        self.top_level_lexenv = parent_lexenv
        for block in self.method.blocks:
            for insn in block.insns:
                insn: NAddressCode
                if insn.op == 'newlexenv':
                    if self.lexenvs:
                        lexenv = LexEnv(self.method, parent_lexenv=self.lexenvs[-1])
                    else:
                        lexenv = LexEnv(self.method, parent_lexenv=parent_lexenv)
                    for i in range(int(insn.args[1].value, 16)):
                        lexenv.add_lexvar(PandasmInsnArgument('var', f'lexvar_{lexenv.lexenv_level}_{i}'))
                    self.lexenvs.append(lexenv)
                    self.top_level_lexenv = lexenv
                elif insn.op == 'newlexenvwithname':
                    if self.lexenvs:
                        lexenv = LexEnv(self.method, parent_lexenv=self.lexenvs[-1])
                    else:
                        lexenv = LexEnv(self.method, parent_lexenv=parent_lexenv)
                    lexenvwithname_arg = insn.args[1].value
                    for name in self.parse_newlexenvwithname(lexenvwithname_arg):
                        lexenv.add_lexvar(PandasmInsnArgument('var', name))
                    self.lexenvs.append(lexenv)
                    self.top_level_lexenv = lexenv
                elif insn.op in ['definemethod', 'definefunc']:
                    target_method_fullname = str(insn.args[2])
                    target_class_name = '.'.join(target_method_fullname.split(':')[0].split('.')[:-1])
                    target_method_name = target_method_fullname.split(':')[0].split('.')[-1]
                    target_class = self.method.parent_class.parent_module.get_class_by_name(target_class_name)
                    target_method = target_class.get_method_by_name(target_method_name)

                    if self.lexenvs:
                        target_method.ctx.collect_lexenv(self.lexenvs[-1])
                    else:
                        target_method.ctx.collect_lexenv(parent_lexenv)
                elif insn.op == 'defineclasswithbuffer':
                    target_class_fullname = str(insn.args[2])
                    target_class_name = '.'.join(target_class_fullname.split(':')[0].split('.')[:-1])
                    target_class = self.method.parent_class.parent_module.get_class_by_name(target_class_name)

                    method_string = str(insn.args[3])
                    methods = self.parse_defineclasswithbuffer(target_class, method_string)
                    for target_method in methods:
                        if self.lexenvs:
                            target_method.ctx.collect_lexenv(self.lexenvs[-1])
                        else:
                            target_method.ctx.collect_lexenv(parent_lexenv)

    def get_lexvar(self, lexenv_relative_level, lexvar_idx):
        # start from the top-level lexenv and go back `lexenv_relative_level` levels
        lexenv = self.top_level_lexenv
        for _ in range(lexenv_relative_level):
            lexenv = lexenv.parent_lexenv

        # return the `lexvar_idx`-th lexvar
        return lexenv.get_lexvar(lexvar_idx)
