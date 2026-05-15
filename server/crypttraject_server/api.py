"""FastAPI application for the CryptTraject server.

Run locally:
    uvicorn crypttraject_server.api:app --reload

Endpoints:
    POST   /session                          create a session from public material
    POST   /session/{sid}/signatures         upload an encoded blob of ciphertexts
    POST   /session/{sid}/cluster            run the pairwise homomorphic pipeline
    GET    /session/{sid}/results/{job_id}   download the binary result blob
    DELETE /session/{sid}                    drop the session
"""

from __future__ import annotations

import json
from typing import Dict
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Path, UploadFile
from fastapi.responses import Response

from crypttraject_shared import (
    SessionDescriptor,
    SignaturePayload,
    EncryptedSignature,
    decode_blobs,
    encode_blobs,
    pair_key,
)

from .homomorphic import run_pair_pipeline
from .schemas import (
    ClusterRequest,
    JobInfo,
    SessionConfig,
    SessionCreated,
    SignaturesIngested,
)
from .session import SessionStore


app = FastAPI(
    title="CryptTraject server",
    version="0.1.0",
    description="Homomorphic clustering server. Never receives secret keys.",
)

store = SessionStore()

# Job results live in memory keyed by (session_id, job_id) for the prototype.
_jobs: Dict[tuple, bytes] = {}


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------

@app.post("/session", response_model=SessionCreated)
async def create_session(
    config: str = Form(..., description="JSON-encoded SessionConfig"),
    context: UploadFile = File(..., description="BFV context bytes"),
    public_key: UploadFile = File(..., description="BFV public key bytes"),
) -> SessionCreated:
    try:
        cfg = SessionConfig(**json.loads(config))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=f"invalid config JSON: {exc}")

    if cfg.bands * cfg.rows_per_band != cfg.num_perm:
        raise HTTPException(
            status_code=400,
            detail=f"bands * rows_per_band ({cfg.bands * cfg.rows_per_band}) must equal num_perm ({cfg.num_perm})",
        )

    descriptor = SessionDescriptor(
        session_id=cfg.session_id or uuid4().hex,
        context_bytes=await context.read(),
        public_key_bytes=await public_key.read(),
        num_perm=cfg.num_perm,
        bands=cfg.bands,
        rows_per_band=cfg.rows_per_band,
    )
    session = store.register(descriptor)
    return SessionCreated(session_id=session.descriptor.session_id)


@app.delete("/session/{session_id}")
async def drop_session(session_id: str = Path(...)) -> dict:
    store.drop(session_id)
    return {"session_id": session_id, "dropped": True}


# ---------------------------------------------------------------------------
# Signatures upload
# ---------------------------------------------------------------------------

@app.post("/session/{session_id}/signatures", response_model=SignaturesIngested)
async def upload_signatures(
    session_id: str = Path(...),
    blob: UploadFile = File(..., description="Encoded ciphertext blob (see codec.encode_blobs)"),
) -> SignaturesIngested:
    try:
        session = store.get(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown session {session_id}")

    try:
        items = decode_blobs(await blob.read())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"bad ciphertext blob: {exc}")

    payload = SignaturePayload(
        session_id=session_id,
        signatures=[EncryptedSignature(rid, ct) for rid, ct in items.items()],
    )
    ingested = session.ingest_signatures(payload)
    return SignaturesIngested(
        session_id=session_id,
        ingested=ingested,
        total=len(session.signatures),
    )


# ---------------------------------------------------------------------------
# Pairwise homomorphic clustering
# ---------------------------------------------------------------------------

@app.post("/session/{session_id}/cluster", response_model=JobInfo)
async def run_cluster(
    session_id: str = Path(...),
    request: ClusterRequest = ClusterRequest(),  # body is optional
) -> JobInfo:
    try:
        session = store.get(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown session {session_id}")

    if len(session.signatures) < 2:
        raise HTTPException(
            status_code=400,
            detail=f"need at least 2 signatures, have {len(session.signatures)}",
        )

    pair_to_ctxt = run_pair_pipeline(session)
    blob = encode_blobs(
        (pair_key(a, b), ct) for (a, b), ct in pair_to_ctxt.items()
    )

    job_id = uuid4().hex
    _jobs[(session_id, job_id)] = blob
    return JobInfo(session_id=session_id, job_id=job_id, n_pairs=len(pair_to_ctxt))


@app.get("/session/{session_id}/results/{job_id}")
async def download_results(
    session_id: str = Path(...),
    job_id: str = Path(...),
) -> Response:
    blob = _jobs.get((session_id, job_id))
    if blob is None:
        raise HTTPException(status_code=404, detail="unknown job")
    return Response(content=blob, media_type="application/octet-stream")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "sessions": len(store._sessions)}
