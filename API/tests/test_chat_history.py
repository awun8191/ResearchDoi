import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.models.chat import ChatMessageRequest
from src.routers import chat as chat_router
from src.service import gemini


class TestChatApi(unittest.IsolatedAsyncioTestCase):
    async def test_delete_session_endpoint_deletes_chat_thread(self):
        fake_delete = AsyncMock(return_value=None)

        with patch("src.service.gemini.delete_chat_session", new=fake_delete):
            await chat_router.delete_session(
                project_id="project-1",
                chat_id="chat-123",
                user={"uid": "dev-user"},
            )

        fake_delete.assert_awaited_once_with(
            uid="dev-user",
            project_id="project-1",
            chat_id="chat-123",
        )

    async def test_list_sessions_endpoint_returns_chat_threads(self):
        fake_sessions = [
            {
                "chat_id": "chat-a",
                "title": "Literature Review",
                "created_at": "2026-03-01T00:00:00+00:00",
                "updated_at": "2026-03-01T00:10:00+00:00",
            }
        ]
        fake_list = AsyncMock(return_value=fake_sessions)

        with patch("src.service.gemini.list_chat_sessions", new=fake_list):
            resp = await chat_router.list_sessions(
                project_id="project-1",
                user={"uid": "dev-user"},
            )

        self.assertEqual([s.model_dump() for s in resp.sessions], fake_sessions)
        fake_list.assert_awaited_once_with(uid="dev-user", project_id="project-1")

    async def test_send_message_endpoint_passes_data_and_returns_reply(self):
        fake_send_message = AsyncMock(return_value={
            "reply": "mock-reply",
            "chat_id": "default",
            "title": "hello",
        })

        with patch("src.service.gemini.send_message", new=fake_send_message):
            resp = await chat_router.send_message(
                body=ChatMessageRequest(
                    project_id="project-1",
                    message="hello",
                    system_prompt="be concise",
                ),
                user={"uid": "dev-user"},
            )

        self.assertEqual(resp.reply, "mock-reply")
        self.assertEqual(resp.chat_id, "default")
        self.assertEqual(resp.title, "hello")
        fake_send_message.assert_awaited_once_with(
            uid="dev-user",
            project_id="project-1",
            chat_id="default",
            user_text="hello",
            chat_title=None,
            system_prompt="be concise",
        )

    async def test_get_session_endpoint_returns_history(self):
        fake_history = [
            {
                "id": "m1",
                "role": "user",
                "text": "hi",
                "timestamp": "2026-03-01T00:00:00+00:00",
            },
            {
                "id": "m2",
                "role": "model",
                "text": "hello",
                "timestamp": "2026-03-01T00:00:01+00:00",
            },
        ]

        fake_get_history = AsyncMock(return_value={
            "chat_id": "default",
            "title": "My Chat",
            "messages": fake_history,
        })

        with patch("src.service.gemini.get_history_firestore", new=fake_get_history):
            resp = await chat_router.get_session(
                project_id="project-1",
                user={"uid": "dev-user"},
            )

        self.assertEqual(resp.chat_id, "default")
        self.assertEqual(resp.title, "My Chat")
        self.assertEqual([m.model_dump() for m in resp.messages], fake_history)
        fake_get_history.assert_awaited_once_with(uid="dev-user", project_id="project-1", chat_id="default")


class TestGeminiPersistence(unittest.TestCase):
    def test_save_turn_uses_atomic_batch_with_stable_ordering(self):
        class FakeBatch:
            def __init__(self):
                self.ops = []
                self.committed = False

            def set(self, ref, data):
                self.ops.append((ref, data))

            def commit(self):
                self.committed = True

        class FakeCollection:
            def document(self, doc_id: str):
                return f"ref:{doc_id}"

        fake_batch = FakeBatch()
        fake_client = SimpleNamespace(batch=lambda: fake_batch)
        fake_collection = FakeCollection()

        with patch("src.service.gemini._chat_collection", return_value=fake_collection), patch(
            "src.service.gemini.firestore.client", return_value=fake_client
        ), patch("src.service.gemini.time.time_ns", return_value=100), patch(
            "src.service.gemini.uuid.uuid4", return_value=SimpleNamespace(hex="turnabc")
        ):
            gemini._save_turn("user-1", "proj-1", "chat-1", "u-msg", "m-msg")

        self.assertTrue(fake_batch.committed)
        self.assertEqual(len(fake_batch.ops), 2)

        first_ref, first_data = fake_batch.ops[0]
        second_ref, second_data = fake_batch.ops[1]

        self.assertEqual(first_ref, "ref:00000000000000000100_0_turnabc")
        self.assertEqual(second_ref, "ref:00000000000000000101_1_turnabc")

        self.assertEqual(first_data["role"], "user")
        self.assertEqual(first_data["position"], 0)
        self.assertEqual(first_data["turn_id"], "turnabc")
        self.assertEqual(first_data["text"], "u-msg")

        self.assertEqual(second_data["role"], "model")
        self.assertEqual(second_data["position"], 1)
        self.assertEqual(second_data["turn_id"], "turnabc")
        self.assertEqual(second_data["text"], "m-msg")


if __name__ == "__main__":
    unittest.main()
