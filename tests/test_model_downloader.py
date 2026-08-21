"""Unit tests for model downloader, sha256 checking, and resume logic."""

import hashlib
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from AnkiAI_ImageAddon.modules.model_downloader import (
    compute_file_sha256,
    download_file_with_resume,
    DownloadError,
)


def test_compute_file_sha256(tmp_path):
    sample_file = tmp_path / "sample.bin"
    content = b"Hello, AnkiAI Model Downloader!"
    sample_file.write_bytes(content)

    expected_sha = hashlib.sha256(content).hexdigest()
    actual_sha = compute_file_sha256(sample_file)
    assert actual_sha == expected_sha


@patch("requests.get")
def test_download_file_with_resume_and_sha(mock_get, tmp_path):
    target_file = tmp_path / "model.onnx"
    content = b"Mock ONNX Model Binary Data"
    expected_sha = hashlib.sha256(content).hexdigest()

    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-length": str(len(content))}
    mock_resp.iter_content = lambda chunk_size: [content]
    mock_get.return_value = mock_resp

    progress_records = []

    def on_progress(done, total):
        progress_records.append((done, total))

    result_path = download_file_with_resume(
        "https://example.com/model.onnx",
        target_file,
        expected_sha256=expected_sha,
        progress_callback=on_progress,
    )

    assert result_path == target_file
    assert target_file.exists()
    assert target_file.read_bytes() == content
    assert len(progress_records) > 0


@patch("requests.get")
def test_download_checksum_mismatch_raises_error(mock_get, tmp_path):
    target_file = tmp_path / "corrupt_model.onnx"
    content = b"Some binary content"
    wrong_sha = "0000000000000000000000000000000000000000000000000000000000000000"

    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-length": str(len(content))}
    mock_resp.iter_content = lambda chunk_size: [content]
    mock_get.return_value = mock_resp

    with pytest.raises(DownloadError):
        download_file_with_resume(
            "https://example.com/model.onnx",
            target_file,
            expected_sha256=wrong_sha,
        )
    assert not target_file.exists()
