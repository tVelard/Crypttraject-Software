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

The desktop client (CLI) is **not** containerized — it runs on the user's
machine for local filesystem access and local key generation. Install it
on the host (`pip install -e .`) and point it at `http://localhost:8000`.

An optional dev shell is available behind a compose profile:

```
docker compose --profile dev run --rm dev
# drops into bash inside the server image, with source bind-mounted
```

Dockerfiles live in [docker/](docker/) and the build is wired so source
edits only invalidate the lightweight layers — Pyfhel + dependencies
are cached as long as `requirements.txt` is unchanged.

## Deploying on a VPS (production)

A separate composition wires the server and web behind a **Caddy** reverse
proxy that terminates TLS (automatic Let's Encrypt) and is the only service
publishing ports:

```
https://<domain>/         -> landing page (nginx)
https://<domain>/api/...  -> FastAPI server
```

The production server image is slimmer than the dev one: it installs
[requirements-server.txt](requirements-server.txt) (no PySide6/Qt) and only
the `shared` + `server` packages, via
[docker/server.prod.Dockerfile](docker/server.prod.Dockerfile).

Quick install on a fresh Debian/Ubuntu VPS:

```
git clone <repo> && cd CryptTraject-Software
./deploy.sh           # installs Docker if needed, creates .env, then starts
# edit .env  (set SITE_ADDRESS=your.domain and ACME_EMAIL=you@example.com)
./deploy.sh           # second run builds + starts the stack
```

Or manually:

```
cp .env.example .env  # edit SITE_ADDRESS / ACME_EMAIL
docker compose -f docker-compose.prod.yml up -d --build
```

| `.env` key                  | Meaning                                                        |
| --------------------------- | -------------------------------------------------------------- |
| `SITE_ADDRESS`              | Domain for HTTPS (e.g. `crypttraject.example.com`), or `:80` to serve plain HTTP on the IP while you have no domain |
| `ACME_EMAIL`                | Let's Encrypt contact email (only needed with a real domain)   |
| `CRYPTTRAJECT_CORS_ORIGINS` | Browser origins allowed to call the API; empty by default      |

DNS: point an `A`/`AAAA` record for your domain at the VPS IP **before**
setting `SITE_ADDRESS` to it, so Caddy can complete the ACME challenge.

The desktop client then points at the API base, e.g.:

```
crypttraject-client ... --server https://<domain>/api
```

**Note (prototype state):** the server keeps sessions and job results in
process memory, so a restart drops them — fine for demos, but re-upload is
needed after a redeploy.

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

## Windows installer (CLI)

The distributed artifact is a single one-click **Windows installer**,
`CryptTraject-Setup.exe`. The end user double-clicks it: the CLI is
installed to Program Files and added to PATH, so `crypttraject-cli` works
from any terminal with nothing else to install. Everything (Python,
Pyfhel/SEAL native libs) is bundled — no separate runtime needed.

Build chain in [packaging/](packaging/):

1. **PyInstaller** ([crypttraject.spec](packaging/crypttraject.spec))
   freezes the CLI into a self-contained `dist/crypttraject/` folder.
2. **Inno Setup** ([installer.iss](packaging/installer.iss)) wraps that
   folder into `dist/CryptTraject-Setup.exe`.

Build it on Windows from a working dev environment:

```
pip install pyinstaller          # plus Inno Setup 6 (https://jrsoftware.org/isdl.php)
python packaging/build_binaries.py
```

PyInstaller does **not** cross-compile and the installer targets Windows,
so the build runs on a Windows runner. The GitHub Actions workflow at
[.github/workflows/release.yml](.github/workflows/release.yml) builds the
installer and attaches `CryptTraject-Setup.exe` to the GitHub Release on
every `v*` tag (trigger it manually from the Actions tab to get the
artifact without cutting a release). On non-Windows hosts
`build_binaries.py` instead emits a plain zip for local dev use.

The trickiest dependency is **Pyfhel**: its compiled SEAL extensions
are bundled via `collect_all("Pyfhel")` in
[packaging/crypttraject.spec](packaging/crypttraject.spec).

### Serving the installer from the VPS

The landing page's download button points at `/download/CryptTraject-Setup.exe`,
served by the web container from the bind-mounted [downloads/](downloads/)
folder. Drop the built installer there on the VPS — no image rebuild needed:

```
scp dist/CryptTraject-Setup.exe root@<VPS>:~/Crypttraject-Software/downloads/
```

## Roadmap

1. ✅ Split client / server / shared.
2. ✅ FastAPI server exposing `POST /session`, `POST /signatures`, `POST /cluster`.
3. ✅ Client CLI (`crypttraject-client`) wiring adapters → encryption → HTTP.
4. ✅ Landing page (React + Vite) in [web/](web/).
5. ✅ Windows CLI installer via PyInstaller + Inno Setup + GitHub Actions.
