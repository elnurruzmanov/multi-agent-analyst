"""F13/F14 — Gradio UI: chat with a live multi-agent trace panel.

Run: python app_gradio.py  ->  http://localhost:7860
Colab deploy: end with demo.launch(share=True) for a public link.
"""

import gradio as gr

import graph


def respond(question, history):
    s = graph.ask(question)
    trace = "\n".join("• " + st for st in s["steps"])
    return f"{s['answer']}\n\n---\n**Trace:**\n{trace}"


demo = gr.ChatInterface(
    fn=respond,
    title="Bank Multi-Agent AI Analyst — Elnur Ruzmanov",
    description=(
        "Supervisor + retriever/web/SQL/code agents + critic. "
        "Domain: digital banking churn (synthetic SQB-style data). "
        "Savolni o'zbekcha ham berish mumkin."
    ),
    examples=[
        "How many customers churned in Q1-2026?",
        "Churn ta'rifi nima?",
        "Qaysi regionda churn eng ko'p?",
        "Calculate 15% of 2600",
    ],
)

if __name__ == "__main__":
    demo.launch()
