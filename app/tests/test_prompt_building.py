import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


def _install_dependency_stubs() -> None:
    if "qdrant_client" not in sys.modules:
        qdrant_client = types.ModuleType("qdrant_client")

        class DummyQdrantClient:
            def __init__(self, *args, **kwargs):
                pass

            def close(self):
                pass

        qdrant_client.QdrantClient = DummyQdrantClient
        sys.modules["qdrant_client"] = qdrant_client

    if "qdrant_client.models" not in sys.modules:
        qdrant_models = types.ModuleType("qdrant_client.models")

        class DummyCollectionInfo:
            pass

        class DummyPointStruct:
            def __init__(self, *args, **kwargs):
                pass

        class DummyVectorParams:
            def __init__(self, *args, **kwargs):
                self.size = kwargs.get("size")

        qdrant_models.CollectionInfo = DummyCollectionInfo
        qdrant_models.Distance = types.SimpleNamespace(COSINE="cosine")
        qdrant_models.PointStruct = DummyPointStruct
        qdrant_models.VectorParams = DummyVectorParams
        sys.modules["qdrant_client.models"] = qdrant_models

    if "fastembed" not in sys.modules:
        fastembed = types.ModuleType("fastembed")

        class DummyTextEmbedding:
            def __init__(self, *args, **kwargs):
                self.model = types.SimpleNamespace(_model_dir=".")

            @staticmethod
            def list_supported_models():
                return []

            def embed(self, texts):
                for _ in texts:
                    yield [0.0, 0.0, 0.0]

        fastembed.TextEmbedding = DummyTextEmbedding
        sys.modules["fastembed"] = fastembed


_install_dependency_stubs()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import apiAsk  # noqa: E402
from backend.apiAsk import ParsedDocument  # noqa: E402
from backend.chat_history import ChatHistoryStore  # noqa: E402
from backend.devices_repo import DevicesRepository  # noqa: E402
from backend.schemas import ChatMessage, HistoryDocument  # noqa: E402


class PromptBuildingTests(unittest.TestCase):
    def test_invalid_model_output_detects_known_garbage_fragments(self):
        self.assertTrue(apiAsk.is_invalid_model_output("Hub heeft geen tools toegewezen voor deze taak."))

    def test_invalid_model_output_detects_corrupted_unicode_stream(self):
        corrupted = "���⸮⸮⸮⸮߷߷߷۞۞۞���⸮⸮⸮⸮߷߷߷۞۞۞"
        self.assertTrue(apiAsk.is_invalid_model_output(corrupted))

    def test_invalid_model_output_keeps_normal_dutch_sentence_valid(self):
        valid = "Ik zie geen directe fout in je vraag. Kun je het exacte antwoord van het model delen?"
        self.assertFalse(apiAsk.is_invalid_model_output(valid))

    def test_all_prompt_templates_start_with_required_prefix(self):
        required_prefix = "Je bent een behulpzame assistent."
        template_paths = [apiAsk.PROMPT_TEMPLATE_PATH, *sorted(apiAsk.PROMPT_TEMPLATE_DIR.glob("*.txt"))]

        for template_path in template_paths:
            text = Path(template_path).read_text(encoding="utf-8")
            self.assertTrue(text.startswith(required_prefix), template_path.name)

    def test_augmented_prompt_places_template_first_and_includes_attachments(self):
        documents = [
            ParsedDocument(
                filename="contract.pdf",
                file_type="pdf",
                text="Artikel 1\nBetaling binnen 14 dagen",
                source_bytes=2048,
                truncated=True,
            )
        ]

        with patch.object(
            apiAsk,
            "_gather_context_with_details",
            return_value=([], {"devices": [], "knowledge": []}),
        ):
            prompt, details = apiAsk.build_augmented_prompt_with_details(
                "Wat staat er in het contract?",
                images_count=2,
                documents=documents,
                mode="Developer",
            )

        self.assertTrue(prompt.startswith("Je bent een behulpzame assistent."))
        self.assertIn("> bijlagen:", prompt)
        self.assertIn("Er zijn 2 afbeeldingen meegestuurd.", prompt)
        self.assertIn("- Document 1: contract.pdf [pdf]", prompt)
        self.assertIn("Kenmerken: 34 tekens uit 2048 bytes; ingekort.", prompt)
        self.assertIn("Geextracteerde inhoud:", prompt)
        self.assertIn("Artikel 1", prompt)
        self.assertTrue(prompt.rstrip().endswith("Huidige vraag: Wat staat er in het contract?"))
        self.assertEqual(
            details["documents"],
            [
                {
                    "filename": "contract.pdf",
                    "file_type": "pdf",
                    "bytes": 2048,
                    "chars": 34,
                    "truncated": True,
                }
            ],
        )

    def test_format_history_lines_include_document_context(self):
        history = [
            ChatMessage(
                role="user",
                content="Bekijk het eerder gedeelde contract.",
                images=["img-a"],
                documents=[
                    HistoryDocument(
                        filename="contract.pdf",
                        file_type="pdf",
                        text="Artikel 1\nBetaling binnen 14 dagen",
                        source_bytes=2048,
                        truncated=True,
                    )
                ],
            )
        ]

        lines = apiAsk._format_history_lines(history)

        self.assertEqual(len(lines), 1)
        self.assertIn("[Afbeeldingen: 1]", lines[0])
        self.assertIn("[Documenten: 1]", lines[0])
        self.assertIn("contract.pdf [pdf]", lines[0])
        self.assertIn("Betaling binnen 14 dagen", lines[0])

    def test_collect_prompt_images_includes_recent_history_images(self):
        history = [
            ChatMessage(role="user", content="eerste", images=["img-1", "img-2"]),
            ChatMessage(role="assistant", content="antwoord"),
            ChatMessage(role="user", content="tweede", images=["img-2", "img-3"]),
        ]

        images = apiAsk.collect_prompt_images(history, current_images=["img-3", "img-4"])

        self.assertEqual(images, ["img-1", "img-2", "img-3", "img-4"])

    def test_chat_history_store_preserves_attachment_only_messages_after_summary(self):
        store = ChatHistoryStore(max_items=5)
        docs = [
            HistoryDocument(
                filename="notitie.txt",
                file_type="txt",
                text="Belangrijke afspraak",
                source_bytes=128,
                truncated=False,
            )
        ]

        store.append("sessie", "user", "", images=["img-1"], documents=docs)
        snapshot = store.snapshot_pending()[0]
        applied = store.apply_summary("sessie", "samenvatting", snapshot.updated_at, snapshot.summarized_at)

        self.assertTrue(applied)
        history = store.get("sessie")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[1].images, ["img-1"])
        self.assertEqual(history[1].documents[0].filename, "notitie.txt")

    def test_device_search_returns_empty_when_embeddings_are_unavailable(self):
        repo = DevicesRepository()

        with patch("backend.devices_repo.embed_text", side_effect=RuntimeError("missing model")):
            self.assertEqual(repo.search_devices("waar is mijn apparaat?"), [])

    def test_rag_min_context_score_default_matches_current_embeddings(self):
        self.assertEqual(apiAsk.MIN_CONTEXT_SCORE, 0.30)

    def test_float_env_uses_override_and_ignores_invalid_values(self):
        with patch.dict("os.environ", {"RAG_MIN_CONTEXT_SCORE": "0.25"}):
            self.assertEqual(apiAsk._float_env("RAG_MIN_CONTEXT_SCORE", 0.30), 0.25)

        with patch.dict("os.environ", {"RAG_MIN_CONTEXT_SCORE": "nope"}):
            self.assertEqual(apiAsk._float_env("RAG_MIN_CONTEXT_SCORE", 0.30), 0.30)

    def test_augmented_prompt_includes_web_search_block_when_results_provided(self):
        from backend.web_search import WebSearchResult

        results = [
            WebSearchResult(
                title="Voorbeeld bron",
                url="https://example.com/article",
                snippet="Korte samenvatting van de pagina.",
                engine="duckduckgo",
            )
        ]

        with patch.object(
            apiAsk,
            "_gather_context_with_details",
            return_value=([], {"devices": [], "knowledge": []}),
        ):
            prompt, _ = apiAsk.build_augmented_prompt_with_details(
                "Wat zijn de laatste ontwikkelingen?",
                web_results=results,
            )

        self.assertIn("> web search:", prompt)
        self.assertIn("Voorbeeld bron", prompt)
        self.assertIn("https://example.com/article", prompt)
        self.assertTrue(prompt.rstrip().endswith("Huidige vraag: Wat zijn de laatste ontwikkelingen?"))

    def test_augmented_prompt_omits_web_search_block_when_no_results(self):
        with patch.object(
            apiAsk,
            "_gather_context_with_details",
            return_value=([], {"devices": [], "knowledge": []}),
        ):
            prompt, _ = apiAsk.build_augmented_prompt_with_details(
                "Wat zijn de laatste ontwikkelingen?",
                web_results=[],
            )

        self.assertNotIn("> web search:", prompt)


if __name__ == "__main__":
    unittest.main()
