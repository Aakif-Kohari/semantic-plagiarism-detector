"""Mock tests for Google Drive API operations."""

import os
from unittest.mock import Mock, patch

import pytest

from src.utils.google_drive import (bulk_download_drive_folder,
                                    download_file_bytes, extract_folder_id,
                                    get_drive_service, list_files_in_folder)

# ── extract_folder_id tests ──────────────────────────────────────────────


def test_extract_folder_id_from_url():
    fid = extract_folder_id(
        "https://drive.google.com/drive/folders/1A2B3C4D5E6F7G8H9"
    )
    assert fid == "1A2B3C4D5E6F7G8H9"


def test_extract_folder_id_from_url_with_extra_params():
    fid = extract_folder_id(
        "https://drive.google.com/drive/folders/abcDEF123?usp=sharing"
    )
    assert fid == "abcDEF123"


def test_extract_folder_id_from_raw_id():
    assert extract_folder_id("abc123DEF_-") == "abc123DEF_-"


def test_extract_folder_id_invalid_url():
    result = extract_folder_id("https://example.com/not-a-drive-url")
    assert result is None


def test_extract_folder_id_empty_string():
    assert extract_folder_id("") is None


# ── get_drive_service tests ──────────────────────────────────────────────


@patch("src.utils.google_drive.build")
def test_get_drive_service_with_api_key(mock_build):
    service = get_drive_service(api_key="test-api-key")
    mock_build.assert_called_once_with(
        "drive", "v3", developerKey="test-api-key"
    )
    assert service == mock_build.return_value


@patch("src.utils.google_drive.build")
@patch("src.utils.google_drive.service_account")
def test_get_drive_service_with_service_account(mock_sa, mock_build):
    mock_creds = Mock()
    mock_sa.Credentials.from_service_account_info.return_value = mock_creds
    sa_info = {"type": "service_account"}

    service = get_drive_service(service_account_info=sa_info)

    mock_sa.Credentials.from_service_account_info.assert_called_once_with(
        sa_info,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    mock_build.assert_called_once_with("drive", "v3", credentials=mock_creds)
    assert service == mock_build.return_value


@patch("src.utils.google_drive.build")
def test_get_drive_service_with_env_key(mock_build):
    with patch.dict(os.environ, {"GOOGLE_DRIVE_API_KEY": "env-key"}, clear=False):
        service = get_drive_service()
    mock_build.assert_called_once_with("drive", "v3", developerKey="env-key")
    assert service == mock_build.return_value


@patch("src.utils.google_drive.build")
def test_get_drive_service_no_credentials(mock_build):
    with patch.dict(os.environ, {"GOOGLE_DRIVE_API_KEY": ""}, clear=False):
        with pytest.raises(ValueError, match="No API Key or Service Account"):
            get_drive_service()


# ── list_files_in_folder tests ───────────────────────────────────────────


def _mock_service_for_list(files):
    service = Mock()
    service.files.return_value.list.return_value.execute.return_value = {
        "files": files
    }
    return service


def test_list_files_in_folder_returns_supported():
    files = [
        {"id": "1", "name": "report.pdf", "mimeType": "application/pdf"},
        {"id": "2", "name": "essay.docx", "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        {"id": "3", "name": "notes.txt", "mimeType": "text/plain"},
        {"id": "4", "name": "script.exe", "mimeType": "application/x-msdownload"},
    ]
    service = _mock_service_for_list(files)
    result = list_files_in_folder(service, "folder123")

    assert len(result) == 3
    assert result[0]["name"] == "report.pdf"
    assert result[1]["name"] == "essay.docx"
    assert result[2]["name"] == "notes.txt"

    service.files.return_value.list.assert_called_once_with(
        q="'folder123' in parents and trashed = false",
        pageSize=100,
        fields="nextPageToken, files(id, name, mimeType, size)",
    )


def test_list_files_in_folder_empty():
    service = _mock_service_for_list([])
    result = list_files_in_folder(service, "folder123")
    assert result == []


def test_list_files_in_folder_no_supported_extensions():
    files = [
        {"id": "1", "name": "script.exe", "mimeType": "application/x-msdownload"},
        {"id": "2", "name": "image.png", "mimeType": "image/png"},
    ]
    service = _mock_service_for_list(files)
    result = list_files_in_folder(service, "folder123")
    assert result == []


def test_list_files_in_folder_handles_api_error():
    service = Mock()
    service.files.return_value.list.return_value.execute.side_effect = \
        Exception("403 Forbidden")

    with pytest.raises(Exception, match="403 Forbidden"):
        list_files_in_folder(service, "folder123")


def test_list_files_in_folder_handles_not_found():
    service = Mock()
    service.files.return_value.list.return_value.execute.side_effect = \
        Exception("404 Not Found")

    with pytest.raises(Exception, match="404 Not Found"):
        list_files_in_folder(service, "folder123")


# ── download_file_bytes tests ────────────────────────────────────────────


@patch("src.utils.google_drive.MediaIoBaseDownload")
def test_download_file_bytes(mock_downloader_cls):
    mock_downloader = Mock()
    mock_downloader.next_chunk.side_effect = [(None, False), (None, True)]
    mock_downloader_cls.return_value = mock_downloader

    service = Mock()
    mock_request = Mock()
    service.files.return_value.get_media.return_value = mock_request

    result = download_file_bytes(service, "file123")

    service.files.return_value.get_media.assert_called_once_with(fileId="file123")
    mock_downloader_cls.assert_called_once()
    assert isinstance(result, bytes)


@patch("src.utils.google_drive.MediaIoBaseDownload")
def test_download_file_bytes_handles_api_error(mock_downloader_cls):
    mock_downloader = Mock()
    mock_downloader.next_chunk.side_effect = Exception("403 Forbidden")
    mock_downloader_cls.return_value = mock_downloader

    service = Mock()
    service.files.return_value.get_media.return_value = Mock()

    with pytest.raises(Exception, match="403 Forbidden"):
        download_file_bytes(service, "file456")


# ── bulk_download_drive_folder tests ─────────────────────────────────────


@patch("src.utils.google_drive.download_file_bytes")
@patch("src.utils.google_drive.list_files_in_folder")
@patch("src.utils.google_drive.get_drive_service")
def test_bulk_download_drive_folder(mock_get_service, mock_list, mock_download):
    mock_list.return_value = [
        {"id": "f1", "name": "doc1.pdf"},
        {"id": "f2", "name": "doc2.docx"},
    ]
    mock_download.side_effect = [b"content1", b"content2"]

    result, names = bulk_download_drive_folder(
        "https://drive.google.com/drive/folders/folder123",
        api_key="key",
    )

    assert len(result) == 2
    assert result["doc1.pdf"] == b"content1"
    assert result["doc2.docx"] == b"content2"
    assert names == ["doc1.pdf", "doc2.docx"]


@patch("src.utils.google_drive.download_file_bytes")
@patch("src.utils.google_drive.list_files_in_folder")
@patch("src.utils.google_drive.get_drive_service")
def test_bulk_download_drive_folder_handles_download_error(
    mock_get_service, mock_list, mock_download
):
    mock_list.return_value = [{"id": "f1", "name": "doc1.pdf"}]
    mock_download.side_effect = Exception("404 Not Found")

    with pytest.raises(Exception, match="404 Not Found"):
        bulk_download_drive_folder(
            "https://drive.google.com/drive/folders/folder123",
            api_key="key",
        )


def test_bulk_download_drive_folder_invalid_folder():
    with pytest.raises(ValueError, match="Invalid Google Drive Folder"):
        bulk_download_drive_folder("https://example.com/path")


@patch("src.utils.google_drive.download_file_bytes")
@patch("src.utils.google_drive.list_files_in_folder")
@patch("src.utils.google_drive.get_drive_service")
def test_bulk_download_drive_folder_handles_list_error(
    mock_get_service, mock_list, mock_download
):
    mock_list.side_effect = Exception("403 Forbidden")

    with pytest.raises(Exception, match="403 Forbidden"):
        bulk_download_drive_folder(
            "https://drive.google.com/drive/folders/folder123",
            api_key="key",
        )
