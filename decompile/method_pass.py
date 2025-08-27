from decompile.dec_pass import Pass
from decompile.ir.method import IRMethod


class MethodPass(Pass):
    def run_on_method(self, method: IRMethod):
        raise NotImplementedError(f'{self.__class__.__name__}: Implement your own pass by extending this class')
