"""Mock mode is the keyless demo path, so its answers have to be real answers.

These pin the behaviour that broke once already: the offline stand-ins must
follow the question instead of returning one canned result.
"""

import config
import graph
from agents import code_agent, data_sql


def test_mock_sql_follows_the_dimension_asked_about():
    assert "GROUP BY region" in config._mock_sql("qaysi regionda churn eng ko'p?")
    assert "GROUP BY segment" in config._mock_sql("premium vs retail churn?")
    assert "GROUP BY platform" in config._mock_sql("android or ios churn?")
    assert "Q1-2026" in config._mock_sql("how many customers churned in q1-2026?")


def test_mock_sql_handles_all_three_languages():
    for question in ("which region has most churn?",
                     "qaysi regionda churn eng ko'p?",
                     "в каком регионе больше всего оттока?"):
        assert "GROUP BY region" in config._mock_sql(question), question


def test_mock_sql_falls_back_to_portfolio_totals():
    assert "COUNT(*) AS customers" in config._mock_sql("something unrelated")


def test_mock_code_computes_the_percentage_in_the_question():
    assert config._mock_code("15% of 2600") == "print(round(15 / 100 * 2600, 2))"
    assert "17 / 100 * 340" in config._mock_code("what is 17% of 340?")
    assert "2 + 2" in config._mock_code("2 + 2")


def test_code_agent_returns_the_right_number_end_to_end():
    assert "390" in code_agent.run("Calculate 15% of 2600")


def test_data_agent_ranks_regions_correctly():
    out = data_sql.run("qaysi regionda churn eng ko'p?")
    assert "Farg'ona" in out.split("Result:")[1].splitlines()[1]


def test_draft_is_grounded_in_agent_output_not_a_canned_string():
    """Regression: the mock draft was keyed off a phrase in the critic's prompt,
    so editing that prompt silently disabled every offline answer."""
    answer = graph.ask("qaysi regionda churn eng ko'p?")["answer"]
    assert "Farg'ona" in answer
    assert "GEMINI_API_KEY" in answer  # the offline-mode disclaimer stays visible
