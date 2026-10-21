from pydantic import BaseModel, ConfigDict, Field


class LoginInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=1,max_length=100)
    password: str = Field(min_length=1,max_length=128)


class PasswordChangeInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    current_password: str = Field(min_length=1,max_length=128)
    new_password: str = Field(min_length=8,max_length=128)
