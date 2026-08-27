from pydantic import BaseModel, ConfigDict


class FrameworkControlRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    framework: str
    code: str
    title: str
    description: str | None


class FrameworkTagsUpdate(BaseModel):
    control_ids: list[int]
