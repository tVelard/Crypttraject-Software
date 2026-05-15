# CryptTraject

Privacy-preserving record clustering via BFV homomorphic encryption + MinHash + LSH.

## Architecture

Three independent Python packages, with a strict separation of responsibilities:

```
shared/   crypttraject_shared     # BFV params + wire format. Imported by both sides.
client/   crypttraject_client     # Local-only: parsing, MinHash, key gen, encrypt, decrypt.
server/   crypttraject_server     # Public-only: receives ciphertexts, runs homomorphic ops.
```

Security invariant: the **secret key is generated and persisted exclusively on the client**. The server only ever receives `context.pkl` + `public_key.pkl` + encrypted signatures.

```
+----------------------+         SessionDescriptor (public key, ctx)         +-----------------------+
|  Client (desktop)    |  ------------------------------------------------>  |  Server (FastAPI)     |
|                      |         SignaturePayload (ciphertexts)              |                       |
|  parse data source   |  ------------------------------------------------>  |  homomorphic Jaccard  |
|  MinHash + BFV.enc   |                                                     |  (diff_sq per pair)   |
|  decrypt results     |  <------------------------------------------------  |                       |
|  cluster locally     |         SimilarityResult (ciphertexts)              |                       |
+----------------------+                                                     +-----------------------+
```

## Generic data ingestion

The client is database-agnostic. Adding support for a new format only requires writing a `DataSourceAdapter` subclass that yields `Record`s, plus picking a `FeatureExtractor` to turn each record into MinHash tokens.

Bundled adapters: `CSVAdapter`, `JSONAdapter` (JSON arrays + JSONL), `PLTGeolifeAdapter`.
Bundled extractors: `GeoHashExtractor` (lat/lon points) and `FieldTokenExtractor` (text fields).

## Folder layout

```
client/crypttraject_client/
  __init__.py
  keys.py            # ClientSession: BFV ctx + key pair. save()/load()/to_session_descriptor()
  minhash.py         # compute_minhash()
  encrypt.py         # encrypt_signature(), encrypt_signatures()
  decrypt.py         # jaccard_from_diff_sq(), build_clusters()
  adapters/
    base.py          # DataSourceAdapter, FeatureExtractor, Record
    features.py      # GeoHashExtractor, FieldTokenExtractor
    csv_adapter.py
    json_adapter.py
    plt_adapter.py

server/crypttraject_server/
  __init__.py
  session.py         # SessionStore, ServerSession (public material only)
  homomorphic.py     # compute_pair_diff_sq(), run_pair_pipeline()

shared/crypttraject_shared/
  bfv_params.py      # BFVParams, DEFAULT_BFV_PARAMS, BFV_T
  wire.py            # SessionDescriptor, SignaturePayload, SimilarityRequest, SimilarityResult

packaging/           # PyInstaller specs + cross-platform build driver.
web/                 # React + Vite landing page.
docker/              # Dockerfiles for the server and the web landing.
docker-compose.yml   # `docker compose up` to launch server + web locally.
```

## Running with Docker (recommended for the server + web)

A `docker-compose.yml` brings up the FastAPI server and the static
landing in one command:

```
docker compose up --build
```

| Service  | URL                     | Purpose                                  |
| -------- | ----------------------- | ---------------------------------------- |
| `server` | http://localhost:8000   | FastAPI + Pyfhel — homomorphic ops       |
| `web`    | http://localhost:5173   | Landing page (nginx serving Vite build)  |

The desktop client (CLI / GUI) is **not** containerized — it needs a Qt
display and local filesystem access. Install it on the host
(`pip install -e .`) and point it at `http://localhost:8000`.

An optional dev shell is available behind a compose profile:

```
docker compose --profile dev run --rm dev
# drops into bash inside the server image, with source bind-mounted
```

Dockerfiles live in [docker/](docker/) and the build is wired so source
edits only invalidate the lightweight layers — Pyfhel + dependencies
are cached as long as `requirements.txt` is unchanged.

## Running it (bare metal)

Install once:

```
pip install -r requirements.txt
pip install -e .
```

Start the server:

```
uvicorn crypttraject_server.api:app --host 0.0.0.0 --port 8000
```

Run the end-to-end client (Geolife example):

```
crypttraject-client \
    --source plt --path "dataset/Geolife Trajectories 1.3/Data" \
    --features geohash --limit 50 \
    --server http://localhost:8000 \
    --key-dir ./keys
```

CSV with grouped lat/lon points:

```
crypttraject-client \
    --source csv --path data/trips.csv \
    --id-column trip_id --point-columns lat,lon \
    --features geohash --server http://localhost:8000
```

JSON-Lines with text fields:

```
crypttraject-client \
    --source jsonl --path data/records.jsonl \
    --id-field id --features tokens --text-fields title,tags \
    --server http://localhost:8000
```

## HTTP contract

| Method | Path                                   | Body                                                          | Returns                       |
| ------ | -------------------------------------- | ------------------------------------------------------------- | ----------------------------- |
| POST   | `/session`                             | multipart: `config` JSON + `context` + `public_key` files     | `{ session_id }`              |
| POST   | `/session/{sid}/signatures`            | multipart: `blob` file (encoded ciphertexts)                  | `{ ingested, total }`         |
| POST   | `/session/{sid}/cluster`               | JSON: `{ threshold }`                                         | `{ job_id, n_pairs }`         |
| GET    | `/session/{sid}/results/{job_id}`      | —                                                             | binary blob of pair ciphertexts |
| DELETE | `/session/{sid}`                       | —                                                             | `{ dropped: true }`           |

## Desktop GUI

A PySide6 wizard wraps the same pipeline:

```
crypttraject-gui
# or
python -m crypttraject_client.gui
```

Four pages: **Source → Encrypt → Cluster → Results**. Long-running steps
(BFV encryption, HTTP upload, server cluster job) run on background
`QThread`s so the UI stays responsive.

## Landing page (web/)

A React + Vite landing page lives in [web/](web/). It presents the
project, the BFV/MinHash/LSH pipeline, supported formats, and the
install instructions.

```
cd web
npm install
npm run dev       # http://localhost:5173 — hot-reload
npm run build     # outputs to web/dist/
```

The page is fully static; deployment is `npm run build` then upload
`web/dist/` to any static host (GitHub Pages, Netlify, etc.). It does
not call the FastAPI server — the install section points users to
build the client from source.

## Binary distribution

PyInstaller specs and a build driver live in [packaging/](packaging/).
Building from a working dev environment:

```
pip install pyinstaller
python packaging/build_binaries.py
```

Output: `dist/crypttraject/` (folder containing `crypttraject-cli` and
`crypttraject-gui` with all shared libs) plus
`dist/CryptTraject-<os>-<arch>.zip`.

PyInstaller does **not** cross-compile, so each OS must build on its own
runner. A GitHub Actions workflow at
[.github/workflows/release.yml](.github/workflows/release.yml) does
exactly that: it builds on Linux / Windows / macOS and attaches the
three zips to the GitHub Release on every `v*` tag. Trigger it manually
from the Actions tab to get artifacts without cutting a release.

The trickiest dependency is **Pyfhel**: its compiled SEAL extensions
are bundled via `collect_all("Pyfhel")` in
[packaging/crypttraject.spec](packaging/crypttraject.spec).

## Roadmap

1. ✅ Split client / server / shared.
2. ✅ FastAPI server exposing `POST /session`, `POST /signatures`, `POST /cluster`.
3. ✅ Client CLI (`crypttraject-client`) wiring adapters → encryption → HTTP.
4. ✅ Desktop GUI (`crypttraject-gui`) wrapping the same pipeline.
5. ✅ Landing page (React + Vite) in [web/](web/).
6. ✅ Binary distribution via PyInstaller + GitHub Actions (Linux / Windows / macOS).
