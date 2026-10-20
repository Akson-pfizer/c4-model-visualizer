#!/usr/bin/env python3
"""CLI runner for the Documentation Agent (`c4-doc-agent`).

Usage:
    python scripts/run_doc_agent.py [PROJECT_PATH] [OUTPUT_FOLDER]

Defaults:
    PROJECT_PATH  = /Users/aksonsamvarghese/Work/claude_bootcamp/c4-model-visualizer
    OUTPUT_FOLDER = /Users/aksonsamvarghese/Work/claude_bootcamp/c4-model-visualizer/documentation
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.doc_agent import documentation_agent


def main() -> None:
    project_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else PROJECT_ROOT
    output_folder = (
        Path(sys.argv[2]).resolve()
        if len(sys.argv) > 2
        else (PROJECT_ROOT / "documentation")
    )

    result = documentation_agent.generate_documentation_suite(
        project_path=project_path,
        output_folder=output_folder,
    )
    print(
        json.dumps(
            {
                "agent_id": result["agent_id"],
                "project_path": result["project_path"],
                "output_folder": result["output_folder"],
                "diagrams_generated": result["diagrams_generated"],
                "sandbox_status": result["sandbox_execution"]["status"],
                "composite_architecture_score": result["evaluation_metrics"][
                    "composite_architecture_score"
                ],
                "total_files_written": len(result["files_written"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
