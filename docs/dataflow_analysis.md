# Dataflow Analysis Module - Input and Output Analysis

## Overview

The dataflow analysis module in dayu consists of three main components that implement classic dataflow analysis algorithms for optimizing decompiled code:

1. **DefUseAnalysis** - Computes definition and use sets for variables
2. **ReachingDefinitions** - Determines which definitions may reach each program point  
3. **LiveVariableAnalysis** - Identifies which variables are live at each program point

These analyses are essential for optimization passes like copy propagation and dead code elimination.

## Core Data Structures

### Input Data Structures

#### IRMethod
- **Purpose**: Container for the method being analyzed
- **Key Fields**:
  - `blocks: List[IRBlock]` - List of basic blocks in the method
  - `name: str` - Method name
  - `parent_class` - Reference to containing class

#### IRBlock  
- **Purpose**: Represents a basic block in the control flow graph
- **Key Fields**:
  - `insns: List[NAddressCode]` - Instructions in the block
  - `predecessors: List[IRBlock]` - Incoming control flow edges
  - `successors: List[IRBlock]` - Outgoing control flow edges
  - `defs: set` - Variables defined in this block (populated by DefUseAnalysis)
  - `uses: set` - Variables used in this block (populated by DefUseAnalysis)

#### NAddressCode (NAC)
- **Purpose**: Intermediate representation instruction
- **Key Types**:
  - `ASSIGN` - Variable assignments (x = y, x = y + z)
  - `CALL` - Function/method calls (x = f(y, z))
  - `UNCOND_JUMP` - Unconditional jumps
  - `COND_JUMP` - Conditional jumps
  - `RETURN` - Method returns
  - `UNCOND_THROW`/`COND_THROW` - Exception throwing
- **Key Fields**:
  - `type: NAddressCodeType` - Instruction type
  - `args: List` - Operands (max 3 for most instructions)
  - `op: str` - Operation (e.g., '+', '==', 'call')

### Output Data Structures

#### DefUseAnalysis Output
- **Block-level**: Populates `defs` and `uses` sets on each `IRBlock`
- **defs**: Set of variables defined in the block
- **uses**: Set of variables used before being defined in the block

#### ReachingDefinitions Output
- **Return Value**: Tuple `(in_block, out_block)`
- **in_block**: Dictionary mapping each block to set of definitions reaching its entry
- **out_block**: Dictionary mapping each block to set of definitions reaching its exit

#### LiveVariableAnalysis Output  
- **Return Value**: Tuple `(in_block, out_block)`
- **in_block**: Dictionary mapping each block to set of variables live at block entry
- **out_block**: Dictionary mapping each block to set of variables live at block exit

## Analysis Flow

### 1. DefUseAnalysis

**Input**: `IRMethod` with populated control flow graph

**Process**:
```python
def run_on_method(self, method: IRMethod):
    for block in method.blocks:
        self.analyze_block(block)
```

For each instruction type:
- **ASSIGN**: Defines first operand, uses remaining operands
- **CALL**: Defines first operand, uses all remaining operands  
- **JUMPS/THROWS**: Uses operands for conditions/values
- **RETURN**: Uses return value operand

**Output**: Populates `defs` and `uses` sets on each block

### 2. ReachingDefinitions

**Input**: 
- `IRMethod` with control flow graph
- Automatically collects all assignment/call instructions as "copies"

**Process**:
1. Compute GEN/KILL sets for each block:
   - **GEN**: Definitions generated in this block
   - **KILL**: Definitions killed by redefinitions in this block
2. Iterative dataflow analysis using worklist algorithm
3. **Transfer Function**: `OUT[B] = GEN[B] ∪ (IN[B] - KILL[B])`
4. **Meet Operation**: `IN[B] = ∪ OUT[P]` for all predecessors P

**Output**: 
- `in_block`: Definitions reaching each block's entry
- `out_block`: Definitions reaching each block's exit

### 3. LiveVariableAnalysis

**Input**:
- `IRMethod` with populated `defs` and `uses` sets (from DefUseAnalysis)

**Process**:
1. Backward dataflow analysis (processes blocks in reverse)
2. **Transfer Function**: `IN[B] = USE[B] ∪ (OUT[B] - DEF[B])`
3. **Meet Operation**: `OUT[B] = ∪ IN[S]` for all successors S
4. Iterative analysis until fixed point

**Output**:
- `in_block`: Variables live at each block's entry
- `out_block`: Variables live at each block's exit

## Integration in Decompiler Pipeline

The dataflow analyses are integrated into the decompiler at multiple points:

### LLIR Level (Low-Level IR)
```python
# In decompile_method_to_llir()
in_r, out_r = ReachingDefinitions().run_on_method(method)
DefUseAnalysis().run_on_method(method)  
in_l, out_l = LiveVariableAnalysis().run_on_method(method)
```

### MLIR/HLIR Levels (Medium/High-Level IR)
```python
# For optimization passes
DefUseAnalysis().run_on_method(method)
in_l, out_l = LiveVariableAnalysis().run_on_method(method)

# Copy propagation uses reaching definitions
if self.config.copy_propagation_enabled_levels:
    CopyPropagation(in_r).run_on_method(method)

# Dead code elimination uses live variables  
if self.config.dead_code_elimination_enabled_levels:
    DeadCodeElimination(out_l).run_on_method(method)
```

## Usage by Optimization Passes

### Copy Propagation
- **Input**: Results from `ReachingDefinitions` 
- **Purpose**: Replace variable uses with their defining expressions when safe
- **Example**: `x = y; z = x` → `x = y; z = y`

### Dead Code Elimination  
- **Input**: Results from `LiveVariableAnalysis`
- **Purpose**: Remove assignments to variables that are never used
- **Example**: Remove `x = y` if `x` is never read afterwards

## Variable Representation

Variables in the analysis are represented as:
- **PandasmInsnArgument**: Register arguments (`acc`, `v0`, `v1`, etc.)
- **ExprArg**: Complex expressions (array accesses, property accesses)
- **ref_obj**: Reference objects for array/property accesses

Special handling for:
- **Nested expressions**: Recursively extract used variables from `ExprArg`
- **Array/property access**: Both the base object and index/property are considered used
- **Unknown instructions**: Conservatively assume all operands are both defined and used

## Error Handling and Edge Cases

1. **Empty blocks**: Handled gracefully with empty sets
2. **No successors/predecessors**: Dummy entry/exit blocks added temporarily
3. **Unknown instruction types**: Conservative analysis assumes worst-case scenario
4. **Circular references**: Fixed-point iteration ensures termination

## Performance Characteristics

- **Time Complexity**: O(|V| × |E|) where V is variables and E is CFG edges
- **Space Complexity**: O(|V| × |B|) where B is basic blocks
- **Convergence**: Typically converges in 2-3 iterations for most methods