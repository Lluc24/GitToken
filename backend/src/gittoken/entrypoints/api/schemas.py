from pydantic import BaseModel

from gittoken.domain.agent import Agent
from gittoken.domain.estimator import ProfileEstimate


class AgentTokensResponse(BaseModel):
    agent: Agent
    commit_count: int
    lines_added: int
    tokens: int


class ProfileTokensResponse(BaseModel):
    login: str
    total_tokens: int
    agents: list[AgentTokensResponse]


def profile_tokens_response(estimate: ProfileEstimate) -> ProfileTokensResponse:
    return ProfileTokensResponse(
        login=estimate.login.value,
        total_tokens=estimate.total_tokens,
        agents=[
            AgentTokensResponse(
                agent=agent_estimate.agent,
                commit_count=agent_estimate.commit_count,
                lines_added=agent_estimate.lines_added,
                tokens=agent_estimate.tokens,
            )
            for agent_estimate in estimate.agent_estimates
        ],
    )
