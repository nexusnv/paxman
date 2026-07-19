# Paxman Playground

A ready-to-run JupyterLab environment for **learning Paxman** — the deterministic
canonicalization engine for Python. Spin it up with one command and explore
canonicalization through runnable notebooks, no install of your own required.

## What's inside

| Path | Purpose |
|------|---------|
| `docker-compose.yml` | Boots a JupyterLab with Paxman installed editable from source. |
| `Dockerfile` | `jupyter/scipy-notebook` base + `pip install -e .` of Paxman. |
| `notebooks/` | The learning notebooks (see below). |
| `data/` | Scratch space for your own sample inputs. |
| `NOTEBOOK_INPUTS.md` | Reference: verified input variants + canonical outputs per capability. |

### Notebooks

Each notebook follows one reference template (`00_email.ipynb`): a title header,
a single imports cell, then concept → runnable example cells showing different
input spellings and their canonical output, an error/edge-case cell, and a
pointer to the Engine/DSL notebooks.

| Notebook | Covers |
|----------|--------|
| `00_email.ipynb` | Email canonicalization (lowercasing, Gmail aliasing, refusal to guess). |
| `01_boolean.ipynb` | Boolean → `"true"` / `"false"` (words, digits, policy-gated tokens). |
| `02_country.ipynb` | Country → ISO 3166-1 alpha-2 (name, alpha-2/3, numeric, synonym). |
| `03_date.ipynb` | Date/datetime → `YYYY-MM-DD` / `...T...Z` (locale, ambiguity surfaced). |
| `04_geolocation.ipynb` | Coordinates → `lat,lon` (hemisphere sign, AMBIGUOUS vs guessed). |
| `05_ip.ipynb` | IP → RFC 4291 / RFC 5952 (IPv4 zeros, IPv6 compression, zone id). |
| `06_money.ipynb` | Money → `ISO4217:amount` (currency required, symbol/code match). |
| `07_phone.ipynb` | Phone → E.164 (country declared, never inferred). |
| `08_url.ipynb` | URL → RFC 3986 normalized (scheme/host lowercased, UNSUPPORTED vs INVALID). |
| `09_uuid.ipynb` | UUID → RFC 4122 (strict-only, no normalization of alternate shapes). |
| `10_engine.ipynb` | `Engine.default()`, `with_authorities`, `authority_override`, `replay`. |
| `11_dsl.ipynb` | Building contracts from a dict with `parse_contract`. |

> All twelve notebooks follow one reference template (`00_email.ipynb`) and are
> verified by the `notebook-smoke` CI job, which executes each one top-to-bottom.
> Per-capability input variants live in `NOTEBOOK_INPUTS.md`.

## Run with Docker (recommended)

Prerequisites: [Docker](https://docs.docker.com/get-docker/) with Compose v2.

```bash
cd playground
docker compose up
```

- First run builds the image (pulls `jupyter/scipy-notebook`, installs Paxman
  editable) — this takes a minute or two.
- The lab starts on **http://127.0.0.1:8888** (localhost only, not reachable
  from the network) and is protected by a **random token** printed to the
  container logs. Get the URL with:

  ```bash
  docker compose logs 2>&1 | grep -E "token=|Open:"
  ```

  Open that URL in your browser. **Never** run the playground on a shared or
  networked host in open mode (below).
- Notebooks are bind-mounted from `playground/notebooks/` on your host, so any
  edit you make in the browser is saved back to the repo. The `data/` scratch
  directory is mounted read-only inside the lab, so a notebook cannot write
  back into your repo tree.
- Shut it down with `Ctrl-C`, or `docker compose down` from another terminal.

### Open mode (tokenless, opt-in — NOT for shared hosts)

The default is localhost + token for safety. To run the original tokenless
lab bound to all interfaces (e.g. for a throwaway local-only demo on an
isolated machine), opt in explicitly:

```bash
PAXMAN_PLAYGROUND_OPEN=1 docker compose up
```

This disables the token and binds to `0.0.0.0`. **Only do this on a host you
trust is unreachable from any untrusted network** — an open Jupyter server is
remote-code-execution exposure.

To rebuild after changing the Dockerfile or `pyproject.toml`:

```bash
docker compose up --build
```

## Run locally without Docker

If you already have the project checked out with `uv`:

```bash
uv run jupyter lab playground/notebooks
```

This uses your local virtual environment instead of the container. The notebooks
are identical; only the runtime differs.

## Where to go next

- Main project README and `AGENTS.md` for deeper context.
- `NOTEBOOK_INPUTS.md` — the factual backbone of every notebook (verified against
  the working tree).
- `ARCHITECTURE.md` — the three invariants (identity, determinism, replay) and
  the three-layer authority model behind `10_engine.ipynb`.

## Notes

- Paxman canonicalizes known information; it **refuses to guess**. Malformed or
  ambiguous input returns `INVALID` / `AMBIGUOUS` rather than a silently "fixed"
  value — that behavior is the whole point, and the notebooks demonstrate it.
- The container installs Paxman **editable** from the repo it was built from, so
  the playground always reflects the source you built it against.
