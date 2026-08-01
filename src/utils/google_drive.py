"""
src/utils/google_drive.py
-------------------------
Utilities for authenticating with Google Drive API, listing folder contents,
and bulk downloading supported assignment files (.pdf, .docx, .txt).
"""

import os
import re
import io
from typing import Dict, List, Tuple, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account

# Supported extensions for the plagiarism detection pipeline
SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".txt")


_DRIVE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{33}$")
_DRIVE_URL_RE = re.compile(r"folders/([a-zA-Z0-9_-]{33})(?:[/?]|$)")

def extract_google_drive_folder_id(url_or_id: str) -> str | None:
    """
    Extracts the Google Drive Folder ID from a full Drive URL or raw ID string.
    Validates a 33-character ID consisting of letters, numbers, '_' and '-'.
    """
    if not isinstance(url_or_id, str):
        return None
        
    cleaned = url_or_id.strip()
    if not cleaned:
        return None

    if _DRIVE_ID_RE.match(cleaned):
        return cleaned

    match = _DRIVE_URL_RE.search(cleaned)
    if match:
        return match.group(1)

    return None


def get_drive_service(api_key: Optional[str] = None, service_account_info: Optional[dict] = None):
    """
    Builds and returns a Google Drive API service instance using an API key or Service Account.
    """
    if service_account_info:
        creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        return build("drive", "v3", credentials=creds)
    elif api_key:
        return build("drive", "v3", developerKey=api_key)
    else:
        # Fallback to environment variable key if present
        env_key = os.getenv("GOOGLE_DRIVE_API_KEY")
        if env_key:
            return build("drive", "v3", developerKey=env_key)
        raise ValueError("No API Key or Service Account credentials provided.")


def list_files_in_folder(service, folder_id: str) -> List[Dict[str, str]]:
    """
    Lists all supported assignment files (.pdf, .docx, .txt) within a specified Google Drive folder.
    """
    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(
        q=query,
        pageSize=100,
        fields="nextPageToken, files(id, name, mimeType, size)"
    ).execute()

    files = results.get("files", [])
    supported_files = [
        f for f in files if f["name"].lower().endswith(SUPPORTED_EXTENSIONS)
    ]
    return supported_files


def download_file_bytes(service, file_id: str) -> bytes:
    """
    Downloads a binary file from Google Drive into a BytesIO stream and returns bytes.
    """
    request = service.files().get_media(fileId=file_id)
    file_stream = io.BytesIO()
    downloader = MediaIoBaseDownload(file_stream, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return file_stream.getvalue()


def bulk_download_drive_folder(
    folder_url_or_id: str,
    api_key: Optional[str] = None,
    service_account_info: Optional[dict] = None,
) -> Tuple[Dict[str, bytes], List[str]]:
    """
    Main helper: Extracts folder ID, lists supported files, downloads them into memory,
    and returns a dictionary mapping filename -> raw bytes.

    Returns:
        Tuple[Dict[str, bytes], List[str]]: (file_bytes_dict, list_of_downloaded_filenames)
    """
    folder_id = extract_google_drive_folder_id(folder_url_or_id)
    if not folder_id:
        raise ValueError("Invalid Google Drive Folder URL or ID.")

    service = get_drive_service(api_key=api_key, service_account_info=service_account_info)
    files_to_download = list_files_in_folder(service, folder_id)

    downloaded_files_dict = {}
    downloaded_names = []

    for f in files_to_download:
        file_bytes = download_file_bytes(service, f["id"])
        downloaded_files_dict[f["name"]] = file_bytes
        downloaded_names.append(f["name"])

    return downloaded_files_dict, downloaded_names