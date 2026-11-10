# Solution Design: Solstice Learning Documentation Q&A

The two alternatives below address Elena Torres's request in
They are separate implementations,not stages of one pipeline. Setup commands are in the [README](README.md).

## 1. Keyword-based search

### Problem restated

Solstice Learning's new admins repeatedly ask Support questions already answered
in the documentation, including password resets, CSV export limits, and billing
cycles. They need a plain-English question interface that finds a trustworthy
source without requiring them to browse pages. Elena prioritizes an honest
"I don't have an answer" over an unsupported answer. This alternative provides
source-backed article lookup rather than generated explanations.

### Assumptions

- The six supplied English articles are authoritative and available to every
  intended user; account-specific data and document permissions are out of scope.
- Questions are independent, and a CLI is sufficient to demonstrate the workflow
  within the exercise's time budget. A customer-facing UI is future work.
- Returning a complete relevant article is acceptable for the baseline, even
  though it does not fully deliver the focused-answer experience Elena wants.
- The five examples are initial regression checks, not enough evidence to
  establish production accuracy or calibrate confidence.

### Proposed approach

The implementation in [docs_qa.py](docs_qa.py) reuses the starter-kit utilities.
It preserves each article as one chunk so limits and qualifications are not lost
through arbitrary character splitting. It normalizes the question, removes common
question words, and ranks articles by Jaccard overlap between unique query words
and article-content words.

A candidate must have a positive overlap score, contain at least 60% of the
remaining query words across its title and content, and match at least two words
(or the only word in a one-word query). The first qualifying candidate is returned
verbatim with its title and document ID; otherwise the tool abstains. These gates
are relevance heuristics, not a measured probability that the article answers
the question.

[test_docs_qa.py](test_docs_qa.py) checks the supplied questions, including the
undocumented Salesforce integration, plus empty input, absent evidence, and chunk
behavior. Matching an article does not establish that it answers every part of
a question.

### Trade-offs considered

- **Keywords versus semantic retrieval:** Keywords are deterministic, inspectable,
  local, and free of API costs, but miss synonyms and paraphrases. Embeddings add operational complexity that is not necessary to establish this small baseline.
- **Whole articles versus passages:** Whole articles preserve conditions such as
  reset-link expiry and export caps. They produce longer answers and can dilute
  matching scores; sentence-aware passages would improve focus.
- **Abstention versus coverage:** Matching gates aim to reduce unrelated answers,
  but may reject valid questions. They can still accept a related article that
  does not answer the question; verbatim output prevents invented wording, not
  incorrect relevance.
- **Single source versus synthesis:** One article keeps provenance simple but
  cannot combine information across documents.

### With more time, data, or budget

I would try giving specific answer from the passage instead of full content.

Also, would create a UI based solution and how additional documentes can be added by Elina/user/organization.

For a specific answer within an article, search smaller passages instead of ranking the whole article. Current prepare_chunks intentionally makes each article one chunk, so a match returns the full article.

A good approach will be:

Split each article into sentences rather than arbitrary character counts, so instructions aren’t cut off mid-sentence.
Group a few neighboring sentences together—or include one sentence of overlap—so important context stays with the answer.
Search those passages and return the best matching passage, along with its article title and ID. Your print_answer already prints the selected chunk’s text and source.
For example, if someone asks “How long are password reset links valid?”, the relevant passage in “Resetting Your Password” could be:

“Password reset links expire after 15 minutes. If yours has expired, go back to the login page and request a brand new reset link.”

Keeping those sentences together is useful: the first gives the duration, and the next explains what to do if the link expires.

## 2. LLM-powered alternative
(This is  alternatiov LLM based solution created for giving specific focused answer instead of returning full document content )

### Problem restated

The same support-deflection problem also calls for a concise answer, not another
page for an admin to read. This alternative uses an LLM to explain only the
relevant documented facts in simple English, while showing evidence. Elena's
preference for abstention remains more important than fluency or answer coverage.

### Assumptions

- Solstice approves sending the questions and supplied articles to the selected
  provider or gateway; credentials, model access, and any billing are available.
- All six short articles fit the selected model's context window. Larger or
  private document collections require a different retrieval/access design.
- The endpoint supports OpenAI-compatible Chat Completions and either strict
  JSON-schema output or JSON-object mode.
- A model instruction to abstain is useful but not a guarantee. Source-quote
  validation is an evidence check, not proof that generated claims are supported.

### Proposed approach

[docs_qa_llm.py](docs_qa_llm.py) sends all loaded articles with each question.
For six short articles this avoids keyword-retrieval misses without adding a
vector database. It is full-context answering, not a retrieval pipeline.

The prompt requests a brief, documentation-only answer preserving relevant
conditions and limits. It treats questions and articles as untrusted reference
data and requests a structured result: `supported`, `answer`, and evidence entries
with document IDs and exact quotes. Unsupported questions should receive the
standard no-answer message rather than an invented answer.

The program validates the structure, cited IDs, and verbatim occurrence of each
quote in its cited article before displaying the answer and evidence. Invalid
output, model refusals, incomplete responses, and API failures are explicit errors,
not falsely reported as documentation gaps. Endpoint, model, authentication, and
JSON mode are configurable; credentials come from environment variables.

[test_docs_qa_llm.py](test_docs_qa_llm.py) mocks API responses to check configuration,
requests, evidence validation, abstention handling, and failures. These tests do
not demonstrate live model accuracy or grounding quality.

### Trade-offs considered

- **LLM versus verbatim lookup:** The LLM can interpret paraphrases and combine
  documented facts into a focused answer, but introduces cost, latency,
  nondeterminism, and hallucination risk.
- **Full context versus retrieval:** Sending all articles is simple and avoids
  omitting the correct source at retrieval time. Cost and context use grow with
  the corpus; it is not a scalable long-term design.
- **Prompt controls versus guarantees:** Documentation-only instructions reduce
  risk but cannot ensure abstention or prevent prompt injection. This alternative
  needs evaluation before customer deployment.

### With more time, data, or budget



Use the same support-question evaluation set to compare both alternatives,
measuring factual support, preservation of limits, abstention, answer clarity,
latency, and per-question cost. Have Support review real model outputs, especially
partially answerable and adversarial questions. Set release criteria with Elena;
do not equate passing mocked tests with customer readiness.

As the corpus grows, add permission-aware hybrid retrieval, sentence-aware
passages with surrounding context, reranking, and explicit token budgets. Evaluate
claim-to-evidence verification and escalate uncertain cases to Support, while
recognizing that another model is not a correctness guarantee. With production
budget, add provider-approved data handling, managed secrets, bounded retries,
monitoring, document-version tracking, and a limited pilot measuring resolved
support questions. Keep the local keyword version as a baseline for comparison.
