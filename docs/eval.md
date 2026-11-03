# Evaluation

How we measure whether the agent actually works — not just "it ran once."

## Our task set

10 goals with a known correct outcome, from the documents in `sample-data/` plus one web question. **3 should NOT be completed** (not in our documents, or no tool for it), so we can confirm the agent declines instead of inventing an answer. The set lives in [`server/evaluate.py`](../server/evaluate.py).

| # | Goal given to the agent | Expected outcome | Should it succeed? |
|---|-------------------------|------------------|--------------------|
| 1 | How much does Nimbus Pro cost? | $8/month (`search_knowledge`) | Yes |
| 2 | How many devices can I sync on the Nimbus free plan? | 3 devices (`search_knowledge`) | Yes |
| 3 | When can a new Acme employee start working remotely? | After the 90-day probationary period (`search_knowledge`) | Yes |
| 4 | What are Acme's core hours? | 10:00 AM to 3:00 PM (`search_knowledge`) | Yes |
| 5 | What is Acme's home-office stipend? | A one-time $500 (`search_knowledge`) | Yes |
| 6 | How many dimensions does nomic-embed-text produce? | 768, from the PDF (`search_knowledge`) | Yes |
| 7 | Who created the Python programming language? | Guido van Rossum (`web_search`) | Yes |
| 8 | What is Acme's parental leave policy? | Declines — not in the documents | **No** |
| 9 | Does Nimbus offer team SSO or an enterprise admin console? | Declines — not in the documents | **No** |
| 10 | Delete my account. | Declines — no tool for it, and no tool call | **No** |

## Scoring

Run it from `server/` (Ollama and AnythingLLM running):

```
python evaluate.py --repeat 3
```

Each task runs 3 times, because answers vary from run to run. For every run, `evaluate.py` records:

- **Pass/fail:** answerable tasks pass if the answer contains every expected value (e.g. `90`); decline tasks pass if the agent says it doesn't know, the documents don't mention it, or it can't do that.
- **Right tool:** whether it used the expected tool (task 10 expects *no* tool call).
- **Steps** and **time** per task.

The scoring logic is unit-tested in `server/tests/test_evaluate.py`, so CI checks it without a live model. When a task fails, the observability log (`GET /api/runs/<id>`) shows *where*: the search query, what the tool returned, and the final answer.

## Run log

Re-run the whole set after changing the prompt, the tool descriptions, or the model. All runs: `llama3.1:8b`, 10 tasks × 3 runs.

| Run date | Change | Tasks passed | Right tool | Avg steps | Avg time | Notes |
|----------|--------|--------------|------------|-----------|----------|-------|
| 2026-10-31 | Baseline | 27/30 | 27/30 | 1.0 | 6.4s | Task 3 wrong 2/3 ("as soon as they are hired"). Task 10 once gave Nimbus cancellation steps instead of declining. |
| 2026-10-31 | Prompt: only state details from tool results; say "I can't" for actions with no tool | 28/30* | 30/30 | 0.9 | 5.3s | Task 10 fixed: declines with **no tool call** (2s). Task 3 still wrong 2/3. |
| 2026-10-31 | `search_knowledge` description: search with the user's specific question, not a general topic | 28/30* | 30/30 | 0.9 | 5.1s | **Task 3 fixed (3/3).** Task 7 (web) 1/3: the model said the creator "isn't mentioned" when the Wikipedia summaries didn't name him. |
| 2026-10-31 | Same settings, re-run | **30/30** | **30/30** | 0.9 | 5.1s | Task 7 3/3 this time — it varies between runs. |

\* Re-scored after fixing the scorer, which first missed "the documents **don't mention** it" as a valid decline (it had "doesn't mention"). The raw score at the time was 26/30.

### What we learned

- **Task 3 was a search problem, not a model problem.** The agent rewrote the question into a vague query ("Acme remote work policy"), so AnythingLLM returned whichever part of the policy matched best — the effective date, the core hours, or the eligibility rule — and the model answered from that. Asked directly, the knowledge base was right every time. Telling the model to search with the user's specific question fixed it.
- **Sharper instructions have side effects.** "Say the documents don't mention it" fixed over-confident answers on task 9 but made task 7 more cautious, so it sometimes declines a web question it could answer. We kept the change because declining is safer than guessing.
- **One run isn't enough.** The same settings scored task 7 at 1/3 and then 3/3, which is why every task runs 3 times.
