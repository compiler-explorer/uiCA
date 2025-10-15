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
uv run ./uiCA.py mybinary.o -arch SKL

# See all options
uv run ./uiCA.py --help

# Run facile (analytical prediction)
uv run ./facile.py -hex "4801D8" -mode loop -arch SKL
```

## How It Works

- **XED disassembler**: Built once from XED-to-XML submodule (creates `xed*.so`)
- **Instruction data**: Pre-generated from uops.info, committed in `instrData/`
- **Dependencies**: Auto-managed by `uv` (just plotly)

## Development

The project uses `pyproject.toml` for packaging. All Python dependencies are managed by `uv`.

To regenerate instruction data (if uops.info XML changes):
```bash
wget https://www.uops.info/instructions.xml
uv run ./convertXML.py instructions.xml
rm instructions.xml
```
