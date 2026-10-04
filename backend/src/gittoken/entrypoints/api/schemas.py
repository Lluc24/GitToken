from pydantic import BaseModel

from gittoken.domain.agent import Agent


class ProfileTokensResponse(BaseModel):
    login: str
    total_tokens: int
    tokens_by_agent: dict[Agent, int]
