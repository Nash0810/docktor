import re
from typing import List

import requests

from ..parser import DockerInstruction, InstructionType
from ..rules.base import Rule
from ..types import Issue


class NewerVersionAvailableRule(Rule):
    """Check Docker Hub for newer patch versions of base images.

    ID: REG001
    """

    @property
    def id(self) -> str:
        return "REG001"

    @property
    def description(self) -> str:
        return "Check if a newer patch version is available for the base image."

    @property
    def explanation(self) -> str:
        return (
            "Queries Docker Hub to see if a higher patch version exists for the base image tag."
        )

    def _parse_leading_version(self, tag: str):
        m = re.match(r"^(\d+(?:\.\d+)*)", tag)
        if not m:
            return None
        parts = [int(p) for p in m.group(1).split('.')]
        return tuple(parts)

    def _is_higher(self, a: tuple, b: tuple) -> bool:
        # Compare two version tuples elementwise
        la = list(a)
        lb = list(b)
        # Pad with zeros
        n = max(len(la), len(lb))
        la += [0] * (n - len(la))
        lb += [0] * (n - len(lb))
        return tuple(la) > tuple(lb)

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []

        for instr in instructions:
            if instr.instruction_type != InstructionType.FROM:
                continue

            if not instr.tag:
                continue

            if instr.tag.lower() == "latest":
                continue

            image = instr.image or ""

            # Determine namespace and image name (assume library if no namespace)
            if '/' in image:
                namespace, image_name = image.split('/', 1)
            else:
                namespace = 'library'
                image_name = image

            # Build version prefix (major.minor) if possible
            tag_parts = instr.tag.split('.')
            if len(tag_parts) >= 2:
                prefix = f"{tag_parts[0]}.{tag_parts[1]}"
            else:
                prefix = instr.tag

            api_url = f"https://hub.docker.com/v2/repositories/{namespace}/{image_name}/tags"
            params = {"page_size": 100}

            try:
                resp = requests.get(api_url, params=params, timeout=2)
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                # On network failure or other errors, do not crash the linter.
                continue

            candidates = []
            results = data.get('results', []) if isinstance(data, dict) else []
            for entry in results:
                name = entry.get('name') if isinstance(entry, dict) else None
                if not name:
                    continue
                if not name.startswith(prefix):
                    continue
                ver = self._parse_leading_version(name)
                if ver is None:
                    continue
                candidates.append((ver, name))

            if not candidates:
                continue

            # parse current tag
            current_ver = self._parse_leading_version(instr.tag)
            if current_ver is None:
                continue

            # find the highest candidate greater than current
            higher = [c for c in candidates if self._is_higher(c[0], current_ver)]
            if not higher:
                continue

            best = max(higher, key=lambda x: x[0])
            best_tag = best[1]

            message = f"Newer version available: {image}:{best_tag}."
            issues.append(Issue(rule_id=self.id, message=message, line_number=instr.line_number, explanation=self.explanation))

        return issues
