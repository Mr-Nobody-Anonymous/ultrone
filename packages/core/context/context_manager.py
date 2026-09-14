# Copyright (c) Ultrone Contributors. All rights reserved.
"""ContextManager: Assembles, optimizes, and budgets prompt context."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .compaction import ContextCompactor
from .context_budget import ContextBudget
from .relevance import RelevanceRanker
from .token_counter import TokenCounter


class ContextManager:
    """Manages prompt assembly adhering to strict model token limits."""

    def __init__(self, budget: Optional[ContextBudget] = None) -> None:
        self.budget = budget or ContextBudget()

    def assemble_context(
        self,
        system_instructions: str,
        goal: str,
        user_request: str,
        memories: Optional[List[str]] = None,
        skills: Optional[List[str]] = None,
        files: Optional[Dict[str, str]] = None,
        observations: Optional[List[str]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Assemble structured and budget-compliant prompt."""
        sections: List[str] = []

        # 1. System instructions
        sys_text = ContextCompactor.compact_text(system_instructions, self.budget.system_instructions)
        if sys_text:
            sections.append(f"### SYSTEM INSTRUCTIONS\n{sys_text}")

        # 2. Goal
        goal_text = ContextCompactor.compact_text(goal, self.budget.goal_and_task)
        if goal_text:
            sections.append(f"### ACTIVE GOAL\n{goal_text}")

        # 3. Relevant Memories
        if memories:
            relevant_mems = RelevanceRanker.rank_items(goal + " " + user_request, memories, top_k=5)
            mem_block = "\n".join(f"- {m}" for m in relevant_mems)
            compact_mem = ContextCompactor.compact_text(mem_block, self.budget.memories)
            sections.append(f"### RELEVANT MEMORY\n{compact_mem}")

        # 4. Relevant Skills
        if skills:
            relevant_skills = RelevanceRanker.rank_items(goal + " " + user_request, skills, top_k=3)
            skills_block = "\n".join(f"- {s}" for s in relevant_skills)
            compact_skills = ContextCompactor.compact_text(skills_block, self.budget.skills)
            sections.append(f"### AVAILABLE SKILLS\n{compact_skills}")

        # 5. Relevant Files
        if files:
            file_entries: List[str] = []
            for path, content in files.items():
                compact_content = ContextCompactor.compact_text(content, max(500, self.budget.files_and_code // len(files)))
                file_entries.append(f"File: {path}\n```\n{compact_content}\n```")
            all_files = "\n\n".join(file_entries)
            compact_files = ContextCompactor.compact_text(all_files, self.budget.files_and_code)
            sections.append(f"### CONTEXT FILES\n{compact_files}")

        # 6. Observations & Tools
        obs_parts: List[str] = []
        if observations:
            obs_parts.extend([f"Obs: {o}" for o in observations[-5:]])
        if tool_results:
            obs_parts.extend([f"Tool [{t.get('tool', 'tool')}]: {t.get('result', '')}" for t in tool_results[-5:]])
        if obs_parts:
            obs_block = "\n".join(obs_parts)
            compact_obs = ContextCompactor.compact_text(obs_block, self.budget.observations_and_tools)
            sections.append(f"### RECENT OBSERVATIONS & TOOL RESULTS\n{compact_obs}")

        # 7. User Request
        user_text = ContextCompactor.compact_text(user_request, self.budget.user_prompt)
        sections.append(f"### USER REQUEST\n{user_text}")

        assembled = "\n\n".join(sections)
        return assembled

    def estimate_tokens(self, text: str) -> int:
        return TokenCounter.count_tokens(text)

    def ensure_budget(self, text: str, max_tokens: int) -> str:
        """Enforces that text strictly stays within max_tokens, compacting if necessary."""
        tokens = self.estimate_tokens(text)
        if tokens <= max_tokens:
            return text
        return ContextCompactor.compact_text(text, max_tokens)
