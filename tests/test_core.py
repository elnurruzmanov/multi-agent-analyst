import graph
import ingestion
import memory


def test_chunk_splits_on_paragraphs():
    text = "a" * 300 + "\n\n" + "b" * 300 + "\n\n" + "c" * 100
    parts = ingestion.chunk(text, max_len=500)
    assert len(parts) == 2
    assert all(len(p) <= 500 for p in parts)


def test_memory_remember_and_recall():
    memory.remember("why do customers churn in Toshkent?", "because of failed tx")
    got = memory.recall("customers churn Toshkent reasons")
    assert "failed tx" in got
    assert memory.recall("completely unrelated topic xyz") == ""


def test_graph_end_to_end_mock():
    s = graph.ask("How many customers churned in Q1-2026?")
    assert s["answer"]
    assert any(st.startswith("supervisor") for st in s["steps"])
    assert any(st.startswith("critic") for st in s["steps"])


def test_graph_no_critic_ablation():
    s = graph.ask("Churn ta'rifi nima?", use_critic=False)
    assert s["answer"]
    assert not any(st.startswith("critic") for st in s["steps"])
