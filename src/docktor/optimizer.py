from typing import List

from .parser import DockerInstruction, InstructionType
from .types import OptimizationResult


class DockerfileOptimizer:
    """
    Applies safe optimizations to a list of Dockerfile instructions.
    """

    def optimize(self, instructions: List[DockerInstruction]) -> OptimizationResult:
        """
        Runs the optimization pipeline.
        """
        all_changes: List[str] = []

        # --- Optimization Pipeline ---
        # 1. Combine RUN commands
        optimized_instructions, run_changes = self._combine_run_commands(instructions)
        all_changes.extend(run_changes)
        
        # 2. Pin untagged FROM images
        optimized_instructions, pin_changes = self._pin_untagged_from_image(optimized_instructions)
        all_changes.extend(pin_changes)

        # 3. Add apt-get cleanup
        optimized_instructions, clean_changes = self._clean_apt_get_installs(optimized_instructions)
        all_changes.extend(clean_changes)

        # 4. Add protocol to EXPOSE
        optimized_instructions, expose_changes = self._add_protocol_to_expose(optimized_instructions)
        all_changes.extend(expose_changes)

        # 5. Replace ADD with COPY 
        optimized_instructions, add_changes = self._replace_add_with_copy(optimized_instructions)
        all_changes.extend(add_changes)

        # 6. Combine consecutive metadata instructions 
        optimized_instructions, metadata_changes = self._combine_consecutive_metadata(optimized_instructions)
        all_changes.extend(metadata_changes)

        # 7. Remove unnecessary sudo 
        optimized_instructions, sudo_changes = self._remove_unnecessary_sudo(optimized_instructions)
        all_changes.extend(sudo_changes)

        # 8. Prepend 'apt-get update' where necessary
        optimized_instructions, update_changes = self._prepend_apt_get_update(optimized_instructions)
        all_changes.extend(update_changes)

        return OptimizationResult(
            optimized_instructions=optimized_instructions,
            applied_optimizations=all_changes,
        )

    def _combine_run_commands(self, instructions: List[DockerInstruction]) -> (List[DockerInstruction], List[str]):
        """Finds consecutive RUN commands and merges them."""
        new_instructions: List[DockerInstruction] = []
        changes_made: List[str] = []
        
        i = 0
        while i < len(instructions):
            current_instruction = instructions[i]
            
            if current_instruction.instruction_type == InstructionType.RUN:
                run_sequence = []
                while (i < len(instructions) and 
                       instructions[i].instruction_type == InstructionType.RUN):
                    run_sequence.append(instructions[i])
                    i += 1
                
                if len(run_sequence) > 1:
                    first_run = run_sequence[0]
                    combined_value = " \\\n    && ".join([run.value.strip() for run in run_sequence])
                    
                    merged_instruction = DockerInstruction(
                        line_number=first_run.line_number,
                        instruction_type=InstructionType.RUN,
                        original=f"RUN {combined_value}",
                        value=combined_value
                    )
                    new_instructions.append(merged_instruction)
                    changes_made.append(f"Combined {len(run_sequence)} RUN commands starting at line {first_run.line_number}.")
                else:
                    new_instructions.extend(run_sequence)
            else:
                new_instructions.append(current_instruction)
                i += 1
                
        return new_instructions, changes_made

    def _pin_untagged_from_image(self, instructions: List[DockerInstruction]) -> (List[DockerInstruction], List[str]):
            """Finds FROM instructions without a tag and pins them to 'latest'."""
            new_instructions: List[DockerInstruction] = []
            changes_made: List[str] = []

            for instruction in instructions:

                if instruction.instruction_type == InstructionType.FROM and instruction.tag is None:

                    original_image_name = instruction.image
                    pinned_image_value = f"{original_image_name}:latest"
                    
                    
                    if instruction.alias:
                        pinned_image_value += f" as {instruction.alias}"

                    new_instruction = DockerInstruction(
                        line_number=instruction.line_number,
                        instruction_type=InstructionType.FROM,
                        original=f"FROM {pinned_image_value}",
                        value=pinned_image_value,
                        image=instruction.image,
                        tag="latest",
                        alias=instruction.alias
                    )
                    new_instructions.append(new_instruction)
                    changes_made.append(f"Pinned untagged base image '{original_image_name}' to 'latest' at line {instruction.line_number}.")
                else:
                    new_instructions.append(instruction)
            
            return new_instructions, changes_made

    def _clean_apt_get_installs(self, instructions: List[DockerInstruction]) -> (List[DockerInstruction], List[str]):
        """Finds RUN apt-get installs and appends cache cleanup if missing."""
        new_instructions: List[DockerInstruction] = []
        changes_made: List[str] = []

        for instruction in instructions:
            if (instruction.instruction_type == InstructionType.RUN and
                    "apt-get install" in instruction.value and
                    "rm -rf /var/lib/apt/lists" not in instruction.value):

                new_value = f"{instruction.value.strip()} \\\n    && rm -rf /var/lib/apt/lists/*"
                
                new_instruction = DockerInstruction(
                    line_number=instruction.line_number,
                    instruction_type=InstructionType.RUN,
                    original=f"RUN {new_value}",
                    value=new_value
                )
                new_instructions.append(new_instruction)
                changes_made.append(f"Appended apt-get cache cleanup to RUN at line {instruction.line_number}.")
            else:
                new_instructions.append(instruction)
        
        return new_instructions, changes_made

    def _add_protocol_to_expose(self, instructions: List[DockerInstruction]) -> (List[DockerInstruction], List[str]):
        """Finds EXPOSE instructions without a protocol and adds /tcp."""
        new_instructions: List[DockerInstruction] = []
        changes_made: List[str] = []

        for instruction in instructions:
            if (instruction.instruction_type == InstructionType.EXPOSE and
                    "/tcp" not in instruction.value and
                    "/udp" not in instruction.value):

                new_value = f"{instruction.value.strip()}/tcp"
                
                new_instruction = DockerInstruction(
                    line_number=instruction.line_number,
                    instruction_type=InstructionType.EXPOSE,
                    original=f"EXPOSE {new_value}",
                    value=new_value
                )
                new_instructions.append(new_instruction)
                changes_made.append(f"Added default '/tcp' protocol to EXPOSE at line {instruction.line_number}.")
            else:
                new_instructions.append(instruction)
        
        return new_instructions, changes_made
    
    def _replace_add_with_copy(self, instructions: List[DockerInstruction]) -> (List[DockerInstruction], List[str]):
        """Replaces all ADD instructions with COPY for better security and clarity."""
        new_instructions: List[DockerInstruction] = []
        changes_made: List[str] = []

        for instruction in instructions:
            if instruction.instruction_type == InstructionType.ADD:
                
                new_instruction = DockerInstruction(
                    line_number=instruction.line_number,
                    instruction_type=InstructionType.COPY,
                    original=f"COPY {instruction.value}",
                    value=instruction.value
                )
                new_instructions.append(new_instruction)
                changes_made.append(f"Replaced 'ADD' with 'COPY' for security at line {instruction.line_number}.")
            else:
            
                new_instructions.append(instruction)
        
        return new_instructions, changes_made
    
    def _combine_consecutive_metadata(self, instructions: List[DockerInstruction]) -> (List[DockerInstruction], List[str]):
        """
        Merges consecutive ENV, LABEL, and ARG instructions to reduce layers.
        """
        new_instructions: List[DockerInstruction] = []
        changes_made: List[str] = []
        
        COMBINABLE_TYPES = [InstructionType.ENV, InstructionType.LABEL, InstructionType.ARG]
        
        i = 0
        while i < len(instructions):
            current_instruction = instructions[i]
            inst_type = current_instruction.instruction_type

            if inst_type in COMBINABLE_TYPES:
                sequence = []
                
                while (i < len(instructions) and 
                       instructions[i].instruction_type == inst_type):
                    sequence.append(instructions[i])
                    i += 1
                

                if len(sequence) > 1:
                    first_inst = sequence[0]

                    combined_value = " \\\n    ".join([inst.value.strip() for inst in sequence])
                    
                    merged_instruction = DockerInstruction(
                        line_number=first_inst.line_number,
                        instruction_type=inst_type,
                        original=f"{inst_type.value} {combined_value}",
                        value=combined_value
                    )
                    new_instructions.append(merged_instruction)
                    changes_made.append(f"Combined {len(sequence)} consecutive '{inst_type.value}' instructions starting at line {first_inst.line_number}.")
                else:
                    
                    new_instructions.extend(sequence)
            else:

                new_instructions.append(current_instruction)
                i += 1
                
        return new_instructions, changes_made
    
    def _remove_unnecessary_sudo(self, instructions: List[DockerInstruction]) -> (List[DockerInstruction], List[str]):
        """Removes unnecessary 'sudo' from RUN commands."""
        new_instructions: List[DockerInstruction] = []
        changes_made: List[str] = []

        for instruction in instructions:
            if instruction.instruction_type == InstructionType.RUN and "sudo " in instruction.value:
                
                new_value = instruction.value.replace("sudo ", "")
                
                new_instruction = DockerInstruction(
                    line_number=instruction.line_number,
                    instruction_type=InstructionType.RUN,
                    original=f"RUN {new_value}",
                    value=new_value
                )
                new_instructions.append(new_instruction)
                changes_made.append(f"Removed unnecessary 'sudo' from RUN at line {instruction.line_number}.")
            else:
                
                new_instructions.append(instruction)
        
        return new_instructions, changes_made
    
    def _prepend_apt_get_update(self, instructions: List[DockerInstruction]) -> (List[DockerInstruction], List[str]):
        """Finds RUN apt-get installs without update and prepends it."""
        new_instructions: List[DockerInstruction] = []
        changes_made: List[str] = []

        for instruction in instructions:
            if (instruction.instruction_type == InstructionType.RUN and
                    "apt-get install" in instruction.value and
                    "apt-get update" not in instruction.value):

                new_value = f"apt-get update && {instruction.value.strip()}"
                
                new_instruction = DockerInstruction(
                    line_number=instruction.line_number,
                    instruction_type=InstructionType.RUN,
                    original=f"RUN {new_value}",
                    value=new_value
                )
                new_instructions.append(new_instruction)
                changes_made.append(f"Prepended 'apt-get update' to RUN at line {instruction.line_number}.")
            else:
                new_instructions.append(instruction)
        
        return new_instructions, changes_made