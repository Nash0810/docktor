from typing import List

from .base import Rule, Issue, DockerInstruction
from ..parser import InstructionType


class PinnedVersionRule(Rule):
    """
    Rule to check for unpinned base image versions (i.e., 'latest' tag or no tag).
    """

    @property
    def id(self) -> str:
        return "BP001"

    @property
    def description(self) -> str:
        return "Base image should have a pinned version, not 'latest' or no tag."

    @property
    def explanation(self) -> str:
        return (
            "Using 'latest' or no tag makes your builds non-deterministic. "
            "A new version of the image could be pushed at any time, potentially "
            "introducing breaking changes or vulnerabilities into your application."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        for instruction in instructions:
            if instruction.instruction_type == InstructionType.FROM:
                image_name = instruction.value
                if ":" not in image_name or image_name.endswith(":latest"):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Base image '{image_name}' uses an unpinned version.",
                            line_number=instruction.line_number,
                            explanation=self.explanation, 
                            fix_suggestion=f"Pin the image to a specific version. E.g., '{image_name.split(':')[0]}:3.11-slim'."
                        )
                    )
        return issues
    
class MissingHealthcheckRule(Rule):
    @property
    def id(self) -> str:
        return "BP002"

    @property
    def description(self) -> str:
        return "An EXPOSE instruction is present without a corresponding HEALTHCHECK."

    @property
    def explanation(self) -> str:
        return (
            "When a port is exposed via 'EXPOSE', it implies a service is listening. "
            "Without a 'HEALTHCHECK' instruction, Docker can only know if the container "
            "is running, not if the service inside it is actually healthy. "
            "Orchestration tools like Kubernetes or Docker Swarm use health checks "
            "to correctly manage traffic, restarts, and rolling deployments."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        
        # Check if any EXPOSE instruction exists
        expose_instruction = next((inst for inst in instructions if inst.instruction_type == InstructionType.EXPOSE), None)
        
        if expose_instruction:
            
            has_healthcheck = any(inst.instruction_type == InstructionType.HEALTHCHECK for inst in instructions)
            
            if not has_healthcheck:
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message="Dockerfile exposes a port but no HEALTHCHECK is defined.",
                  
                        line_number=expose_instruction.line_number,
                        severity="warning",
                        explanation=self.explanation,
                        fix_suggestion="Add a HEALTHCHECK instruction to test the exposed service."
                    )
                )
                
        return issues
    
class ExposePortWithoutProtocolRule(Rule):
    """
    Rule to check that EXPOSE instructions specify a protocol (TCP/UDP).
    """

    @property
    def id(self) -> str:
        return "BP003"

    @property
    def description(self) -> str:
        return "EXPOSE instructions should specify the protocol (e.g., 80/tcp)."

    @property
    def explanation(self) -> str:
        return (
            "While Docker defaults to TCP for exposed ports, explicitly stating the "
            "protocol (e.g., 'EXPOSE 80/tcp' or 'EXPOSE 53/udp') makes the Dockerfile "
            "unambiguous and serves as clearer documentation for developers maintaining "
            "the service."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        for instruction in instructions:
            if instruction.instruction_type == InstructionType.EXPOSE:
                port_value = instruction.value
                
                if "/tcp" not in port_value and "/udp" not in port_value:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"Port '{port_value}' is exposed without a /tcp or /udp protocol.",
                            line_number=instruction.line_number,
                            severity="info", \
                            explanation=self.explanation,
                            fix_suggestion=f"Specify the protocol, e.g., 'EXPOSE {port_value}/tcp'."
                        )
                    )
        return issues
    
class MissingLabelRule(Rule):
    """
    Rule to check that the Dockerfile contains a LABEL instruction for metadata.
    """

    @property
    def id(self) -> str:
        return "BP004"

    @property
    def description(self) -> str:
        return "Dockerfile should have a LABEL instruction for image metadata."

    @property
    def explanation(self) -> str:
        return (
            "The 'LABEL' instruction adds key-value metadata to your image, such as "
            "maintainer info, version number, or a link to the source repository. "
            "This metadata is very useful for organizing and managing images in a "
            "professional or automated environment."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        
        # Check if any LABEL instruction exists in the entire file
        has_label = any(inst.instruction_type == InstructionType.LABEL for inst in instructions)
        
        if not has_label:
            issues.append(
                Issue(
                    rule_id=self.id,
                    message="No LABEL instruction found. Consider adding metadata to your image.",
                    
                    line_number=1,
                    severity="info",
                    explanation=self.explanation,
                    fix_suggestion='Add a LABEL instruction, e.g., LABEL maintainer="you@example.com".'
                )
            )
            
        return issues