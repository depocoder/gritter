from pydantic import BaseModel, Field


class InstanceAI(BaseModel):
    """Simple AI Instance."""

    model: str = Field(min_length=1)
    promt: str = Field(min_length=1)
