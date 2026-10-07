from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.schemas.evidence import ProvenanceResult
from app.services.c2pa_service import C2PAService


def test_c2pa_missing_file():
    service = C2PAService()
    res = service.inspect(Path("/non/existent/file.mp4"))
    assert res.state == "UNAVAILABLE"
    assert res.valid is None
    assert res.trusted is None


def test_c2pa_no_manifest_found(synthetic_video_path: Path):
    service = C2PAService()
    res = service.inspect(synthetic_video_path)
    assert res.state == "NONE_FOUND"
    assert res.valid is None
    assert res.trusted is None
    assert "Absence of content credentials does not indicate manipulation" in res.note


def test_c2pa_corrupted_file(tmp_path: Path):
    corrupt_file = tmp_path / "corrupt.mp4"
    corrupt_file.write_bytes(b"INVALID_HEADER_GARBAGE_DATA" * 10)

    service = C2PAService()
    res = service.inspect(corrupt_file)
    assert res.state == "ERROR"
    assert "Unable to read content credentials" in res.note


@patch("c2pa.Reader.try_create")
def test_c2pa_manifest_valid_and_trusted(mock_try_create, tmp_path):
    video_file = tmp_path / "signed_video.mp4"
    video_file.write_bytes(b"dummy signed data")

    mock_reader = MagicMock()
    mock_reader.get_validation_state.return_value = "Valid"
    mock_reader.json.return_value = '{"active_manifest": "m1", "manifests": {"m1": {"signature_info": {"issuer": "Adobe Inc."}}}}'
    mock_try_create.return_value = mock_reader

    service = C2PAService(trusted_signers=["Adobe", "Truepic"])
    res = service.inspect(video_file)

    assert res.state == "FOUND"
    assert res.valid is True
    assert res.trusted is True
    assert res.signer == "Adobe Inc."
    assert "trusted signer: 'Adobe Inc.'" in res.note


@patch("c2pa.Reader.try_create")
def test_c2pa_manifest_valid_but_untrusted(mock_try_create, tmp_path):
    video_file = tmp_path / "untrusted_signed.mp4"
    video_file.write_bytes(b"dummy signed data")

    mock_reader = MagicMock()
    mock_reader.get_validation_state.return_value = "Valid"
    mock_reader.json.return_value = '{"active_manifest": "m1", "manifests": {"m1": {"signature_info": {"issuer": "Unknown Actor Org"}}}}'
    mock_try_create.return_value = mock_reader

    service = C2PAService(trusted_signers=["Adobe", "Truepic"])
    res = service.inspect(video_file)

    assert res.state == "FOUND"
    assert res.valid is True
    assert res.trusted is False
    assert res.signer == "Unknown Actor Org"
    assert "not on the configured trust list" in res.note


@patch("c2pa.Reader.try_create")
def test_c2pa_manifest_invalid_signature(mock_try_create, tmp_path):
    video_file = tmp_path / "tampered_signed.mp4"
    video_file.write_bytes(b"dummy tampered data")

    mock_reader = MagicMock()
    mock_reader.get_validation_state.return_value = "Invalid: signature mismatch"
    mock_reader.json.return_value = '{"active_manifest": "m1", "manifests": {"m1": {"signature_info": {"issuer": "Adobe Inc."}}}}'
    mock_try_create.return_value = mock_reader

    service = C2PAService(trusted_signers=["Adobe"])
    res = service.inspect(video_file)

    assert res.state == "FOUND"
    assert res.valid is False
    assert res.trusted is False
    assert "signature validation failed" in res.note.lower()


@patch("c2pa.Reader.try_create")
def test_c2pa_manifest_ai_generation_declared(mock_try_create, tmp_path):
    video_file = tmp_path / "ai_gen.mp4"
    video_file.write_bytes(b"dummy ai data")

    mock_reader = MagicMock()
    mock_reader.get_validation_state.return_value = "Valid"
    mock_reader.json.return_value = (
        '{"active_manifest": "m1", "manifests": {"m1": {'
        '"signature_info": {"issuer": "OpenAI"}, '
        '"assertions": [{"label": "c2pa.actions", "data": {"actions": [{"action": "c2pa.created", "digitalSourceType": "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"}]}}]'
        '}}}'
    )
    mock_try_create.return_value = mock_reader

    service = C2PAService(trusted_signers=["OpenAI"])
    res = service.inspect(video_file)

    assert res.state == "FOUND"
    assert res.valid is True
    assert res.trusted is True
    assert res.ai_generated is True
    assert "declaring ai/algorithmic media generation" in res.note.lower()
