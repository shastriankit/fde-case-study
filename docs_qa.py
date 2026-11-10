"""Command-line documentation search using the starter-kit utilities."""

import argparse
from pathlib import Path

from starter_kit.docs_qa_utils import chunk_all_docs, find_best_chunks, load_docs, normalize_text


DEFAULT_DOCS_PATH = Path(__file__).resolve().parent / "starter_kit" / "data" / "docs.json"
NO_ANSWER = "I don't have an answer for that in the documentation."
STOP_WORDS = set(
    "a an and are as at be before by can could do does for from have how i in "
    "is it me my of on or that the there this to use was what when where which "
    "who why will with would you your s t".split()
)
MIN_QUERY_COVERAGE = 0.6


def prepare_chunks(docs):
    """Keep each article intact so the answer includes all qualifications."""
    chunk_size = max((len(doc["content"]) for doc in docs), default=1)
    return chunk_all_docs(docs, chunk_size=max(1, chunk_size))


def answer_question(question, chunks):
    """Return a matching source article, or None for insufficient evidence."""
    query_tokens = set(normalize_text(question)) - STOP_WORDS
    if not query_tokens:
        return None

    matches = find_best_chunks(" ".join(sorted(query_tokens)), chunks, top_n=len(chunks))
    for score, chunk in matches:
        source_tokens = set(normalize_text(chunk["title"] + " " + chunk["text"]))
        shared_tokens = query_tokens & source_tokens
        coverage = len(shared_tokens) / len(query_tokens)
        if (score > 0 and coverage >= MIN_QUERY_COVERAGE
                and len(shared_tokens) >= min(2, len(query_tokens))):
            return chunk
    return None


def print_answer(question, chunks):
    answer = answer_question(question, chunks)
    if answer is None:
        print(NO_ANSWER)
    else:
        print(answer["text"])
        print(f"\nSource: {answer['title']} ({answer['doc_id']})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", help="Question to ask the documentation")
    parser.add_argument("--docs", type=Path, default=DEFAULT_DOCS_PATH)
    args = parser.parse_args()
    try:
        chunks = prepare_chunks(load_docs(args.docs))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Unable to load documentation: {error}\n")

    if args.question is not None:
        print_answer(args.question, chunks)
        return

    print("Ask a documentation question. Type 'exit' or 'quit' to stop.")
    while True:
        try:
            question = input("\nQuestion: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in {"exit", "quit"}:
            break
        print_answer(question, chunks)


if __name__ == "__main__":
    main()