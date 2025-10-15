# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

uiCA (uops.info Code Analyzer) is a CPU pipeline simulator that predicts throughput of x86-64 basic blocks on Intel microarchitectures. It models the instruction decode pipeline, execution ports, dependencies, and various microarchitectural features to provide cycle-accurate performance predictions.

**This is Compiler Explorer's fork** (on the `ce` branch). The primary goal is to make uiCA runnable and installable with `uv` in a virtual environment, eliminating the need for setup.sh and manual submodule building.

## Current State & Goals

**Current setup** (to be replaced):
- `setup.sh` builds XED-to-XML submodule and downloads/converts instruction data
- Requires manual git submodule management
- Not pip/uv installable

**Target setup** (using uv):
- Package should be installable via `uv pip install` or `uv run`
- Dependencies managed in pyproject.toml
- XED library should be pre-built or fetched as a dependency
- Instruction data (from uops.info) should be included or downloaded during install

## Dependencies

- XED disassembler (currently built from XED-to-XML submodule)
- instructions.xml from uops.info (converted to Python data in instrData/)
- Python packages: plotly, pydot (Windows), graphviz (optional for dependency graphs)

## Usage

Basic usage:
```bash
./uiCA.py <binary_file> -arch <ARCH>
```

Common architectures: SKL (Skylake), SKX (Skylake-X), ICL (Ice Lake), TGL (Tiger Lake)
Use `-arch all` to compare all supported microarchitectures.

## Architecture

### Core Components

**uiCA.py** (2096 lines) - Main simulator implementing the CPU pipeline model:
- `Uop`, `FusedUop`, `LaminatedUop` - Uop hierarchy representing different fusion domains
- `FrontEnd` - Models instruction fetch, decode (MITE), DSB (uop cache), microcode sequencer
- `Decoder`, `PreDecoder` - Models decode pipeline with complex/simple decoder constraints
- `Renamer` - Register renaming and move elimination
- `Scheduler`, `ReorderBuffer` - Out-of-order execution modeling
- `runSimulation()` - Main simulation loop that cycles through fetch/decode/execute/retire stages

**instructions.py** - `Instr` class representing instruction metadata (ports, latencies, operands)

**microArchConfigs.py** - `MicroArchConfig` classes defining CPU parameters (issue width, decoders, queue sizes, etc.) for each supported microarchitecture

**facile.py** - Analytical throughput prediction using various bottleneck formulas (port usage, decode limits, latency) without full simulation

**convertXML.py** - Parses uops.info XML data into Python data structures saved to instrData/

**x64_lib.py** - x86-64 register utilities and constants

### Data Flow

1. XED disassembles binary → instruction bytes + operands
2. Instructions matched against instrData/{ARCH}_data.py (generated from XML)
3. Simulator creates Uop objects with dependencies and port constraints
4. Pipeline simulation tracks each uop through fetch/decode/execute/retire
5. Critical path analysis identifies bottlenecks (throughput, latency, decode, front-end)

### Key Abstractions

- **Unfused domain uops** (`Uop`) - Individual operations as seen by execution units
- **Fused domain uops** (`FusedUop`) - After micro-fusion (e.g., load+compute)
- **Laminated domain uops** (`LaminatedUop`) - After macro-fusion (e.g., cmp+jcc)
- **InstrInstance** - A specific dynamic instance of an instruction in simulation
- **RenamedOperand** - Operand after register renaming with producer/consumer tracking

### Pipeline Stages Modeled

1. **PreDecode** - 16-byte block alignment, LCP (length-changing prefix) stalls
2. **Decode/MITE** - Complex vs simple decoder constraints, macro-fusion
3. **DSB** - Decoded uop cache, 32-byte blocks
4. **MS** - Microcode sequencer for complex instructions
5. **IDQ** - Instruction decode queue feeding the backend
6. **Issue** - Fused-domain uop issue (typically 4-wide)
7. **Dispatch** - Unfused uops to reservation stations
8. **Execute** - Port assignment and execution
9. **Retire** - In-order retirement from reorder buffer

## Output Options

- `-trace <file.html>` - Cycle-by-cycle execution trace
- `-graph <file.html>` - Performance event timeline graph
- `-depGraph <file.svg>` - Dependency graph visualization
- `-alignmentOffset <n|all>` - Test alignment sensitivity
- `-TPonly` - Throughput prediction only (no detailed analysis)

## Testing

No formal test suite. Test by running on known basic blocks and comparing with hardware measurements from uops.info.

## Architecture-Specific Data

After setup, instrData/ contains generated modules like SKL_data.py with per-instruction performance data (ports, latencies, uop counts) measured from real CPUs.
