from __future__ import annotations


class QuestionGenerationAgentClient:
    @classmethod
    def for_testing(cls) -> "QuestionGenerationAgentClient":
        return cls()

    def generate(self, request: dict) -> dict:
        strategy = request.get("question_strategy", "core_only")
        max_questions = int(request.get("max_questions", 1))
        questions: list[dict] = []

        if max_questions >= 1:
            questions.append(
                {
                    "question_id": "q-1",
                    "question_level": "core",
                    "prompt": "Explain the current-stage boundary.",
                    "intent": "Check current-stage understanding.",
                    "expected_signals": request.get("current_decisions", []),
                    "source_context": request.get("source_refs", []),
                }
            )

        if max_questions >= 2 and strategy in {"core_and_why", "full_depth"}:
            questions.append(
                {
                    "question_id": "q-2",
                    "question_level": "why",
                    "prompt": "Why did we choose this boundary?",
                    "intent": "Check reasoning about trade-offs.",
                    "expected_signals": request.get("boundary_focus", []),
                    "source_context": request.get("source_refs", []),
                }
            )

        if max_questions >= 3 and strategy == "full_depth":
            questions.append(
                {
                    "question_id": "q-3",
                    "question_level": "abstract",
                    "prompt": "How does this boundary generalize?",
                    "intent": "Check boundary transfer.",
                    "expected_signals": request.get("boundary_focus", []),
                    "source_context": request.get("source_refs", []),
                }
            )

        return {
            "request_id": request["request_id"],
            "questions": questions,
            "generation_summary": f"Generated {len(questions)} structured questions.",
            "coverage_notes": [],
            "warnings": [],
            "confidence": 0.8,
        }


class AssessmentAgentClient:
    @classmethod
    def for_testing(cls) -> "AssessmentAgentClient":
        return cls()

    def assess(self, request: dict) -> dict:
        answer = str(request.get("user_answer", "")).strip()
        answer_length = len(answer)

        if answer_length < 20:
            verdict = "weak"
            recommended_action = "redirect_to_learning"
            confidence = 0.7
            score_total = 0.35
        elif answer_length < 80:
            verdict = "partial"
            recommended_action = "continue_answering"
            confidence = 0.8
            score_total = 0.72
        else:
            verdict = "strong"
            recommended_action = "continue_answering"
            confidence = 0.9
            score_total = 0.9

        assessment = {
            "score_total": score_total,
            "dimension_scores": {
                "correctness": 3 if verdict != "weak" else 1,
                "reasoning": 3 if verdict == "strong" else 2,
                "decision_awareness": 2 if verdict != "weak" else 1,
                "boundary_awareness": 3 if verdict != "weak" else 1,
                "stability": 3 if verdict == "strong" else 2,
            },
            "verdict": verdict,
            "core_gaps": [] if verdict == "strong" else ["Needs deeper boundary explanation."],
            "misconceptions": [],
            "evidence": [f"assessment evidence: verdict={verdict}"] if answer else [],
        }

        return {
            "request_id": request["request_id"],
            "assessment": assessment,
            "recommended_action": recommended_action,
            "recommended_follow_up_questions": [] if verdict == "strong" else ["Explain the why again."],
            "learning_recommendations": [] if verdict == "strong" else ["Revisit the stage boundary."],
            "warnings": [],
            "confidence": confidence,
        }