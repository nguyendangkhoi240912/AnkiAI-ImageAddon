"""Tests for image_handler status returns (skipped / overwrite)."""

from unittest.mock import MagicMock, patch

import pytest

from AnkiAI_ImageAddon.modules.image_handler import ImageHandler, ImageError


@pytest.fixture
def handler():
    mw = MagicMock()
    mw.col = MagicMock()
    mw.col.media.writeData.return_value = "test.jpg"
    return ImageHandler(mw)


@pytest.fixture
def note_with_image():
    return {"Word": "hello", "Image": '<img src="old.jpg">'}


@pytest.fixture
def empty_note():
    return {"Word": "hello", "Image": ""}


class TestInsertImageToNote:
    def test_skip_when_image_exists(self, handler, note_with_image):
        before = note_with_image["Image"]
        assert handler.insert_image_to_note(
            note_with_image, "new.jpg", "Image", overwrite=False
        ) is False
        assert note_with_image["Image"] == before

    def test_overwrite_replaces_image(self, handler, note_with_image):
        assert handler.insert_image_to_note(
            note_with_image, "new.jpg", "Image", overwrite=True
        ) is True
        assert "new.jpg" in note_with_image["Image"]
        assert "old.jpg" not in note_with_image["Image"]

    def test_missing_field_raises(self, handler, empty_note):
        with pytest.raises(ImageError, match="không tồn tại"):
            handler.insert_image_to_note(empty_note, "x.jpg", "MissingField")


class TestProcessImageStatus:
    @patch.object(ImageHandler, "download_image", return_value=b"\xff\xd8\xff\x00")
    @patch.object(ImageHandler, "get_image_filename", return_value="w.jpg")
    @patch.object(ImageHandler, "save_image_to_anki", return_value="w.jpg")
    def test_returns_skipped_when_image_exists(
        self, _save, _name, _dl, handler, note_with_image
    ):
        status, msg = handler.process_image(
            "http://example.com/a.jpg", note_with_image, "word", "Image"
        )
        assert status == "skipped"
        assert "ảnh" in msg.lower()
        _dl.assert_not_called()
        _save.assert_not_called()

    @patch.object(ImageHandler, "download_image", return_value=b"\xff\xd8\xff\x00")
    @patch.object(ImageHandler, "get_image_filename", return_value="w.jpg")
    @patch.object(ImageHandler, "save_image_to_anki", return_value="w.jpg")
    def test_returns_true_when_inserted(
        self, _save, _name, _dl, handler, empty_note
    ):
        status, msg = handler.process_image(
            "http://example.com/a.jpg", empty_note, "word", "Image"
        )
        assert status is True
        assert "thành công" in msg.lower()

    @patch.object(ImageHandler, "insert_image_to_note", return_value=False)
    def test_save_and_insert_removes_orphan(
        self, _insert, handler, empty_note
    ):
        handler.col.media.writeData.return_value = "orphan.jpg"
        status, _ = handler.save_and_insert(
            empty_note, b"\xff\xd8\xff\x00", "word", "Image"
        )
        assert status == "skipped"
        handler.col.media.trash_files.assert_called_once_with(["orphan.jpg"])
