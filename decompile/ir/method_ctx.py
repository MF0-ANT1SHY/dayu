import typing

from decompile.ir.lexenv import LexEnv
from decompile.ir.nac import NAddressCode
from pandasm.insn import PandasmInsnArgument


class IRMethodContext:
    def __init__(self, method):
        self.method = method
