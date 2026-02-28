"""Tests for FineTuningManager — Mistral fine-tuning API wrapper."""

import unittest
from unittest.mock import MagicMock, patch


class TestFineTuningManager(unittest.TestCase):
    # 1
    @patch("app.finetuning.Mistral")
    @patch("app.finetuning.settings")
    def test_upload_training_data(self, mock_settings, MockMistral):
        """Mock client.files.upload(), verify it's called with correct args."""
        mock_settings.mistral_api_key = "test-key"
        mock_client = MagicMock()
        MockMistral.return_value = mock_client
        mock_client.files.upload.return_value = MagicMock(id="file-123")

        from app.finetuning import FineTuningManager

        mgr = FineTuningManager()

        with patch("builtins.open", unittest.mock.mock_open(read_data=b"data")):
            file_id = mgr.upload_training_data("/tmp/data.jsonl")

        self.assertEqual(file_id, "file-123")
        mock_client.files.upload.assert_called_once()
        call_kwargs = mock_client.files.upload.call_args
        self.assertEqual(call_kwargs[1]["purpose"], "fine-tune")

    # 2
    @patch("app.finetuning.Mistral")
    @patch("app.finetuning.settings")
    def test_create_job(self, mock_settings, MockMistral):
        """Mock client.fine_tuning.jobs.create(), verify params."""
        mock_settings.mistral_api_key = "test-key"
        mock_client = MagicMock()
        MockMistral.return_value = mock_client

        mock_job = MagicMock()
        mock_job.model_dump.return_value = {
            "id": "job-abc",
            "model": "mistral-small-latest",
            "status": "queued",
        }
        mock_client.fine_tuning.jobs.create.return_value = mock_job

        from app.finetuning import FineTuningManager

        mgr = FineTuningManager()
        result = mgr.create_job(
            model="mistral-small-latest",
            training_file_id="file-123",
            suffix="mars-agent",
            hyperparameters={"training_steps": 100},
        )

        self.assertEqual(result["id"], "job-abc")
        mock_client.fine_tuning.jobs.create.assert_called_once_with(
            model="mistral-small-latest",
            training_files=[{"file_id": "file-123", "weight": 1}],
            hyperparameters={"training_steps": 100},
            suffix="mars-agent",
        )

    # 3
    @patch("app.finetuning.Mistral")
    @patch("app.finetuning.settings")
    def test_get_job(self, mock_settings, MockMistral):
        """Mock client.fine_tuning.jobs.get()."""
        mock_settings.mistral_api_key = "test-key"
        mock_client = MagicMock()
        MockMistral.return_value = mock_client

        mock_job = MagicMock()
        mock_job.model_dump.return_value = {
            "id": "job-abc",
            "status": "running",
            "fine_tuned_model": None,
        }
        mock_client.fine_tuning.jobs.get.return_value = mock_job

        from app.finetuning import FineTuningManager

        mgr = FineTuningManager()
        result = mgr.get_job("job-abc")

        self.assertEqual(result["id"], "job-abc")
        self.assertEqual(result["status"], "running")
        mock_client.fine_tuning.jobs.get.assert_called_once_with(job_id="job-abc")

    # 4
    @patch("app.finetuning.Mistral")
    @patch("app.finetuning.settings")
    def test_list_jobs(self, mock_settings, MockMistral):
        """Mock client.fine_tuning.jobs.list()."""
        mock_settings.mistral_api_key = "test-key"
        mock_client = MagicMock()
        MockMistral.return_value = mock_client

        mock_job1 = MagicMock()
        mock_job1.model_dump.return_value = {"id": "job-1", "status": "completed"}
        mock_job2 = MagicMock()
        mock_job2.model_dump.return_value = {"id": "job-2", "status": "running"}

        mock_response = MagicMock()
        mock_response.data = [mock_job1, mock_job2]
        mock_client.fine_tuning.jobs.list.return_value = mock_response

        from app.finetuning import FineTuningManager

        mgr = FineTuningManager()
        result = mgr.list_jobs()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "job-1")
        self.assertEqual(result[1]["id"], "job-2")

    # 5
    @patch("app.finetuning.Mistral")
    @patch("app.finetuning.settings")
    def test_cancel_job(self, mock_settings, MockMistral):
        """Mock client.fine_tuning.jobs.cancel()."""
        mock_settings.mistral_api_key = "test-key"
        mock_client = MagicMock()
        MockMistral.return_value = mock_client

        mock_job = MagicMock()
        mock_job.model_dump.return_value = {"id": "job-abc", "status": "cancelled"}
        mock_client.fine_tuning.jobs.cancel.return_value = mock_job

        from app.finetuning import FineTuningManager

        mgr = FineTuningManager()
        result = mgr.cancel_job("job-abc")

        self.assertEqual(result["status"], "cancelled")
        mock_client.fine_tuning.jobs.cancel.assert_called_once_with(job_id="job-abc")

    # 6
    @patch("app.finetuning.Mistral")
    @patch("app.finetuning.settings")
    def test_activate_model_agent(self, mock_settings, MockMistral):
        """Call activate_model(job_id, 'agent'), verify setting is updated."""
        mock_settings.mistral_api_key = "test-key"
        mock_settings.fine_tuned_agent_model = ""
        mock_client = MagicMock()
        MockMistral.return_value = mock_client

        mock_job = MagicMock()
        mock_job.model_dump.return_value = {
            "id": "job-abc",
            "status": "completed",
            "fine_tuned_model": "ft:mistral-small:mars-agent:abc123",
        }
        mock_client.fine_tuning.jobs.get.return_value = mock_job

        from app.finetuning import FineTuningManager

        mgr = FineTuningManager()
        result = mgr.activate_model("job-abc", "agent")

        self.assertEqual(result["activated"], "ft:mistral-small:mars-agent:abc123")
        self.assertEqual(result["target"], "agent")
        self.assertEqual(
            mock_settings.fine_tuned_agent_model,
            "ft:mistral-small:mars-agent:abc123",
        )

    # 7
    @patch("app.finetuning.Mistral")
    @patch("app.finetuning.settings")
    def test_activate_model_narration(self, mock_settings, MockMistral):
        """Call activate_model(job_id, 'narration'), verify setting is updated."""
        mock_settings.mistral_api_key = "test-key"
        mock_settings.fine_tuned_narration_model = ""
        mock_client = MagicMock()
        MockMistral.return_value = mock_client

        mock_job = MagicMock()
        mock_job.model_dump.return_value = {
            "id": "job-abc",
            "status": "completed",
            "fine_tuned_model": "ft:mistral-small:mars-narration:xyz789",
        }
        mock_client.fine_tuning.jobs.get.return_value = mock_job

        from app.finetuning import FineTuningManager

        mgr = FineTuningManager()
        result = mgr.activate_model("job-abc", "narration")

        self.assertEqual(result["activated"], "ft:mistral-small:mars-narration:xyz789")
        self.assertEqual(result["target"], "narration")
        self.assertEqual(
            mock_settings.fine_tuned_narration_model,
            "ft:mistral-small:mars-narration:xyz789",
        )

    # 8
    @patch("app.finetuning.Mistral")
    @patch("app.finetuning.settings")
    def test_activate_model_invalid_target(self, mock_settings, MockMistral):
        """Verify ValueError for invalid target."""
        mock_settings.mistral_api_key = "test-key"
        mock_client = MagicMock()
        MockMistral.return_value = mock_client

        mock_job = MagicMock()
        mock_job.model_dump.return_value = {
            "id": "job-abc",
            "status": "completed",
            "fine_tuned_model": "ft:model:suffix:id",
        }
        mock_client.fine_tuning.jobs.get.return_value = mock_job

        from app.finetuning import FineTuningManager

        mgr = FineTuningManager()
        with self.assertRaises(ValueError) as ctx:
            mgr.activate_model("job-abc", "invalid_target")
        self.assertIn("Invalid target", str(ctx.exception))

    # 9
    @patch("app.finetuning.Mistral")
    @patch("app.finetuning.settings")
    def test_activate_model_no_model(self, mock_settings, MockMistral):
        """Verify error when job has no fine_tuned_model."""
        mock_settings.mistral_api_key = "test-key"
        mock_client = MagicMock()
        MockMistral.return_value = mock_client

        mock_job = MagicMock()
        mock_job.model_dump.return_value = {
            "id": "job-abc",
            "status": "running",
            "fine_tuned_model": None,
        }
        mock_client.fine_tuning.jobs.get.return_value = mock_job

        from app.finetuning import FineTuningManager

        mgr = FineTuningManager()
        with self.assertRaises(ValueError) as ctx:
            mgr.activate_model("job-abc", "agent")
        self.assertIn("no fine-tuned model", str(ctx.exception))

    # 10
    @patch("app.finetuning.settings")
    def test_missing_api_key(self, mock_settings):
        """Verify RuntimeError when MISTRAL_API_KEY is empty."""
        mock_settings.mistral_api_key = ""

        from app.finetuning import FineTuningManager

        mgr = FineTuningManager()
        with self.assertRaises(RuntimeError) as ctx:
            mgr.upload_training_data("/tmp/data.jsonl")
        self.assertIn("MISTRAL_API_KEY", str(ctx.exception))
