import json
import unittest

from docs_qa import DEFAULT_DOCS_PATH, answer_question, prepare_chunks
from starter_kit.docs_qa_utils import chunk_text, load_docs


class DocsQATests(unittest.TestCase):
    def test_example_questions(self):
        chunks = prepare_chunks(load_docs(DEFAULT_DOCS_PATH))
        examples_path = DEFAULT_DOCS_PATH.with_name("example_questions.json")
        examples = json.loads(examples_path.read_text(encoding="utf-8"))
        for example in examples["example_questions"]:
            with self.subTest(question_id=example["question_id"]):
                answer = answer_question(example["question"], chunks)
                self.assertEqual(
                    answer["doc_id"] if answer else None,
                    example["expected_doc_id"],
                )
                if answer:
                    source = next(doc for doc in load_docs(DEFAULT_DOCS_PATH)
                                  if doc["doc_id"] == answer["doc_id"])
                    self.assertEqual(answer["text"], source["content"])

    def test_no_evidence(self):
        chunks = prepare_chunks(load_docs(DEFAULT_DOCS_PATH))
        for question in ("", "   ", "What can I do?", "quantum teleportation"):
            with self.subTest(question=question):
                self.assertIsNone(answer_question(question, chunks))
        self.assertIsNone(answer_question("reset password", prepare_chunks([])))

    def test_chunking_preserves_all_text(self):
        self.assertEqual(chunk_text("abcdefg", 3), ["abc", "def", "g"])
        self.assertEqual(chunk_text("ab", 3), ["ab"])
        self.assertEqual(chunk_text("", 3), [])
        self.assertEqual(chunk_text("abcdef", 3), ["abc", "def"])

    def test_invalid_chunk_size(self):
        for chunk_size in (0, -1):
            with self.subTest(chunk_size=chunk_size):
                with self.assertRaises(ValueError):
                    chunk_text("example", chunk_size)


if __name__ == "__main__":
    unittest.main()