from decompile.dec_pass import Pass
from decompile.ir.irclass import IRClass


class ClassPass(Pass):
    def run_on_class(self, clazz: IRClass):
        raise NotImplementedError(f'{self.__class__.__name__}: Implement your own pass by extending this class')
