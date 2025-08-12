from typing import List

from .base import Rule, Issue, DockerInstruction
from ..parser import InstructionType


class CombineRunRule(Rule):
    """
    Rule to check for consecutive RUN commands that can be combined.
    """

    @property
    def id(self) -> str:
        return "PERF001"

    @property
    def description(self) -> str:
        return "Combine consecutive RUN commands to reduce image layers."

    @property
    def explanation(self) -> str:
        return (
            "Each RUN command in a Dockerfile creates a new layer in the Docker image. "
            "Consolidating multiple RUN commands into a single one using '&&' reduces "
            "the number of layers, resulting in a smaller and potentially faster image."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []

        for i in range(len(instructions) - 1):
            current_instruction = instructions[i]
            next_instruction = instructions[i+1]

            # Check if the current and next instructions are both RUN commands
            if (current_instruction.instruction_type == InstructionType.RUN and
                    next_instruction.instruction_type == InstructionType.RUN):
                
                if i > 0 and instructions[i-1].instruction_type == InstructionType.RUN:
                    continue

                issues.append(
                    Issue(
                        rule_id=self.id,
                        message="Multiple consecutive RUN commands can be combined with '&&'.",
                        line_number=current_instruction.line_number,
                        severity="info",
                        explanation=self.explanation,  
                        fix_suggestion="Combine this RUN instruction with the following one(s)."
                    )
                )
        return issues
    
class AptGetCleanRule(Rule):
    """
    Rule to check that 'apt-get install' is followed by a cache cleanup.
    """

    @property
    def id(self) -> str:
        return "PERF002"

    @property
    def description(self) -> str:
        return "RUN apt-get install should clean up the apt-get cache in the same layer."

    @property
    def explanation(self) -> str:
        return (
            "Package managers like 'apt-get' leave behind a cache of downloaded package "
            "lists in '/var/lib/apt/lists/'. If this cache is not removed in the same "
            "RUN command that performed the installation, it gets baked into the "
            "image layer, needlessly increasing its size by several megabytes."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        for instruction in instructions:
            if instruction.instruction_type == InstructionType.RUN:
                # Check if the command uses apt-get install
                if "apt-get install" in instruction.value:
                    # Now check if it's missing the cleanup command
                    if "rm -rf /var/lib/apt/lists" not in instruction.value:
                        issues.append(
                            Issue(
                                rule_id=self.id,
                                message="RUN with 'apt-get install' is missing cache cleanup.",
                                line_number=instruction.line_number,
                                severity="warning",
                                explanation=self.explanation,
                                fix_suggestion="Append '&& rm -rf /var/lib/apt/lists/*' to the RUN command."
                            )
                        )
        return issues
    
class CacheBustingCopyRule(Rule):
    """
    Rule to detect when a broad 'COPY . .' happens before dependency installation,
    which busts the build cache.
    """
    # Common dependency installation commands
    INSTALL_COMMANDS = ["pip install", "npm install", "yarn install", "bundle install"]

    @property
    def id(self) -> str:
        return "PERF003"

    @property
    def description(self) -> str:
        return "Broad 'COPY' command before dependency installation can bust the cache."

    @property
    def explanation(self) -> str:
        return (
            "The Docker build cache works layer by layer. If you 'COPY' your entire "
            "source code before installing dependencies, any change to any file will "
            "invalidate the cache for the slow dependency installation step. You should "
            "first copy only the dependency manifest (e.g., requirements.txt), install "
            "dependencies, and then copy the rest of your source code."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        install_line_number = -1
        
        # First, find the line number of the dependency installation
        for instruction in instructions:
            if instruction.instruction_type == InstructionType.RUN:
                if any(cmd in instruction.value for cmd in self.INSTALL_COMMANDS):
                    install_line_number = instruction.line_number
                    break 
        
        if install_line_number == -1:
            return issues

        for instruction in instructions:
     
            if instruction.line_number >= install_line_number:
                break

            if instruction.instruction_type == InstructionType.COPY:
                
                if instruction.value.strip().startswith(". "):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            message="A broad 'COPY . ...' is used before dependency installation.",
                            line_number=instruction.line_number,
                            severity="warning",
                            explanation=self.explanation,
                            fix_suggestion="Copy only the dependency file (e.g., requirements.txt) first, run install, then copy the rest."
                        )
                    )
        return issues

class UnnecessaryPackagesRule(Rule):
    """
    Rule to detect the installation of common build-time packages
    in the final image.
    """
    # Common package managers' install commands
    INSTALL_CMDS = ["apt-get install", "apk add", "yum install"]
    
    # Common packages that are usually not needed in a final image
    UNNECESSARY_PACKAGES = [
        "build-essential",
        "gcc",
        "g++",
        "make",
        "git",
        "vim",
        "nano",
        "curl",
        "wget",
    ]

    @property
    def id(self) -> str:
        return "PERF004"

    @property
    def description(self) -> str:
        return "Avoid installing build-time dependencies in the final image."

    @property
    def explanation(self) -> str:
        return (
            "Installing build tools or utilities like 'git', 'gcc', or 'curl' "
            "increases the size and attack surface of your final production image. "
            "These packages are often only needed to build your application. Use a "
            "multi-stage build to compile assets or dependencies in a temporary 'builder' "
            "stage, then copy only the necessary artifacts to a clean final stage."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        for instruction in instructions:
            if instruction.instruction_type == InstructionType.RUN:
                # Check if this RUN command is an install command
                if any(cmd in instruction.value for cmd in self.INSTALL_CMDS):
                    # Check if any of the unnecessary packages are being installed
                    for package in self.UNNECESSARY_PACKAGES:
                    
                        if f" {package}" in instruction.value:
                            issues.append(
                                Issue(
                                    rule_id=self.id,
                                    message=f"Build-time package '{package}' is installed in the final image.",
                                    line_number=instruction.line_number,
                                    severity="info",
                                    explanation=self.explanation,
                                    fix_suggestion="Use a multi-stage build to keep the final image lean."
                                )
                            )
        return issues  



    """
    Rule to detect the installation of common build-time packages
    in the final image.
    """
    # Common package managers' install commands
    INSTALL_CMDS = ["apt-get install", "apk add", "yum install"]
    
    # Common packages that are usually not needed in a final image
    UNNECESSARY_PACKAGES = [
        "build-essential",
        "gcc",
        "g++",
        "make",
        "git",
        "vim",
        "nano",
        "curl",
        "wget",
    ]

    @property
    def id(self) -> str:
        return "PERF004"

    @property
    def description(self) -> str:
        return "Avoid installing build-time dependencies in the final image."

    @property
    def explanation(self) -> str:
        return (
            "Installing build tools or utilities like 'git', 'gcc', or 'curl' "
            "increases the size and attack surface of your final production image. "
            "These packages are often only needed to build your application. Use a "
            "multi-stage build to compile assets or dependencies in a temporary 'builder' "
            "stage, then copy only the necessary artifacts to a clean final stage."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        for instruction in instructions:
            if instruction.instruction_type == InstructionType.RUN:

                if any(cmd in instruction.value for cmd in self.INSTALL_CMDS):
                    
                    for package in self.UNNECESSARY_PACKAGES:

                        if f" {package}" in instruction.value:
                            issues.append(
                                Issue(
                                    rule_id=self.id,
                                    message=f"Build-time package '{package}' is installed in the final image.",
                                    line_number=instruction.line_number,
                                    severity="info",
                                    explanation=self.explanation,
                                    fix_suggestion="Use a multi-stage build to keep the final image lean."
                                )
                            )
        return issues
    
class AptGetUpgradeRule(Rule):
    """
    Rule to check for the use of 'apt-get upgrade', which can lead to
    non-deterministic builds.
    """
    FORBIDDEN_COMMANDS = ["apt-get upgrade", "apt-get dist-upgrade"]

    @property
    def id(self) -> str:
        return "PERF005"

    @property
    def description(self) -> str:
        return "Avoid using 'apt-get upgrade' or 'dist-upgrade' in Dockerfiles."

    @property
    def explanation(self) -> str:
        return (
            "Running 'apt-get upgrade' makes your Docker build non-deterministic. "
            "It can pull in different package versions each time the image is built, "
            "potentially introducing breaking changes unexpectedly. Instead of upgrading "
            "all packages, you should install specific, pinned versions of the packages "
            "your application requires."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        for instruction in instructions:
            if instruction.instruction_type == InstructionType.RUN:
                for command in self.FORBIDDEN_COMMANDS:
                    if command in instruction.value:
                        issues.append(
                            Issue(
                                rule_id=self.id,
                                message=f"Potentially unsafe command '{command}' found.",
                                line_number=instruction.line_number,
                                severity="warning",
                                explanation=self.explanation,
                                fix_suggestion="Remove the upgrade command. If you need a newer package, update the base image or install a specific version."
                            )
                        )
                        
                        break
        return issues
    
class BroadCopyRule(Rule):
    """
    Rule to check for broad 'COPY . .' commands that can hurt caching.
    """

    @property
    def id(self) -> str:
        return "PERF006"

    @property
    def description(self) -> str:
        return "Avoid broad 'COPY . .' commands; be specific to improve caching."

    @property
    def explanation(self) -> str:
        return (
            "Using a broad 'COPY . .' command copies every file from your build context, "
            "including files that don't affect your application like READMEs or the .git "
            "folder (if not ignored). Any change to any of these files will invalidate "
            "this layer's cache and trigger a rebuild of all subsequent layers. It is "
            "better to be specific and copy only the necessary directories (e.g., 'COPY src/ /app/src')."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        for instruction in instructions:
            if instruction.instruction_type == InstructionType.COPY:
            
                copy_args = instruction.value.split()
                if copy_args:
                    source_arg = copy_args[0]
                    if source_arg == "." or source_arg == "./":
                        issues.append(
                            Issue(
                                rule_id=self.id,
                                message="Broad 'COPY . .' pattern detected. This can harm layer caching.",
                                line_number=instruction.line_number,
                                severity="info",
                                explanation=self.explanation,
                                fix_suggestion="Be more specific in your COPY instruction, e.g., 'COPY src/ /app/src'."
                            )
                        )
        return issues
    
class RedundantUpdateRule(Rule):
    """
    Rule to check for redundant 'apt-get update' commands.
    """
    UPDATE_COMMAND = "apt-get update"

    @property
    def id(self) -> str:
        return "PERF007"

    @property
    def description(self) -> str:
        return "Avoid redundant 'apt-get update' commands."

    @property
    def explanation(self) -> str:
        return (
            "Calling 'apt-get update' multiple times in a Dockerfile is inefficient. "
            "The package lists only need to be updated once before the relevant "
            "'apt-get install' commands. Each redundant call slows down the build "
            "and can add unnecessary network overhead."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        update_found = False

        for instruction in instructions:
            if instruction.instruction_type == InstructionType.RUN:
                if self.UPDATE_COMMAND in instruction.value:
                    if update_found:
                        issues.append(
                            Issue(
                                rule_id=self.id,
                                message="Redundant 'apt-get update' command found.",
                                line_number=instruction.line_number,
                                severity="info",
                                explanation=self.explanation,
                                fix_suggestion="Consolidate your 'apt-get update' calls into a single command."
                            )
                        )
                    else:
                       
                        update_found = True
        return issues