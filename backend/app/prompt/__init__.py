"""Central registry for all LLM prompts used by Orthos backend agents.

Import from ``app.prompt`` (or submodules) rather than scattering prompt strings
across agents / FastAPI routes.
"""

from app.prompt.c4 import (
    LAYER_FRAMING,
    SYSTEM_PROMPT,
    build_prompt,
    build_repair_prompt,
)
from app.prompt.code_analysis import (
    CODE_ANALYSIS_FACTORS,
    CODE_ANALYSIS_SUPERVISOR_SYSTEM,
    build_code_analysis_factor_prompts,
    build_code_analysis_supervisor_prompts,
)
from app.prompt.docs import REFINED_DOCUMENTATION_AGENT_PROMPT
from app.prompt.explain import (
    EXPLAIN_COMPACT_SYSTEM,
    EXPLAIN_DEEP_SYSTEM,
    build_explain_user_prompt,
)

__all__ = [
    "LAYER_FRAMING",
    "SYSTEM_PROMPT",
    "build_prompt",
    "build_repair_prompt",
    "REFINED_DOCUMENTATION_AGENT_PROMPT",
    "EXPLAIN_COMPACT_SYSTEM",
    "EXPLAIN_DEEP_SYSTEM",
    "build_explain_user_prompt",
    "CODE_ANALYSIS_FACTORS",
    "CODE_ANALYSIS_SUPERVISOR_SYSTEM",
    "build_code_analysis_factor_prompts",
    "build_code_analysis_supervisor_prompts",
]
