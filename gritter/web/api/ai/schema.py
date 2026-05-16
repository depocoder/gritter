from pydantic import BaseModel, Field


class InstanceAI(BaseModel):
    """Simple AI Instance."""

    prompt: str = Field(min_length=1)
