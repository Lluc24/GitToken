from pathlib import Path

import yaml
from pydantic import TypeAdapter

from gittoken.domain.attribution import AgentSignature

_AGENT_SIGNATURES = TypeAdapter(tuple[AgentSignature, ...])


def load_agent_signatures(signatures_file: Path) -> tuple[AgentSignature, ...]:
    return _AGENT_SIGNATURES.validate_python(yaml.safe_load(signatures_file.read_text()))
