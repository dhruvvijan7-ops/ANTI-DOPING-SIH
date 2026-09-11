"""Import pipeline exceptions.

Every failure path surfaces a human-readable reason; nothing is silently
discarded (condition §24, §598-§602).
"""
from __future__ import annotations


class BadUploadError(Exception):
    """Upload-level rejection (size, empty, undetectable, unsupported, corrupt)."""


class EmptyPayloadError(BadUploadError):
    """No content was provided."""


class UnsupportedFormatError(BadUploadError):
    """Content could not be identified as a supported import format."""


class BadUploadSizeError(BadUploadError):
    """Upload exceeded the configured size limit."""