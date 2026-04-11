from review_gate.project_agent_prompt_builder import ProjectAgentPromptBuilder


def test_project_agent_prompt_builder_includes_mixed_question_rules() -> None:
    builder = ProjectAgentPromptBuilder()

    prompt = builder.build(
        {
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_label": "first-migration-checkpoint",
            "stage_goal": "stabilize workflow to facts without widening the graph surface",
            "stage_summary": "generation-side orchestration split is complete",
            "current_decisions": ["split generation-side orchestration", "keep DTO shape stable"],
            "key_logic_points": ["checkpoint persistence", "transport compatibility"],
            "known_weak_points": ["real LLM output normalization"],
            "boundary_focus": ["project vs interview questions", "transport vs durable ids"],
            "max_questions": 4,
        }
    )

    assert "project-grounded questions" in prompt.system_prompt
    assert "interview-style fundamentals" in prompt.system_prompt
    assert "mid-level design and implementation questions" in prompt.system_prompt
    assert "higher-level trade-off or failure-mode questions" in prompt.system_prompt
    assert "Do not generate a question set made only of abstract architecture prompts." in prompt.system_prompt


def test_project_agent_prompt_builder_carries_stage_context_into_user_prompt() -> None:
    builder = ProjectAgentPromptBuilder()

    prompt = builder.build(
        {
            "project_id": "proj-1",
            "stage_id": "stage-2",
            "stage_label": "project-agent-llm-integration",
            "stage_goal": "make question generation more realistic",
            "stage_summary": "switch from stub generation to llm-backed generation",
            "current_decisions": ["llm first on generation side"],
            "boundary_focus": ["project relevance", "interview layering"],
            "max_questions": 3,
        }
    )

    assert "Project id: proj-1" in prompt.user_prompt
    assert "Stage id: stage-2" in prompt.user_prompt
    assert "Stage label: project-agent-llm-integration" in prompt.user_prompt
    assert "Stage goal: make question generation more realistic" in prompt.user_prompt
    assert "- Include at least one project-grounded question." in prompt.user_prompt
    assert "- Include at least one interview-style fundamentals question." in prompt.user_prompt


def test_project_agent_prompt_builder_exposes_stable_output_contract() -> None:
    builder = ProjectAgentPromptBuilder()

    prompt = builder.build(
        {
            "project_id": "proj-1",
            "stage_id": "stage-3",
            "max_questions": 2,
        }
    )

    question_contract = prompt.output_contract["questions"][0]
    assert question_contract["id"] == "q-1"
    assert question_contract["type"] == "open"
    assert question_contract["difficulty"] == "basic|intermediate|advanced"
