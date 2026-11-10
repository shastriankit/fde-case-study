# Documentation Q&A Assistant

Two command-line alternatives answer questions using the six synthetic articles in
[`starter_kit/data/docs.json`](starter_kit/data/docs.json). Both require Python 3.8
or newer and use only the Python standard library: no package installation is needed.
Run the PowerShell commands below from the repository root.

## 1. Keyword-based search - `docs_qa.py`

[`docs_qa.py`](docs_qa.py) runs entirely locally, with no API key or network access.
It returns a matching article verbatim, followed by its title and document ID.

### How it works

1. Load the articles and keep each article as one searchable chunk.
2. Normalize the question and remove common question words.
3. Rank articles by Jaccard keyword overlap between the remaining question words
   and the article content.
4. Select the first ranked article that has a positive score, covers at least 60%
   of the question's remaining unique words across its title and content, and
   shares at least two words (or the only word in a one-word query).
5. If none qualify, print:
   `I don't have an answer for that in the documentation.`

The score and coverage threshold are heuristics, not probabilities or calibrated
confidence scores.

### How to run

Ask a single question:

```powershell
python docs_qa.py "What's the maximum number of rows I can export to CSV?"
```

Start an interactive session:

```powershell
python docs_qa.py
```

Type `exit` or `quit` to stop. Questions are processed independently.

Select another documentation file:

```powershell
python docs_qa.py --docs starter_kit\data\docs.json "How do I reset my password?"
```

The default data path is resolved relative to the script, not the current working
directory. A custom file must follow the existing JSON schema: a top-level `docs`
array containing articles with `doc_id`, `title`, and `content` strings.

### Tests

```powershell
python -m unittest test_docs_qa -v
```

[`test_docs_qa.py`](test_docs_qa.py) checks all five supplied example questions,
including an undocumented topic, full-article preservation, empty input, absent
evidence, and chunk boundaries/invalid sizes.

### Gaps and known limitations

- **No semantic understanding:** Synonyms, paraphrases, spelling errors, and
  different word forms may prevent a relevant article from matching.
- **Whole-article answers:** It does not extract a focused passage or summarize.
  Keeping articles intact preserves qualifications but can make answers lengthy.
- **One source only:** It cannot combine facts across multiple articles.
- **Relevance is not guaranteed:** A related article can pass the thresholds
  without answering the question. Returning source text avoids generated facts,
  but does not prove that the selected article answers every part of a question.
- **English-oriented matching:** Normalization and stop words are designed for
  English, not multilingual search.
- **Limited scale and evaluation:** Every question scores every article. There
  is no search index or broad evaluation set; larger collections need better
  retrieval, passage handling, and threshold evaluation.

## 2. LLM-powered alternative - `docs_qa_llm.py`

[`docs_qa_llm.py`](docs_qa_llm.py) asks an OpenAI-compatible Chat Completions model
to write a focused answer in simple English. It needs network access, a compatible
endpoint, and a valid credential with model access and any required billing.

### How it works

1. Load and validate the documentation, including required fields and unique IDs.
2. Send the question and **all loaded articles** to the configured endpoint.
   There is no keyword retrieval, embedding model, or vector database.
3. Instruct the model to answer only from the documentation, retain relevant
   conditions and limits, cite sources, and provide exact evidence quotes.
4. Validate the returned JSON structure, document IDs, and that each quote occurs
   verbatim in its cited article.
5. Print the focused answer, source titles/IDs, and evidence. For an unsupported
   question, the model is instructed to return the same no-answer message as the
   keyword version.

API failures, refusals, incomplete responses, and invalid answers are reported as
errors with a nonzero exit status, not presented as missing documentation.

### How to run with OpenAI

In a fresh PowerShell terminal, configure the key and ask a question:

```powershell
$env:OPENAI_API_KEY = "<your-api-key>"
python docs_qa_llm.py "My password reset link expired. What should I do?"
```

The default endpoint is OpenAI's public Chat Completions API, with bearer
authentication and model `gpt-4o-mini`.

Start an interactive session:

```powershell
python docs_qa_llm.py
```

Type `exit` or `quit` to stop. No chat history is sent; each question is independent.

### How to run with a custom endpoint

For the gateway using a `subscription-key` query parameter:

```powershell
$env:LLM_ENDPOINT = "https://routeopenai.azure-api.net/base/openai/v1/chat/completions"
$env:LLM_API_KEY = "<your-gateway-key>"
$env:LLM_MODEL = "gpt-4o"
$env:LLM_AUTH = "subscription-query"
python docs_qa_llm.py "What are the Growth plan API limits?"
```

Keep the key out of `LLM_ENDPOINT`; the script adds and URL-encodes the
`subscription-key` parameter at request time. Query keys can appear in gateway
logs. If the gateway supports the standard Azure API Management subscription
header, prefer:

```powershell
$env:LLM_AUTH = "subscription-header"
```

Confirm the required authentication method with your gateway administrator:

| Authentication mode | How the key is sent |
|---|---|
| `bearer` | Authorization header using the Bearer scheme |
| `subscription-header` | `Ocp-Apim-Subscription-Key` header |
| `subscription-query` | `subscription-key` query parameter |

VS Code references such as `${input:chat.lm.secret...}` cannot be resolved by
Python. Supply the actual gateway key through the environment variable instead.

### Configuration and compatibility

| Environment variable | CLI override | Default |
|---|---|---|
| `LLM_ENDPOINT` | `--endpoint` | `https://api.openai.com/v1/chat/completions` |
| `LLM_MODEL` | `--model` | `OPENAI_MODEL`, otherwise `gpt-4o-mini` |
| `LLM_AUTH` | `--auth` | `bearer` |
| `LLM_RESPONSE_FORMAT` | `--response-format` | `json_schema` |
| `LLM_API_KEY` | None | `OPENAI_API_KEY` |

CLI options take precedence over their corresponding environment variables.
`LLM_API_KEY` and `LLM_MODEL`, when set, take precedence over their `OPENAI_*`
fallbacks. Clear stale `LLM_*` settings or use a fresh terminal when switching
back to the public OpenAI API.

Endpoints must use HTTPS. Non-secret query parameters such as `api-version` are
preserved. The endpoint must support either strict JSON-schema outputs or
JSON-object mode. If it rejects `json_schema` but supports JSON-object mode:

```powershell
$env:LLM_RESPONSE_FORMAT = "json_object"
python docs_qa_llm.py "When do password reset links expire?"
```

There is no automatic retry with weaker formatting. Local answer and evidence
validation stays enabled in both modes.

Select another documentation file and override the model:

```powershell
python docs_qa_llm.py --docs starter_kit\data\docs.json --model gpt-4o "How do I reset my password?"
```

Custom files use the same schema as the keyword version and must contain at least
one article, nonempty string fields, and unique document IDs.

### Tests

```powershell
python -m unittest test_docs_qa_llm -v
```

[`test_docs_qa_llm.py`](test_docs_qa_llm.py) uses mocked HTTP responses. It checks
request construction, authentication modes, configuration precedence, JSON modes,
citations, abstention handling, and API/validation errors. Tests need no API key,
send no data externally, and incur no API charges.

To run both alternatives' tests:

```powershell
python -m unittest test_docs_qa test_docs_qa_llm -v
```

### Gaps and known limitations

- **Grounding is not guaranteed:** A valid quote proves that the quote exists,
  not that every generated claim follows from it. The model can still invent,
  misinterpret, or omit facts and qualifications.
- **Prompt injection remains possible:** Instructions treat questions and
  articles as untrusted data, but do not guarantee resistance to malicious input.
- **No live quality evaluation:** Mocked tests verify application behavior, not
  actual model accuracy, simple-English quality, or refusal reliability. Evaluate
  real outputs against expected answers before relying on them.
- **Small-dataset design:** All articles are sent on every request. There is no
  retrieval, token-budget enforcement, or automatic context-size management.
  Larger collections can exceed context limits or become expensive.
- **Cost, privacy, and latency:** Questions and articles leave the machine and may
  incur provider charges. Use only data approved for the configured service.
  Keep keys out of source control and rotate exposed credentials.
- **Endpoint compatibility:** Only OpenAI-compatible Chat Completions with the
  supported JSON modes is implemented. Authentication supports one key through
  one method; gateways needing multiple credentials require additional integration.
- **No retries, streaming, or memory:** Requests use a 60-second network timeout,
  do not retry automatically, and display answers only after receiving the response.
  Follow-up questions cannot depend on earlier turns.
- **Strict evidence checks:** Harmless changes to a quote's whitespace or
  punctuation cause validation failure. JSON-object mode can produce more
  schema errors because the provider does not enforce the answer schema.
