"""Tests for AddImageTask result finalization."""

import pytest

from AnkiAI_ImageAddon import AddImageTask


class TestFinalizeResult:
    def test_true_success(self):
        assert AddImageTask._finalize_result(True, "ok", "cat") == (True, "ok")

    def test_skipped_not_treated_as_success(self):
        out = AddImageTask._finalize_result("skipped", "Đã có ảnh", "cat")
        assert out == ("skipped", "Đã có ảnh")

    def test_false_failure(self):
        assert AddImageTask._finalize_result(False, "lỗi", "cat") == (False, "lỗi")
