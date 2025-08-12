from typing import List

from .base import Rule, Issue, DockerInstruction
from ..parser import InstructionType
import re

class AddInsteadOfCopyRule(Rule):

    @property
    def id(self) -> str:
        return "SEC001"

    @property
    def description(self) -> str:
        return "Use COPY instead of ADD unless you need ADD's specific features."

    @property
    def explanation(self) -> str:
        return (
            "The 'ADD' instruction has magic features like remote URL downloads and "
            "automatic tarball extraction. This can introduce security vulnerabilities "
            "if the source is compromised. 'COPY' is more transparent and safer as it "
            "only copies local files."
        )


    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        for instruction in instructions:
            if instruction.instruction_type == InstructionType.ADD:
                issues.append(
                    Issue(
                        rule_id=self.id,
                        message="ADD is used. Prefer COPY for clarity and security.",
                        line_number=instruction.line_number,
                        severity="warning",
                        explanation=self.explanation,  
                        fix_suggestion="Replace 'ADD' with 'COPY' if you are only copying local files."
                    )
                )

        return issues
    
class NonRootUserRule(Rule):
 

    @property
    def id(self) -> str:
        return "SEC002"

    @property
    def description(self) -> str:
        return "Container should not run as root user for security reasons."

    @property
    def explanation(self) -> str:
        return (
            "Running a container as the 'root' user is a security risk. It violates "
            "the Principle of Least Privilege. If an attacker compromises your "
            "application, they will gain root access inside the container, making it "
            "easier to escalate their attack. Best practice is to create a dedicated "
            "non-root user and switch to it with the 'USER' instruction."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        last_user_instruction: DockerInstruction | None = None

        
        for instruction in instructions:
            if instruction.instruction_type == InstructionType.USER:
                last_user_instruction = instruction
        
        
        if last_user_instruction is None:
            issues.append(
                Issue(
                    rule_id=self.id,
                    message="No 'USER' instruction found. Container will run as root.",
                    
                    line_number=instructions[-1].line_number if instructions else 1,
                    severity="warning",
                    explanation=self.explanation,
                    fix_suggestion="Add a non-root user and switch to them, e.g., 'USER myappuser'."
                )
            )

        elif last_user_instruction.value.strip() == "root":
            issues.append(
                Issue(
                    rule_id=self.id,
                    message="Container is explicitly set to run as 'root' user.",
                    line_number=last_user_instruction.line_number,
                    severity="warning",
                    explanation=self.explanation,
                    fix_suggestion="Switch to a non-root user."
                )
            )
            
        return issues

class EnvVarSecretsRule(Rule):

    SECRET_KEYWORDS = [
        "PASSWORD",
        "SECRET",
        "TOKEN",
        "API_KEY",
        "APIKEY",
        "ACCESS_KEY",
        "SECRET_KEY",
        "PASSWD",
    ]

    @property
    def id(self) -> str:
        return "SEC003"

    @property
    def description(self) -> str:
        return "Do not store secrets in environment variables."

    @property
    def explanation(self) -> str:
        return (
            "Setting secrets like passwords or API keys via 'ENV' is a major security "
            "risk. These values are stored in plain text within the image layers and "
            "can be easily viewed by anyone with access to the image using 'docker inspect'. "
            "Use build-time arguments with '--secret' mounts (for Docker BuildKit) or "
            "a runtime secret management system instead."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        for instruction in instructions:
            if instruction.instruction_type == InstructionType.ENV:
   
                env_var_key = instruction.value.split("=")[0].split()[0]
                
                
                for keyword in self.SECRET_KEYWORDS:
                    if keyword in env_var_key.upper():
                        issues.append(
                            Issue(
                                rule_id=self.id,
                                message=f"Potential secret found in ENV variable '{env_var_key}'.",
                                line_number=instruction.line_number,
                                severity="warning", 
                                explanation=self.explanation,
                                fix_suggestion="Use Docker secrets or build-time ARGs to handle sensitive data."
                            )
                        )
                       
                        break
        return issues
    
class CopyChownRule(Rule):


    @property
    def id(self) -> str:
        return "SEC004"

    @property
    def description(self) -> str:
        return "Use --chown with COPY/ADD when running as a non-root user."

    @property
    def explanation(self) -> str:
        return (
            "When you use 'COPY' or 'ADD', the new files are owned by 'root' by default. "
            "If you have switched to a non-root user with 'USER', that user may not have "
            "the necessary permissions to read or write these files. Using the '--chown' "
            "flag ensures that the copied files are owned by the correct application user "
            "from the start, preventing potential runtime permission errors."
        )

    def check(self, instructions: List[DockerInstruction]) -> List[Issue]:
        issues: List[Issue] = []
        last_user = "root"
        last_user_line = -1

       
        for instruction in instructions:
            if instruction.instruction_type == InstructionType.USER:
                last_user = instruction.value.strip()
                last_user_line = instruction.line_number

        
        if last_user == "root":
            return issues

        for instruction in instructions:
            if instruction.line_number > last_user_line:
                if (instruction.instruction_type == InstructionType.COPY or
                        instruction.instruction_type == InstructionType.ADD):
                    
                    if "--chown=" not in instruction.value:
                        issues.append(
                            Issue(
                                rule_id=self.id,
                                message=f"'{instruction.instruction_type.value}' is used without '--chown' after switching to non-root user '{last_user}'.",
                                line_number=instruction.line_number,
                                severity="warning",
                                explanation=self.explanation,
                                fix_suggestion=f"Add '--chown={last_user}' to the {instruction.instruction_type.value} command."
                            )
                        )
        return issues