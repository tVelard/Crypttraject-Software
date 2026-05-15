"""Pydantic schemas for the HTTP layer.

Kept separate from the wire dataclasses in crypttraject_shared because
those are transport-agnostic and used by both sides. These Pydantic
models are server-input/output specific.
"""

from typing import Optional

from pydantic import BaseModel, Field


class SessionConfig(BaseModel):
    num_perm: int = Field(128, gt=0, le=8192)
    bands: int = Field(16, gt=0)
    rows_per_band: int = Field(8, gt=0)
    session_id: Optional[str] = None


class SessionCreated(BaseModel):
    session_id: str
    num_signatures: int = 0


class SignaturesIngested(BaseModel):
    session_id: str
    ingested: int
    total: int


class ClusterRequest(BaseModel):
    threshold: float = Field(0.5, ge=0.0, le=1.0)


class JobInfo(BaseModel):
    session_id: str
    job_id: str
    n_pairs: int
