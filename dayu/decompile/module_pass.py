from dayu.decompile.dec_pass import Pass
from dayu.decompile.ir.module import IRModule


class ModulePass(Pass):
    def run_on_module(self, module: IRModule):
        raise NotImplementedError(f'{self.__class__.__name__}: Implement your own pass by extending this class')
