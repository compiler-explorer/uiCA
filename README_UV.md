# uiCA with uv

Quick start for Compiler Explorer's `ce` branch.

## Setup

```bash
git clone https://github.com/compiler-explorer/uiCA.git
cd uiCA
git checkout ce
git submodule update --init --recursive
uv run --with setuptools python build.py
```

## Usage

```bash
# Analyze a binary file
uv run uica mybinary.o -arch SKL

# See all options
uv run uica --help

# Run facile (analytical prediction)
uv run uica-facile -hex "4801D8" -mode loop -arch SKL
```

## How It Works

- **XED disassembler**: Built from XED-to-XML submodule → creates platform-specific `xed*.so` (~7MB)
- **Instruction data**: Downloaded from uops.info as `instructions.xml` (~110MB), converted to Python files in `instrData/` (~12MB)
- **Dependencies**: Auto-managed by `uv` (just plotly and its deps)

The `build.py` script:
1. Downloads and converts instruction performance data from uops.info (if not present)
2. Builds the XED disassembler Python extension
3. Copies `xed.so` to your virtualenv's site-packages
4. Touches `pyproject.toml` so `uv` auto-rebuilds the package mapping on next use

**Note**: The first `uv run uica` after `build.py` will automatically reinstall the package to pick up `instrData`. This is normal and only happens once.

## Development

The project uses `pyproject.toml` for packaging. All Python dependencies are managed by `uv`.

To rebuild after XED source changes:
```bash
rm -rf XED-to-XML/obj XED-to-XML/build xed*.so
uv run --with setuptools python build.py
```

To regenerate instruction data (if uops.info updates):
```bash
rm -rf instrData/
uv run --with setuptools python build.py
```
