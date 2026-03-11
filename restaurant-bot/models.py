from pydantic import BaseModel


class InputGuardrailOutput(BaseModel):
    is_off_topic: bool
    reason: str


class OutputGuardrailOutput(BaseModel):
    is_unprofessional: bool
    leaks_internal_info: bool
    reason: str
