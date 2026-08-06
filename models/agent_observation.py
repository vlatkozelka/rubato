from pydantic import BaseModel


class AgentObservation(BaseModel):
    step_id: str
    tool: str
    description: str
    result: str

def parse_observations(obs_dicts: list[dict]) -> list[AgentObservation]:
    return [AgentObservation.model_validate(d) for d in obs_dicts]