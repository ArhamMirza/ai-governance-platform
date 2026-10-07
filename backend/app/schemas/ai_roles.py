from pydantic import BaseModel


class AIRoleRead(BaseModel):
    code: str
    label: str
    parent: str
    description: str
