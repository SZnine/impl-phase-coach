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
    assert "Do not let all questions collapse into the same difficulty or the same category" in prompt.system_prompt
    assert "Use concrete module, persistence, migration, id-boundary, or failure-mode references" in prompt.system_prompt


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
    assert "- Make at least one question something a real backend/system-design interviewer could directly ask in an interview." in prompt.user_prompt
    assert "- Avoid letting every question sit at the same layer of abstraction." in prompt.user_prompt


def test_project_agent_prompt_builder_includes_bad_output_examples_to_avoid() -> None:
    builder = ProjectAgentPromptBuilder()

    prompt = builder.build(
        {
            "project_id": "proj-1",
            "stage_id": "stage-1",
            "stage_label": "project-agent-quality-tuning",
            "stage_goal": "improve project grounding and interview realism",
            "stage_summary": "project agent is live but question quality is still uneven",
            "current_decisions": ["project agent is provider-backed"],
            "key_logic_points": ["question taxonomy", "normalization stability"],
            "known_weak_points": ["level collapse"],
            "boundary_focus": ["project grounding", "interview realism"],
            "max_questions": 4,
        }
    )

    assert "Bad output examples to avoid:" in prompt.user_prompt
    assert "A set where every question is a generic architecture question." in prompt.user_prompt
    assert "A set where every question is effectively the same 'explain the design' prompt." in prompt.user_prompt
    assert "A set with no fundamentals question and no migration/failure-mode question." in prompt.user_prompt


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
