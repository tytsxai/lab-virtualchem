"""Pydantic request/response schemas for stdlib REST API.

Only request validation is used by the HTTPServer based API implementation.
All request models forbid unknown fields by default to prevent parameter
smuggling / silent typos.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ListRecordsQuery(StrictModel):
    user_id: str | None = None


class GetRecordQuery(StrictModel):
    user_id: str | None = None


class StartExperimentRequest(StrictModel):
    experiment_id: str = Field(min_length=1)
    user_id: str = Field(default="anonymous", min_length=1)


class SubmitStepRequest(StrictModel):
    session_id: str = Field(min_length=1)
    data: dict[str, Any] = Field(default_factory=dict)


class FinishExperimentRequest(StrictModel):
    session_id: str = Field(min_length=1)


class GenerateReportRequest(StrictModel):
    record_id: str = Field(min_length=1)
    format: Literal["html", "pdf"] = "html"

