"""
Unit tests for the Job Match algorithm (no database needed).
Run:  python -m unittest test_job_match.py
"""

import unittest

from app import calculate_match, parse_skills, rank_jobs


class TestParseSkills(unittest.TestCase):
    def test_splits_trims_and_dedupes(self):
        self.assertEqual(parse_skills(" Python, SQL,,flask ; python "), ["Python", "SQL", "flask"])

    def test_empty(self):
        self.assertEqual(parse_skills(""), [])
        self.assertEqual(parse_skills(None), [])


class TestCalculateMatch(unittest.TestCase):
    def test_spec_example_full_match(self):
        result = calculate_match(["Python", "SQL", "Flask"], ["Python", "SQL", "Flask"])
        self.assertEqual(result["percent"], 100)
        self.assertEqual((result["matched_count"], result["total"]), (3, 3))
        self.assertEqual(result["missing"], [])

    def test_spec_example_partial_match(self):
        result = calculate_match(["Python", "SQL", "Flask"], ["Python", "SQL", "Tableau"])
        self.assertEqual(result["percent"], 67)
        self.assertEqual(result["missing"], ["Tableau"])

    def test_case_insensitive_and_aliases(self):
        result = calculate_match(["js", "POSTGRES", "html5"], ["JavaScript", "PostgreSQL", "HTML"])
        self.assertEqual(result["percent"], 100)

    def test_no_required_skills(self):
        self.assertEqual(calculate_match(["Python"], [])["percent"], 0)


class TestRankJobs(unittest.TestCase):
    JOBS = [
        {"job_id": 1, "job_title": "Data Analyst", "skills": ["Python", "SQL", "Tableau"]},
        {"job_id": 2, "job_title": "Software Developer", "skills": ["Python", "SQL", "Flask"]},
        {"job_id": 3, "job_title": "Designer", "skills": ["Figma"]},
        {"job_id": 4, "job_title": "No Skills Listed", "skills": []},
    ]

    def test_sorted_best_first_and_skips_jobs_without_skills(self):
        results = rank_jobs(["Python", "SQL", "Flask"], self.JOBS)
        self.assertEqual([r["job"]["job_id"] for r in results], [2, 1, 3])
        self.assertEqual([r["percent"] for r in results], [100, 67, 0])

    def test_minimum_percent_filter(self):
        results = rank_jobs(["Python", "SQL", "Flask"], self.JOBS, min_percent=50)
        self.assertEqual([r["job"]["job_id"] for r in results], [2, 1])


if __name__ == "__main__":
    unittest.main()
