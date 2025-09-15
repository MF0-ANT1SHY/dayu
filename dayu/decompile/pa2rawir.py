import copy

from dayu.ark.abcfile.abcfile import AbcFile
from dayu.ark.abcreader import AbcReader
from dayu.decompile.ir.basicblock import IRBlock
from dayu.decompile.ir.builder import IRBuilder
from dayu.decompile.ir.irclass import IRClass
from dayu.decompile.ir.method import IRMethod
from dayu.decompile.ir.module import IRModule
from dayu.decompile.ir.nac import NAddressCode, NAddressCodeType
from dayu.pandasm.file import PandasmFile
from dayu.pandasm.method import PandasmMethod
from dayu.pandasm.pa_class import PandasmClass


class Pandasm2RawIR:
    @classmethod
    def transform_module(cls, pa_file: PandasmFile, abc_file: AbcFile = None):
        ir_module = IRModule()
        for pa_class in pa_file.iter_classes():
            cls.transform_class(pa_class, ir_module, abc_file)
        # module requests information is read directly from abc files
        # we need this information when decompiling the "ldexternalmodulevar" instruction
        if abc_file:
            ir_module.ctx.read_module_requests_from_abc(abc_file)
        return ir_module

    @classmethod
    def transform_class(cls, pa_class: PandasmClass, parent_ir_module: IRModule = None, abc_file: AbcFile = None):
        ir_class = IRClass(pa_class.name, parent_ir_module)
        for pa_method in pa_class.methods:
            cls.transform_method(pa_method, ir_class)

        return ir_class

    @classmethod
    def transform_method(cls, pa_method: PandasmMethod, parent_ir_class: IRClass = None):
        ir_method = IRMethod(pa_method.name, parent_ir_class)

        # in the original PandasmFile, there's no concept of a basic block;
        # in the raw IR, we put all NACs (IR instructions) into one big IRBlock
        # these NACs will be split into proper basic blocks in the BuildCFG pass
        ir_block = IRBlock(ir_method)

        # create an IRBuilder to help us put the NACs
        builder = IRBuilder(ir_method.parent_class.parent_module)
        builder.set_insert_point(ir_block)
        for insn in pa_method.insns:
            nac = NAddressCode(insn.mnemonic, insn.arguments if insn.arguments else insn.operands, NAddressCodeType.UNKNOWN, label_name=insn.label)
            builder.insert(nac)

        return ir_method

