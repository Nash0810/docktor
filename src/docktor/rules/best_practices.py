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
    
class RunInScratchImageRule(Rule):
    """
    Rule to detect RUN commands in a 'scratch' image, which will always fail.
    """

    @property
    def id(self) -> str:
        return "BP005"

    @property
    def description(self) -> str:
        return "RUN command cannot be used in a 'scratch' image."

    @property
    def explanation(self) -> str:
        return (
            "The 'FROM scratch' instruction creates a completely empty image with no "
            "shell or any other binaries. Because of this, any 'RUN' command is "
            "guaranteed to fail as there is no shell (like /bin/sh) to execute it. "
            "You can only use instructions like COPY or CMD in a scratch image."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        
    
        first_from = next((inst for inst in instructions if inst.instruction_type == InstructionType.FROM), None)
        
        if first_from and first_from.value.strip().lower() == "scratch":
         
            for instruction in instructions:
                if instruction.line_number > first_from.line_number:
                    if instruction.instruction_type == InstructionType.RUN:
                        issues.append(
                            Issue(
                                rule_id=self.id,
                                message="A 'RUN' instruction cannot be used after 'FROM scratch'.",
                                line_number=instruction.line_number,
                           
                                severity="error",
                                explanation=self.explanation,
                                fix_suggestion="Remove the RUN instruction or use a different base image that includes a shell."
                            )
                        )
          
                        break
        return issues
    
class InvalidCopyFromRule(Rule):
    """
    Rule to detect COPY --from commands that refer to a non-existent stage.
    """

    @property
    def id(self) -> str:
        return "BP006"

    @property
    def description(self) -> str:
        return "COPY --from must refer to a previously defined build stage."

    @property
    def explanation(self) -> str:
        return (
            "The '--from' flag in a 'COPY' or 'ADD' instruction must reference a "
            "stage name that was previously defined using 'FROM <image> AS <stage_name>'. "
            "Referring to a stage that does not exist is a syntax error that will "
            "cause the Docker build to fail immediately."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        defined_stages = set()

        for instruction in instructions:
            if instruction.instruction_type == InstructionType.FROM:
               
                parts = instruction.value.split()
                if len(parts) > 2 and parts[1].upper() == "AS":
                    defined_stages.add(parts[2])

        
        for instruction in instructions:
            if (instruction.instruction_type == InstructionType.COPY or
                    instruction.instruction_type == InstructionType.ADD):
                
                
                for part in instruction.value.split():
                    if part.lower().startswith("--from="):
                        stage_name = part.split("=")[1]
                        if stage_name not in defined_stages:
                            issues.append(
                                Issue(
                                    rule_id=self.id,
                                    message=f"COPY --from refers to a non-existent stage: '{stage_name}'.",
                                    line_number=instruction.line_number,
                                    severity="error",
                                    explanation=self.explanation,
                                    fix_suggestion="Ensure the stage name is spelled correctly and defined in a previous 'FROM ... AS ...' instruction."
                                )
                            )
                        break 
        return issues
    
class ShellFormCommandRule(Rule):
    """
    Rule to check for CMD/ENTRYPOINT instructions using the shell form
    instead of the recommended exec form.
    """

    @property
    def id(self) -> str:
        return "BP007"

    @property
    def description(self) -> str:
        return "Use the exec form of CMD/ENTRYPOINT for better signal handling."

    @property
    def explanation(self) -> str:
        return (
            "The 'shell form' of CMD or ENTRYPOINT (e.g., 'CMD my-app --arg') runs your "
            "command inside a shell, which can prevent OS signals like SIGTERM from "
            "reaching your application. This can lead to containers that do not shut "
            "down gracefully. The 'exec form' (e.g., 'CMD [\"my-app\", \"--arg\"]') is "
            "the recommended best practice as it handles signals correctly."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        for instruction in instructions:
            if (instruction.instruction_type == InstructionType.CMD or
                    instruction.instruction_type == InstructionType.ENTRYPOINT):
           
                if not instruction.value.strip().startswith("["):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"'{instruction.instruction_type.value}' is using the shell form instead of the exec form.",
                            line_number=instruction.line_number,
                            severity="info",
                            explanation=self.explanation,
                            fix_suggestion=f"Convert to the exec form, e.g., {instruction.instruction_type.value} [\"{instruction.value.split()[0]}\", \"...\"]"
                        )
                    )
        return issues
    
class WorkdirAbsoluteRule(Rule):
    """
    Rule to check that WORKDIR is using an absolute path.
    """

    @property
    def id(self) -> str:
        return "BP008"

    @property
    def description(self) -> str:
        return "Use absolute paths for WORKDIR for clarity and reliability."

    @property
    def explanation(self) -> str:
        return (
            "Using a relative path with 'WORKDIR' can be ambiguous and lead to "
            "unexpected behavior depending on the preceding instructions. Always "
            "using an absolute path (one that starts with '/') makes your Dockerfile "
            "more reliable, predictable, and easier for other developers to understand."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        for instruction in instructions:
            if instruction.instruction_type == InstructionType.WORKDIR:
                path = instruction.value.strip()
         
                if not path.startswith("/") and not path.startswith("$"):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message=f"WORKDIR path '{path}' is not absolute.",
                            line_number=instruction.line_number,
                            severity="info",
                            explanation=self.explanation,
                            fix_suggestion=f"Change the path to be absolute, e.g., '/{path}'."
                        )
                    )
        return issues
    
class AptGetUpdateBeforeInstallRule(Rule):
    """
    Rule to ensure 'apt-get update' is run in the same command as 'apt-get install'.
    """

    @property
    def id(self) -> str:
        return "BP009"

    @property
    def description(self) -> str:
        return "'apt-get install' should be preceded by 'apt-get update' in the same RUN command."

    @property
    def explanation(self) -> str:
        return (
            "Base images often have outdated package lists. Running 'apt-get install' "
            "without first running 'apt-get update' in the same command can lead to "
            "build failures if the package manager cannot locate the requested packages. "
            "Combining them with '&&' ensures the package lists are always fresh for "
            "the installation step."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        for instruction in instructions:
            if instruction.instruction_type == InstructionType.RUN:
            
                if "apt-get install" in instruction.value:
                 
                    if "apt-get update" not in instruction.value:
                        issues.append(
                            Issue(
                                rule_id=self.id,
                                message="RUN with 'apt-get install' is missing 'apt-get update'.",
                                line_number=instruction.line_number,
                                severity="error",
                                explanation=self.explanation,
                                fix_suggestion="Add 'apt-get update &&' before your 'apt-get install' command."
                            )
                        )
        return issues