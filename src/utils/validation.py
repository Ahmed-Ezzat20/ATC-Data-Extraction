"""
Input Validation Module

Provides validation functions for URLs, files, and configuration.
"""

import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


def validate_youtube_url(url: str) -> bool:
    """
    Validate YouTube video URL format.

    Args:
        url: YouTube URL to validate

    Returns:
        True if valid, False otherwise
    """
    if not url:
        return False

    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
    ]

    for pattern in youtube_patterns:
        if re.match(pattern, url):
            return True

    return False


def validate_playlist_url(url: str) -> bool:
    """
    Validate YouTube playlist URL format.

    Args:
        url: YouTube playlist URL to validate

    Returns:
        True if valid, False otherwise
    """
    if not url:
        return False

    playlist_pattern = r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)'
    return bool(re.match(playlist_pattern, url))


def validate_api_key(api_key: str) -> bool:
    """
    Validate Gemini API key format.

    Args:
        api_key: API key to validate

    Returns:
        True if valid format, False otherwise
    """
    if not api_key or len(api_key) < 20:
        return False

    # Basic format check (alphanumeric and common special characters)
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', api_key))


def validate_file_exists(file_path: str) -> bool:
    """
    Validate that a file exists.

    Args:
        file_path: Path to file

    Returns:
        True if file exists, False otherwise
    """
    return Path(file_path).exists() and Path(file_path).is_file()


def validate_directory_exists(dir_path: str, create: bool = False) -> bool:
    """
    Validate that a directory exists, optionally creating it.

    Args:
        dir_path: Path to directory
        create: Whether to create directory if it doesn't exist

    Returns:
        True if directory exists or was created, False otherwise
    """
    path = Path(dir_path)

    if path.exists():
        return path.is_dir()

    if create:
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    return False


def validate_timestamp(start_time: int, end_time: int) -> bool:
    """
    Validate timestamp range.

    Args:
        start_time: Start time in seconds
        end_time: End time in seconds

    Returns:
        True if valid, False otherwise
    """
    return (
        start_time >= 0 and
        end_time >= 0 and
        end_time > start_time
    )


def validate_video_id(video_id: str) -> bool:
    """
    Validate YouTube video ID format.

    Args:
        video_id: Video ID to validate

    Returns:
        True if valid format, False otherwise
    """
    if not video_id:
        return False

    # YouTube video IDs are typically 11 characters long
    return bool(re.match(r'^[a-zA-Z0-9_-]{11}$', video_id))


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass
