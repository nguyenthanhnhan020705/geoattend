from pydantic import BaseModel, ConfigDict, Field


class CreateUserInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=1,max_length=100)
    full_name: str = Field(min_length=1,max_length=200)
    password: str = Field(min_length=8,max_length=128)


class ResetPasswordInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    new_password: str = Field(min_length=8,max_length=128)
