from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass
class Prompt:
    text: str
    type: str

    def to_json(self):
        return {
            "type": self.type,
            "text": self.text,
        }


@dataclass
class Model:
    name: str
    options: Dict


@dataclass
class Check:
    name: str
    value: Any


@dataclass
class Case:
    name: str
    inputs: Dict[str, Any]
    checks: Tuple[Check, ...]


@dataclass
class Eval:
    ev: str
    """Version number for the llm_evals configuration file"""
    name: str
    """Human-readable name for this eval"""
    prompts: Tuple[Tuple[Prompt, ...], ...]
    """List of prompts to evaluate (parametrized)"""
    models: Tuple[Model, ...]
    """List of models to evaluate (parametrized)"""
    cases: Tuple[Case, ...]
    """List of test cases to evaluate (parametrized)"""
