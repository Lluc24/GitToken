# ruff: noqa: S101 - tests assert by design
from gittoken.domain import (
    MIN_TOKENS_BY_RARITY,
    TOKENS_PER_ADDED_LINE,
    Agent,
    AgenticCommit,
    GithubProfile,
    GithubUserId,
    Rarity,
    VerifiedGithubUsername,
    find_agent,
)

_LOGIN = VerifiedGithubUsername("someone")
_GITHUB_ID = GithubUserId(1)


def profile_with(lines_added_by_agent: dict[Agent, int]) -> GithubProfile:
    return GithubProfile(
        _GITHUB_ID,
        _LOGIN,
        tuple(
            AgenticCommit(agent, lines_added) for agent, lines_added in lines_added_by_agent.items()
        ),
    )


def test_find_agent_matches_author_case_insensitively() -> None:
    assert find_agent(["NoReply@Anthropic.com"]) is Agent.CLAUDE_CODE


def test_find_agent_prefers_the_first_agent_among_authors() -> None:
    emails = ["person@example.com", "noreply@openai.com", "noreply@anthropic.com"]
    assert find_agent(emails) is Agent.CODEX


def test_find_agent_returns_none_without_an_agent_author() -> None:
    assert find_agent(["person@example.com"]) is None
    assert find_agent([]) is None


def test_tokens_scale_with_added_lines() -> None:
    assert AgenticCommit(Agent.CURSOR, 12).tokens == 12 * TOKENS_PER_ADDED_LINE


def test_total_tokens_sums_every_agentic_commit() -> None:
    profile = profile_with({Agent.CLAUDE_CODE: 3, Agent.COPILOT: 2})
    expected = 5 * TOKENS_PER_ADDED_LINE
    assert profile.total_tokens == expected


def test_tokens_by_agent_orders_largest_first() -> None:
    profile = profile_with({Agent.COPILOT: 2, Agent.CLAUDE_CODE: 3})
    assert list(profile.tokens_by_agent) == [Agent.CLAUDE_CODE, Agent.COPILOT]


def test_rarity_thresholds_are_inclusive() -> None:
    for rarity, min_tokens in MIN_TOKENS_BY_RARITY.items():
        at_threshold = GithubProfile(
            _GITHUB_ID,
            _LOGIN,
            (AgenticCommit(Agent.AIDER, min_tokens // TOKENS_PER_ADDED_LINE),),
        )
        if min_tokens % TOKENS_PER_ADDED_LINE:
            continue
        assert at_threshold.total_tokens == min_tokens
        assert at_threshold.rarity is rarity


def test_rarity_falls_just_below_a_threshold() -> None:
    one_below_rare = MIN_TOKENS_BY_RARITY[Rarity.RARE] - 1
    profile = GithubProfile(
        _GITHUB_ID,
        _LOGIN,
        (AgenticCommit(Agent.JULES, one_below_rare // TOKENS_PER_ADDED_LINE),),
    )
    assert profile.total_tokens < MIN_TOKENS_BY_RARITY[Rarity.RARE]
    assert profile.rarity is Rarity.COMMON


def test_no_agentic_commits_means_common_rarity() -> None:
    profile = GithubProfile(_GITHUB_ID, _LOGIN, ())
    assert profile.total_tokens == 0
    assert profile.tokens_by_agent == {}
    assert profile.rarity is Rarity.COMMON
