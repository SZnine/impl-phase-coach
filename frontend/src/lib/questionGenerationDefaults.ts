import type { GenerateQuestionSetRequestDTO } from "./api";

export const defaultQuestionGenerationLearningContext = {
  learning_goal: "练习当前阶段的真实项目题、面试基础题和误区诊断题",
  target_user_level: "intermediate",
  preferred_language: "zh-CN",
  question_mix: ["project implementation", "interview fundamentals", "mistake diagnosis", "failure scenario"],
  preferred_question_style: "concrete study-app question list with direct prompts and reviewable answers",
} satisfies Pick<
  GenerateQuestionSetRequestDTO,
  "learning_goal" | "target_user_level" | "preferred_language" | "question_mix" | "preferred_question_style"
>;
