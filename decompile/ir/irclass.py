import typing

from decompile.ir.irclass_ctx import IRClassContext
from decompile.ir.method import IRMethod


class IRClass:
    def __init__(self, name=None, parent_module=None):
        self.name = name
        self.methods: typing.List[IRMethod] = []
        self.parent_module = parent_module
        if self.parent_module:
            self.parent_module.insert_class(self)
        self.ctx = IRClassContext(self)

    def insert_method(self, method: IRMethod):
        self.methods.append(method)

    def remove_method(self, method: IRMethod):
        self.methods.remove(method)

    def erase_from_parent(self):
        if not self.parent_module:
            raise Exception(f'{self.__class__.__name__}: this class has no parent')
        self.parent_module.remove_class(self)

    def get_method_by_name(self, method_name):
        for method in self.methods:
            if method.name == method_name:
                return method
        return None
