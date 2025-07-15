import typing

from decompile.ir.method import IRMethod


class IRClassContext:
    def __init__(self, clazz):
        self.clazz = clazz

    def collect_lexenvs(self):
        main_method: typing.Optional[IRMethod] = self.clazz.get_method_by_name('func_main_0')
        if not main_method:
            print(f'Warning: main method not found for class {self.clazz.name}')
            return

        main_method.ctx.collect_lexenv(parent_lexenv=None)
