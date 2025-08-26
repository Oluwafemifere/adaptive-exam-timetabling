from pydantic import BaseModel, Field, model_validator
from datetime import datetime, timezone
from typing import Optional

class TokenData(BaseModel):
    sub: str = Field(..., description="Subject (user identifier)")
    exp: Optional[int] = Field(None, description="Expiration time as UNIX timestamp")
    exp_datetime: Optional[datetime] = Field(None, description="Expiration time as datetime")

    # This runs before model creation
    @model_validator(mode="before")
    def compute_exp_datetime(cls, values: dict) -> dict:
        exp = values.get("exp")
        if exp is not None:
            values["exp_datetime"] = datetime.fromtimestamp(exp, tz=timezone.utc)
        return values

    # This runs after model creation
    @model_validator(mode="after")
    def check_not_expired(self) -> "TokenData":
        if self.exp_datetime and self.exp_datetime < datetime.now(timezone.utc):
            raise ValueError("Token has expired")
        return self
