from dayu.ark.abcstring import String
from dayu.ark.abcstruct import AbcStructure
from dayu.common.binary_reader import BinaryReader


class ForeignClass(AbcStructure):
    def __init__(self, bin_reader: BinaryReader, offset=None):
        super().__init__(bin_reader, offset)
        self.name = String(bin_reader).data
