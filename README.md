# drawlego

Render LEGO block configurations from YAML files into PNG images.

## Requirements

- Python 3.10+
- A working Python environment (`venv`, Poetry, etc.)

Project dependencies:

- `pyvista`
- `pyyaml`

## Installation

### Option 1: Poetry

```bash
poetry install
```

### Option 2: pip + virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install pyvista pyyaml
```

## Usage

Basic command:

```bash
python drawlego.py <input.yaml>
```

The script creates a PNG next to the input file by default.

Example:

```bash
python drawlego.py example_configs/tower_3.yaml
```

This writes:

- `example_configs/tower_3.png`

Set a custom output path:

```bash
python drawlego.py example_configs/grid_9.yaml --output grid.png
```

## Running with Poetry

If you installed with Poetry, run:

```bash
poetry run python drawlego.py example_configs/bridge_8.yaml
```

## Input Format

Input YAML files are expected to contain a top-level `blocks` list (see files in `example_configs/`).
