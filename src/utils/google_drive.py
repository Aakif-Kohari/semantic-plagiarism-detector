"""
src/utils/google_drive.py
-------------------------
Utilities for authenticating with Google Drive API, listing folder contents,
and bulk downloading supported assignment files (.pdf, .docx, .txt).
"""

import io
import os
import re
from typing import Dict, List, Optional, Tuple

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from src.utils.filename import unique_filename

# Supported extensions for the plagiarism detection pipeline
SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".doc", ".txt")


def extract_folder_id(url_or_id: str) -> Optional[str]:
    """
    Extracts the Google Drive Folder ID from a full Drive URL or raw ID string.
    Example URL: https://drive.google.com/drive/folders/1A2B3C4D5E6F7G8H9
    """
    url_or_id = url_or_id.strip()
    if not url_or_id:
        return None

    # Regex pattern to match folder ID inside standard Drive URLs
    match = re.search(r"folders/([a-zA-Z0-9_-]+)", url_or_id)
    if match:
        return match.group(1)

    # Return raw string if it looks like a direct ID key
    if re.match(r"^[a-zA-Z0-9_-]+$", url_or_id):
        return url_or_id

    return None


def get_drive_service(
    api_key: Optional[str] = None, service_account_info: Optional[dict] = None
):
    """
    Builds and returns a Google Drive API service instance using an API key or Service Account.
    """
    if service_account_info:
        creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
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
    results = (
        service.files()
        .list(
            q=query,
            pageSize=100,
            fields="nextPageToken, files(id, name, mimeType, size)",
        )
        .execute()
    )

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
    folder_id = extract_folder_id(folder_url_or_id)
    if not folder_id:
        raise ValueError("Invalid Google Drive Folder URL or ID.")

    service = get_drive_service(
        api_key=api_key, service_account_info=service_account_info
    )
    files_to_download = list_files_in_folder(service, folder_id)

    downloaded_files_dict = {}
    downloaded_names = []

    for file_record in files_to_download:
        file_bytes = download_file_bytes(service, file_record["id"])
        safe_name = unique_filename(
            file_record["name"],
            downloaded_files_dict,
        )
        downloaded_files_dict[safe_name] = file_bytes
        downloaded_names.append(safe_name)

    return downloaded_files_dict, downloaded_names
