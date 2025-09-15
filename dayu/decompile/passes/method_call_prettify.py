from dayu.decompile.ir.basicblock import IRBlock
from dayu.decompile.ir.method import IRMethod
from dayu.decompile.ir.nac import NAddressCodeType
from dayu.decompile.method_pass import MethodPass


class MethodCallPrettify(MethodPass):
    """
    turn "this.v0 = func(FunctionObject, NewTarget, this, ...)" into "this.v0 = func(this, ...)"
    """
    def run_on_method(self, method: IRMethod):
        for block in method.blocks:
            self.run_on_block(block)

    def run_on_block(self, block: IRBlock):
        for insn in block.insns:
            if insn.type == NAddressCodeType.CALL:
                if len(insn.args) < 4:  # v0 = func(FunctionObject, NewTarget, ...), at least four arguments
                    continue
                if insn.args[2].type == 'FunctionObject' and insn.args[3].type == 'NewTarget':
                    insn.args[2:] = insn.args[4:]
