import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

from docs_qa_llm import (
    API_URL, NO_ANSWER, answer_question, main, print_answer, validate_answer, validate_docs,
)


class DocsQALLMTests(unittest.TestCase):
    def setUp(self):
        self.docs = [{"doc_id": "D-01", "title": "Passwords",
                      "content": "Reset links expire after 15 minutes. Request a new link."}]
        self.answer = {
            "supported": True,
            "answer": "Request a new link. Links expire after 15 minutes.",
            "evidence": [{"doc_id": "D-01", "quote": self.docs[0]["content"]}],
        }

    def completion(self, result, finish_reason="stop"):
        return io.BytesIO(json.dumps({
            "choices": [{"finish_reason": finish_reason,
                         "message": {"content": json.dumps(result)}}],
        }).encode("utf-8"))

    @patch("docs_qa_llm.urlopen")
    def test_request_and_focused_answer(self, open_url):
        open_url.return_value = self.completion(self.answer)
        result = answer_question("My link expired. What now?", self.docs, "test-key", "test-model")
        self.assertEqual(result, self.answer)
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, API_URL)
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        payload = json.loads(request.data)
        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(json.loads(payload["messages"][1]["content"])["articles"], self.docs)
        self.assertTrue(payload["response_format"]["json_schema"]["strict"])
        self.assertEqual(open_url.call_args.kwargs["timeout"], 60)
        output = io.StringIO()
        with redirect_stdout(output):
            print_answer(result, self.docs)
        self.assertIn("Source: Passwords (D-01)", output.getvalue())
        self.assertIn("Evidence: Reset links expire", output.getvalue())

    @patch("docs_qa_llm.urlopen")
    def test_custom_endpoint_authentication(self, open_url):
        endpoint = "https://gateway.example.com/chat/completions?api-version=2024-10-21"
        for auth in ("bearer", "subscription-header", "subscription-query"):
            with self.subTest(auth=auth):
                open_url.return_value = self.completion(self.answer)
                answer_question("Reset?", self.docs, "key+/=&", "gpt-4o",
                                endpoint=endpoint, auth=auth)
                request = open_url.call_args.args[0]
                parts = urlsplit(request.full_url)
                query = parse_qs(parts.query)
                self.assertEqual(parts.hostname, "gateway.example.com")
                self.assertEqual(query["api-version"], ["2024-10-21"])
                self.assertEqual(json.loads(request.data)["model"], "gpt-4o")
                if auth == "bearer":
                    self.assertEqual(request.get_header("Authorization"), "Bearer key+/=&")
                elif auth == "subscription-header":
                    self.assertEqual(request.get_header("Ocp-apim-subscription-key"), "key+/=&")
                    self.assertIsNone(request.get_header("Authorization"))
                else:
                    self.assertEqual(query["subscription-key"], ["key+/=&"])
                    self.assertIsNone(request.get_header("Authorization"))
                if auth != "subscription-query":
                    self.assertNotIn("subscription-key", query)

    @patch("docs_qa_llm.urlopen")
    def test_json_mode_still_validates_evidence(self, open_url):
        open_url.return_value = self.completion(self.answer)
        answer_question("Reset?", self.docs, "key", "model", response_format="json_object")
        payload = json.loads(open_url.call_args.args[0].data)
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertIn('"evidence"', payload["messages"][0]["content"])
        invalid = {**self.answer, "evidence": [{"doc_id": "D-01", "quote": "Invented"}]}
        open_url.return_value = self.completion(invalid)
        with self.assertRaises(RuntimeError):
            answer_question("Reset?", self.docs, "key", "model", response_format="json_object")

    @patch("docs_qa_llm.urlopen")
    def test_invalid_configuration_does_not_send_requests(self, open_url):
        configurations = [
            {"endpoint": "http://gateway.example.com/chat"},
            {"endpoint": "https://user:password@gateway.example.com/chat"},
            {"endpoint": "https://gateway.example.com/chat#fragment"},
            {"endpoint": "https://gateway.example.com/chat?subscription-key=secret"},
            {"endpoint": "not a URL"}, {"auth": "unknown"}, {"response_format": "text"},
        ]
        for configuration in configurations:
            with self.subTest(configuration=configuration), self.assertRaises(ValueError):
                answer_question("Reset?", self.docs, "key", "model", **configuration)
        open_url.assert_not_called()

    @patch("docs_qa_llm.answer_question")
    def test_cli_environment_and_overrides(self, answer):
        environment = {
            "LLM_ENDPOINT": "https://gateway.example.com/chat",
            "LLM_API_KEY": "gateway-key", "LLM_MODEL": "gpt-4o",
            "LLM_AUTH": "subscription-query", "LLM_RESPONSE_FORMAT": "json_object",
        }
        answer.return_value = {"supported": False, "answer": NO_ANSWER, "evidence": []}
        with patch.dict("os.environ", environment, clear=True), redirect_stdout(io.StringIO()):
            with patch("sys.argv", ["docs_qa_llm.py", "Salesforce?"]):
                main()
            args, kwargs = answer.call_args
            self.assertEqual(args[2:], ("gateway-key", "gpt-4o"))
            self.assertEqual(kwargs, {"endpoint": environment["LLM_ENDPOINT"],
                                     "auth": "subscription-query", "response_format": "json_object"})
            with patch("sys.argv", [
                "docs_qa_llm.py", "--endpoint", "https://other.example.com/chat",
                "--auth", "subscription-header", "--model", "other-model",
                "--response-format", "json_schema", "Salesforce?",
            ]):
                main()
            args, kwargs = answer.call_args
            self.assertEqual(args[3], "other-model")
            self.assertEqual(kwargs, {"endpoint": "https://other.example.com/chat",
                                     "auth": "subscription-header", "response_format": "json_schema"})

    @patch("docs_qa_llm.answer_question")
    def test_legacy_openai_environment(self, answer):
        answer.return_value = {"supported": False, "answer": NO_ANSWER, "evidence": []}
        with patch.dict("os.environ", {"OPENAI_API_KEY": "legacy-key",
                                      "OPENAI_MODEL": "legacy-model"}, clear=True):
            with patch("sys.argv", ["docs_qa_llm.py", "Salesforce?"]), redirect_stdout(io.StringIO()):
                main()
        args, kwargs = answer.call_args
        self.assertEqual(args[2:], ("legacy-key", "legacy-model"))
        self.assertEqual(kwargs, {"endpoint": API_URL, "auth": "bearer",
                                 "response_format": "json_schema"})

    @patch("docs_qa_llm.urlopen")
    def test_error_message_does_not_expose_query_credentials(self, open_url):
        open_url.side_effect = HTTPError(
            "https://gateway.example.com/chat?subscription-key=private-key",
            401, "private-key", {}, None,
        )
        with self.assertRaises(RuntimeError) as caught:
            answer_question("Reset?", self.docs, "private-key", "model",
                            endpoint="https://gateway.example.com/chat",
                            auth="subscription-query")
        self.assertIn("401", str(caught.exception))
        self.assertNotIn("private-key", str(caught.exception))

    @patch("docs_qa_llm.urlopen")
    def test_unsupported_question(self, open_url):
        expected = {"supported": False, "answer": NO_ANSWER, "evidence": []}
        open_url.return_value = self.completion(expected)
        self.assertEqual(answer_question("Salesforce?", self.docs, "key", "model"), expected)

    def test_rejects_invalid_evidence_and_answers(self):
        invalid_results = [
            {**self.answer, "evidence": []},
            {**self.answer, "evidence": [{"doc_id": "unknown", "quote": "Request a new link."}]},
            {**self.answer, "evidence": [{"doc_id": "D-01", "quote": "Links never expire."}]},
            {**self.answer, "supported": False},
            {**self.answer, "answer": ""},
            {**self.answer, "supported": "true"},
            {**self.answer, "evidence": [None]},
            [],
        ]
        for result in invalid_results:
            with self.subTest(result=result), self.assertRaises(ValueError):
                validate_answer(result, self.docs)

    @patch("docs_qa_llm.urlopen")
    def test_api_errors_are_not_answers(self, open_url):
        for error in (HTTPError("https://example.com", 429, "Limit", {}, None),
                      URLError("offline"), TimeoutError()):
            with self.subTest(error=type(error).__name__):
                open_url.side_effect = error
                with self.assertRaises(RuntimeError):
                    answer_question("Reset?", self.docs, "key", "model")

    @patch("docs_qa_llm.urlopen")
    def test_rejects_malformed_refused_and_incomplete_responses(self, open_url):
        responses = [
            b"not json", b"{}", b'{"choices": []}',
            b'{"choices": [{"message": {"refusal": "Cannot comply"}}]}',
        ]
        for body in responses:
            with self.subTest(body=body), self.assertRaises(RuntimeError):
                open_url.return_value = io.BytesIO(body)
                answer_question("Reset?", self.docs, "key", "model")
        open_url.return_value = self.completion(self.answer, finish_reason="length")
        with self.assertRaises(RuntimeError):
            answer_question("Reset?", self.docs, "key", "model")

    @patch("docs_qa_llm.urlopen")
    def test_invalid_inputs_do_not_call_api(self, open_url):
        for question, docs, key, model in [
            (" ", self.docs, "key", "model"), ("Reset?", [], "key", "model"),
            ("Reset?", self.docs, "", "model"), ("Reset?", self.docs, "key", ""),
        ]:
            with self.subTest(question=question, docs=docs, model=model):
                with self.assertRaises(ValueError):
                    answer_question(question, docs, key, model)
        open_url.assert_not_called()
        for docs in ([self.docs[0], self.docs[0]], [{}], "not a list"):
            with self.subTest(docs=docs), self.assertRaises(ValueError):
                validate_docs(docs)


if __name__ == "__main__":
    unittest.main()
