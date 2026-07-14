# Install

Paxman v2.0.0 is not yet published to a package index. The only install path is from source.

## Requirements

- Python 3.12 or newer.
- [`uv`](https://docs.astral.sh/uv/) for dependency management. Install it with `curl -LsSf https://astral.sh/uv/install.sh | sh` or your platform's package manager.

## Steps

```bash
git clone https://github.com/nexusnv/paxman.git
cd paxman
uv sync
```

`uv sync` reads the project configuration and creates a virtual environment with Paxman and its (one) runtime dependency (`attrs`) installed in editable mode.

## Verify the install

```bash
uv run python -c "import paxman; print(paxman.__version__)"
```

Expected output:

```text
0.0.0.dev0
```

If the import works, the install succeeded. Proceed to [Quickstart](quickstart.md) for the 5-minute walkthrough.
