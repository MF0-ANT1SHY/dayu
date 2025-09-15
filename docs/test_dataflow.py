#!/usr/bin/env python3
"""
Test script to verify dataflow analysis module functionality

This script tests the three main dataflow analysis passes and validates
their inputs and outputs match expected behavior.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decompile.ir.basicblock import IRBlock
from decompile.ir.method import IRMethod
from decompile.ir.nac import NAddressCode, NAddressCodeType
from decompile.passes.defuse import DefUseAnalysis
from decompile.passes.reaching_def import ReachingDefinitions
from decompile.passes.live_variable import LiveVariableAnalysis
from pandasm.insn import PandasmInsnArgument


def test_defuse_analysis():
    """Test DefUse analysis on a simple method"""
    print("Testing DefUse Analysis...")
    
    method = IRMethod("test_method")
    block = IRBlock(method)
    
    # Create some variables
    v0 = PandasmInsnArgument('reg', 'v0')
    v1 = PandasmInsnArgument('reg', 'v1')
    const5 = PandasmInsnArgument('imm', '5')
    
    # Add instructions: v0 = 5; v1 = v0
    insn1 = NAddressCode('=', [v0, const5], NAddressCodeType.ASSIGN)
    insn2 = NAddressCode('=', [v1, v0], NAddressCodeType.ASSIGN)
    block.insert_insn(insn1)
    block.insert_insn(insn2)
    
    # Run analysis
    defuse = DefUseAnalysis()
    defuse.run_on_method(method)
    
    # Verify results - check that we got some defs and uses
    assert len(block.defs) > 0, "Should have some definitions"
    assert len(block.uses) > 0, "Should have some uses"
    
    # Check that v0 and v1 are defined
    def_vars = [str(d) for d in block.defs]
    assert 'v0' in def_vars, "v0 should be defined"
    assert 'v1' in def_vars, "v1 should be defined"
    
    print("✓ DefUse Analysis test passed")
    return True


def test_reaching_definitions():
    """Test reaching definitions on a method with multiple blocks"""
    print("Testing Reaching Definitions...")
    
    method = IRMethod("test_method")
    block1 = IRBlock(method)
    block2 = IRBlock(method)
    
    # Block 1: v0 = 5
    v0 = PandasmInsnArgument('reg', 'v0')
    const5 = PandasmInsnArgument('imm', '5')
    insn1 = NAddressCode('=', [v0, const5], NAddressCodeType.ASSIGN)
    block1.insert_insn(insn1)
    
    # Block 2: v1 = v0  
    v1 = PandasmInsnArgument('reg', 'v1')
    insn2 = NAddressCode('=', [v1, v0], NAddressCodeType.ASSIGN)
    block2.insert_insn(insn2)
    
    # Set up control flow
    block1.add_successor(block2)
    
    # Run analysis
    reaching_def = ReachingDefinitions()
    in_r, out_r = reaching_def.run_on_method(method)
    
    # Verify results
    # Block 1 should have no incoming definitions, but generate v0=5
    assert len(in_r[block1]) == 0, f"Block1 should have no incoming definitions"
    assert len(out_r[block1]) == 1, f"Block1 should have one outgoing definition"
    
    # Block 2 should receive v0=5 definition and generate v1=v0
    assert insn1 in in_r[block2], f"Block2 should receive v0=5 definition"
    assert insn2 in out_r[block2], f"Block2 should generate v1=v0 definition"
    
    print("✓ Reaching Definitions test passed")
    return True


def test_live_variable_analysis():
    """Test live variable analysis"""
    print("Testing Live Variable Analysis...")
    
    method = IRMethod("test_method")
    block1 = IRBlock(method)
    block2 = IRBlock(method)
    
    # First run DefUse to populate defs/uses
    v0 = PandasmInsnArgument('reg', 'v0')
    v1 = PandasmInsnArgument('reg', 'v1')
    const5 = PandasmInsnArgument('imm', '5')
    
    # Block 1: v0 = 5
    insn1 = NAddressCode('=', [v0, const5], NAddressCodeType.ASSIGN)
    block1.insert_insn(insn1)
    
    # Block 2: return v0
    insn2 = NAddressCode('return', [v0], NAddressCodeType.RETURN)
    block2.insert_insn(insn2)
    
    # Set up control flow
    block1.add_successor(block2)
    
    # Run DefUse first
    defuse = DefUseAnalysis()
    defuse.run_on_method(method)
    
    # Run live variable analysis
    live_var = LiveVariableAnalysis()
    in_l, out_l = live_var.run_on_method(method)
    
    # Verify results
    # v0 should be live at the end of block1 (needed by block2)
    assert v0 in out_l[block1], f"v0 should be live at exit of block1"
    
    # Nothing should be live at the end of block2 (return statement)
    assert len(out_l[block2]) == 0, f"Nothing should be live at exit of block2"
    
    print("✓ Live Variable Analysis test passed")
    return True


def test_integration():
    """Test that all analyses work together correctly"""
    print("Testing Integration...")
    
    method = IRMethod("integration_test")
    block1 = IRBlock(method)
    block2 = IRBlock(method) 
    block3 = IRBlock(method)
    
    # Create a diamond CFG:
    # Block1 -> Block2, Block3
    # Block2, Block3 -> (implicit end)
    
    v0 = PandasmInsnArgument('reg', 'v0')
    v1 = PandasmInsnArgument('reg', 'v1')
    v2 = PandasmInsnArgument('reg', 'v2')
    const1 = PandasmInsnArgument('imm', '1')
    const2 = PandasmInsnArgument('imm', '2')
    const3 = PandasmInsnArgument('imm', '3')
    
    # Block 1: v0 = 1; conditional jump
    insn1 = NAddressCode('=', [v0, const1], NAddressCodeType.ASSIGN)
    block1.insert_insn(insn1)
    
    # Block 2: v1 = 2
    insn2 = NAddressCode('=', [v1, const2], NAddressCodeType.ASSIGN)
    block2.insert_insn(insn2)
    
    # Block 3: v2 = 3  
    insn3 = NAddressCode('=', [v2, const3], NAddressCodeType.ASSIGN)
    block3.insert_insn(insn3)
    
    # Set up CFG
    block1.add_successor(block2)
    block1.add_successor(block3)
    
    # Run all analyses
    defuse = DefUseAnalysis()
    defuse.run_on_method(method)
    
    reaching_def = ReachingDefinitions()
    in_r, out_r = reaching_def.run_on_method(method)
    
    live_var = LiveVariableAnalysis()
    in_l, out_l = live_var.run_on_method(method)
    
    # Basic sanity checks
    assert len(method.blocks) == 3, "Should have 3 blocks"
    assert v0 in block1.defs, "Block1 should define v0"
    assert v1 in block2.defs, "Block2 should define v1"
    assert v2 in block3.defs, "Block3 should define v2"
    
    print("✓ Integration test passed")
    return True


def run_all_tests():
    """Run all dataflow analysis tests"""
    print("=== DATAFLOW ANALYSIS TESTS ===\n")
    
    tests = [
        test_defuse_analysis,
        test_reaching_definitions, 
        test_live_variable_analysis,
        test_integration
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
    
    print(f"\n=== RESULTS ===")
    print(f"Passed: {passed}/{len(tests)} tests")
    
    if passed == len(tests):
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)