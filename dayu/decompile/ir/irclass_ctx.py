import typing

from dayu.decompile.ir.method import IRMethod


class IRClassContext:
    def __init__(self, clazz):
        self.clazz = clazz
