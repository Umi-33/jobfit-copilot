import unittest

from backend.app.core.jd_parser import (
    extract_education,
    extract_experience,
    extract_salary,
    extract_tech_keywords,
)
from backend.app.core.profile_parser import extract_experience_years, extract_skills


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
