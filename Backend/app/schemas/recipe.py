from typing import List

from pydantic import BaseModel, Field


class CleanStepsRequest(BaseModel):
    text: str = Field(..., description="Raw recipe step text")


class CleanStepsResponse(BaseModel):
    steps: List[str] = Field(default_factory=list)


__all__ = ["CleanStepsRequest", "CleanStepsResponse"]

