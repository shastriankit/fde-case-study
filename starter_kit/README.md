# Starter Kit — Docs Q&A Assistant

## Contents

- `data/docs.json` — 6 synthetic documentation articles covering common product topics.
- `data/example_questions.json` — 5 example questions to test against, including one that isn't covered by any doc.
- `docs_qa_utils.py` — a small, optional Python utility module with basic chunking and keyword-matching helpers, provided as a rough starting point.

## A few notes

- You're free to use, modify, replace, or ignore `docs_qa_utils.py` entirely — it's not guaranteed to be complete, optimal, or bug-free.
- Not every question in `example_questions.json` has a good answer in the docs — take a look at how `expected_doc_id` is set for each one.

## Run the Q&A tool

Requires Python 3.8 or newer; no third-party packages or API keys are needed.
Run these commands from the repository root:

```powershell
python docs_qa.py
```

Enter questions at the prompt, then enter `exit` or `quit` to stop. You can also
ask a single question or specify another documentation file with the same schema:

```powershell
python docs_qa.py "What's the maximum number of rows I can export to CSV?"
python docs_qa.py --docs starter_kit\data\docs.json "How do I reset my password?"
```

The default data path is resolved relative to the script, not the working directory.
Answers contain the matching article verbatim, followed by its title and document ID.
If no sufficiently relevant article is found, the tool says it does not have an answer.

## Approach and limitations

The implementation reuses `load_docs`, `chunk_all_docs`, `normalize_text`, and
`find_best_chunks`. For these six short articles, it keeps each article intact to
avoid splitting words or omitting important qualifications. The utility's chunking
also now preserves trailing text and articles shorter than the chunk size.

Questions are normalized and common question words are removed. Articles are ranked
by keyword overlap. A candidate must cover at least 60% of the remaining query words
and share at least two words (or the only word in a one-word query). This threshold
is a heuristic, not a calibrated confidence score.

This is English keyword search, not semantic question answering. It can miss synonyms
and paraphrases, and a related article can pass the threshold without answering every
part of a question. Returning source text prevents invented answers, but does not
guarantee relevance. It returns one complete article rather than a concise generated
answer. Larger documents would need passage-level retrieval and a broader evaluation
set before production use.

## Tests

```powershell
python -m unittest test_docs_qa -v
```

Tests cover all five supplied questions (including the undocumented Salesforce
integration), verbatim source text, empty input, absent evidence, and chunk boundaries.
