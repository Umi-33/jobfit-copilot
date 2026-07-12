import unittest

from backend.app.core.jd_parser import (
    extract_education,
    extract_experience,
    extract_salary,
    extract_tech_keywords,
    parse_jd,
)
from backend.app.core.profile_parser import extract_experience_years, extract_skills, parse_profile
from backend.app.core.project_matcher import match_projects


class ProfileParserTests(unittest.TestCase):
    def test_calendar_years_and_project_duration_are_not_experience(self):
        profile = "2022年入学，2026年毕业。课程项目持续2年，无正式全职开发经验。"
        self.assertEqual(extract_experience_years(profile), 0.0)

    def test_explicit_profile_experience_is_still_supported(self):
        profile = "经验：1.5 年 Web / AI 工具原型经验。"
        self.assertEqual(extract_experience_years(profile), 1.5)

    def test_negated_skills_are_not_extracted(self):
        profile = """
        没有 React 经验。
        无 Docker/Linux 部署经验。
        未掌握 LangChain。
        不具备 TypeScript 生产经验。
        没有生产级 RAG/Agent 框架经验。
        """
        skills = set(extract_skills(profile))
        self.assertFalse(
            {"React", "Docker", "Linux", "LangChain", "TypeScript", "RAG", "Agent"} & skills
        )

    def test_affirmative_skill_before_contrast_is_preserved(self):
        skills = extract_skills("补充了解 RAG，但没有生产级经验。")
        self.assertIn("RAG", skills)

    def test_english_substrings_do_not_become_skills(self):
        skills = set(extract_skills("负责 storage 管理、reactive 状态和 next step 规划。"))
        self.assertNotIn("RAG", skills)
        self.assertNotIn("React", skills)
        self.assertNotIn("Next.js", skills)

    def test_explicit_agent_workflow_phrases_are_basic_agent_skills(self):
        cases = [
            "做过小型 Agentic Workflow 原型",
            "搭建过 Agent Workflow",
            "实现 Human-in-the-loop Agent 流程",
        ]
        for profile in cases:
            with self.subTest(profile=profile):
                skills = set(extract_skills(profile))
                self.assertIn("Agent", skills)
                self.assertNotIn("LangChain", skills)

    def test_negated_production_agent_does_not_create_agent_skill(self):
        skills = extract_skills("没有生产级 Agent 经验。")
        self.assertNotIn("Agent", skills)

    def test_job_direction_does_not_create_aigc_project(self):
        profile = parse_profile("求职方向：AIGC 内容管线。技能：Python、Prompt。")
        self.assertEqual(profile["projects"], [])

    def test_skills_do_not_create_visualization_project(self):
        profile = parse_profile("技能：Vue3、ECharts、数据可视化。")
        self.assertEqual(profile["projects"], [])

    def test_explicit_project_creates_record_from_user_text(self):
        profile = parse_profile("项目：JobFit Copilot，使用 Python 和 FastAPI 分析 JD。")
        self.assertEqual(len(profile["projects"]), 1)
        self.assertEqual(profile["projects"][0]["name"], "JobFit Copilot")
        self.assertEqual(profile["projects"][0]["summary"], "使用 Python 和 FastAPI 分析 JD。")
        self.assertEqual(set(profile["projects"][0]["tags"]), {"Python", "FastAPI"})

    def test_profile_without_project_returns_empty_list(self):
        profile = parse_profile("技能：Python、Vue3。计划学习 Docker。")
        self.assertEqual(profile["projects"], [])

    def test_only_explicit_projects_are_returned_with_other_skills(self):
        profile = parse_profile(
            "技能：Vue3、ECharts、AIGC 内容管线。\n"
            "求职方向：AI 前端。\n"
            "项目：JobFit Copilot，使用 Python 解析 JD。"
        )
        self.assertEqual([project["name"] for project in profile["projects"]], ["JobFit Copilot"])

    def test_declared_work_keeps_its_own_name(self):
        profile = parse_profile("作品：《绛珠踪》LLM API评估，使用 Prompt 约束输出。")
        self.assertEqual(profile["projects"][0]["name"], "《绛珠踪》LLM API评估")

    def test_multiline_project_block_reads_summary_and_tags(self):
        profile = parse_profile(
            """
            项目：JobFit Copilot｜AI 岗位筛选与面试准备助手
            - 这是一个面向个人真实求职流程的 AI 应用原型。
            - 后端使用 Python、FastAPI、SQLite 和可解释规则引擎实现。
            - 项目包含 Human-in-the-loop Agentic Workflow。
            - 已实现岗位解析、评分、风险识别和人工确认。
            """
        )
        project = profile["projects"][0]
        self.assertEqual(project["name"], "JobFit Copilot｜AI 岗位筛选与面试准备助手")
        self.assertTrue({"Python", "FastAPI", "Agent", "AI 工具落地"} <= set(project["tags"]))
        self.assertIn("面向个人真实求职流程", project["summary"])
        self.assertIn("Human-in-the-loop Agentic Workflow", project["summary"])
        self.assertNotEqual(project["summary"], project["name"])

    def test_top_level_section_stops_project_block(self):
        profile = parse_profile(
            """
            项目：JobFit Copilot
            - 使用 Python 和 FastAPI。
            能力边界：
            - 没有生产级 Docker、Linux 或 LangChain 经验。
            """
        )
        project = profile["projects"][0]
        self.assertEqual(set(project["tags"]), {"Python", "FastAPI"})
        self.assertNotIn("能力边界", project["summary"])

    def test_skills_outside_project_block_do_not_become_project_tags(self):
        profile = parse_profile(
            """
            项目：JobFit Copilot
            - 使用 Python 解析 JD。
            技能：Vue3、ECharts、Docker、Linux。
            """
        )
        self.assertEqual(profile["projects"][0]["tags"], ["Python"])

    def test_two_project_blocks_are_kept_separate(self):
        profile = parse_profile(
            """
            项目：JobFit Copilot
            - 使用 Python 和 FastAPI。
            项目：《前端可视化实验》
            - 使用 Vue3 和 ECharts。
            """
        )
        first, second = profile["projects"]
        self.assertEqual(first["name"], "JobFit Copilot")
        self.assertEqual(set(first["tags"]), {"Python", "FastAPI"})
        self.assertEqual(second["name"], "《前端可视化实验》")
        self.assertTrue({"Vue3", "ECharts", "数据可视化"} <= set(second["tags"]))
        self.assertFalse({"Python", "FastAPI"} & set(second["tags"]))

    def test_multiline_jobfit_project_can_be_recommended(self):
        profile = parse_profile(
            """
            项目：JobFit Copilot｜AI 岗位筛选与面试准备助手
            - 面向真实求职流程开发 AI 应用原型。
            - 后端使用 Python 和 FastAPI。
            - 包含 Human-in-the-loop Agentic Workflow。
            能力边界：
            - 没有生产级 Agent 框架经验。
            """
        )
        jd = parse_jd("校招 AI 前端岗位，负责对接大模型 API 和 Agent 工作流。")
        recommended = match_projects(profile, jd)
        self.assertEqual(len(profile["projects"]), 1)
        self.assertTrue(profile["projects"][0]["tags"])
        self.assertEqual(recommended[0]["name"], "JobFit Copilot｜AI 岗位筛选与面试准备助手")


class JdParserTests(unittest.TestCase):
    def test_graduation_dates_are_not_experience(self):
        cases = [
            "招聘2026届毕业生",
            "要求2026年毕业",
            "毕业时间：2026年-2027年",
            "面向在校/应届学生",
        ]
        for jd in cases:
            with self.subTest(jd=jd):
                self.assertEqual(extract_experience(jd)["min"], 0.0)

    def test_supported_experience_formats(self):
        cases = [
            ("要求1-3年经验", 1.0, 3.0),
            ("要求2年以上经验", 2.0, None),
            ("至少1年开发经验", 1.0, None),
        ]
        for jd, expected_min, expected_max in cases:
            with self.subTest(jd=jd):
                experience = extract_experience(jd)
                self.assertEqual(experience["min"], expected_min)
                self.assertEqual(experience["max"], expected_max)

    def test_graduation_range_is_not_salary(self):
        self.assertEqual(
            extract_salary("面向2026-2027届毕业生"),
            {"min": None, "max": None, "raw": None},
        )

    def test_supported_salary_formats(self):
        cases = [
            ("薪资10-15K", 10000, 15000),
            ("薪资10k-15k", 10000, 15000),
            ("薪资8000-12000", 8000, 12000),
        ]
        for jd, expected_min, expected_max in cases:
            with self.subTest(jd=jd):
                salary = extract_salary(jd)
                self.assertEqual(salary["min"], expected_min)
                self.assertEqual(salary["max"], expected_max)

    def test_bachelor_requirement_is_not_raised_by_master_preference(self):
        self.assertEqual(extract_education("本科及以上，硕士优先"), "本科")

    def test_jd_english_substrings_do_not_become_tech_keywords(self):
        keywords = set(extract_tech_keywords("维护 storage，使用 reactive 模式，规划 next step。"))
        self.assertNotIn("RAG", keywords)
        self.assertNotIn("React", keywords)
        self.assertNotIn("Next.js", keywords)


if __name__ == "__main__":
    unittest.main()
