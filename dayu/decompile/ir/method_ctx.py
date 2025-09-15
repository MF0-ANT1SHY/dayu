import typing

from dayu.decompile.ir.lexenv import LexEnv
from dayu.decompile.ir.nac import NAddressCode
from dayu.pandasm.insn import PandasmInsnArgument


class IRMethodContext:
    def __init__(self, method):
        self.method = method
