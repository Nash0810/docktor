from typing import List

from .parser import DockerInstruction, InstructionType
from .types import OptimizationResult


class DockerfileOptimizer:
    """
    Applies safe optimizations to a list of Dockerfile instructions.
    """

    def optimize(self, instructions: List[DockerInstruction]) -> OptimizationResult:
         
        all_changes: List[str] = []

        optimized_instructions, run_changes = self._combine_run_commands(instructions)
        all_changes.extend(run_changes)
   
        optimized_instructions, pin_changes = self._pin_untagged_from_image(optimized_instructions)
        all_changes.extend(pin_changes)

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
                   
                    combined_value = " \\\n    && ".join([run.value for run in run_sequence])
                    
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
            if instruction.instruction_type == InstructionType.FROM and ":" not in instruction.value:
               
                original_image = instruction.value
                pinned_image = f"{original_image}:latest"
                
                new_instruction = DockerInstruction(
                    line_number=instruction.line_number,
                    instruction_type=InstructionType.FROM,
                    original=f"FROM {pinned_image}",
                    value=pinned_image
                )
                new_instructions.append(new_instruction)
                changes_made.append(f"Pinned untagged base image '{original_image}' to 'latest' at line {instruction.line_number}.")
            else:
                # Pass all other instructions through unchanged
                new_instructions.append(instruction)
        
        return new_instructions, changes_made