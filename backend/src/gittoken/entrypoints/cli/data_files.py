from pathlib import Path

import yaml
from pydantic import TypeAdapter

from gittoken.domain.attribution import AgentSignature
from gittoken.domain.estimator import EstimatorVersion

_AGENT_SIGNATURES = TypeAdapter(tuple[AgentSignature, ...])
_ESTIMATOR_VERSION = TypeAdapter(EstimatorVersion)


def load_agent_signatures(signatures_file: Path) -> tuple[AgentSignature, ...]:
    return _AGENT_SIGNATURES.validate_python(yaml.safe_load(signatures_file.read_text()))


def load_estimator_version(estimator_version_file: Path) -> EstimatorVersion:
    return _ESTIMATOR_VERSION.validate_python(yaml.safe_load(estimator_version_file.read_text()))
