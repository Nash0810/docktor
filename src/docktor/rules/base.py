from abc import ABC, abstractmethod
from typing import List

from ..parser import DockerInstruction
from ..types import Issue


class Rule(ABC):
    """Abstract Base Class for all linting rules."""

    @property
    @abstractmethod
    def id(self) -> str:

        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def explanation(self) -> str:
        pass

    @abstractmethod
    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        pass
