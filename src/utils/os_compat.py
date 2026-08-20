"""
src/utils/os_compat.py
----------------------
Operating System compatibility patches and workarounds.

This module centralizes OS-specific hacks, event loop policy adjustments,
and platform-dependent workarounds that are required to make the application
run smoothly across Windows, macOS, and Linux environments.

By isolating these patches in a dedicated utility module, we prevent
OS-level implementation details from cluttering the main application
routing files (e.g., streamlit_app.py) and improve overall code readability.

Issue #2781: Isolate OS-specific asyncio patches.
"""

import asyncio
import logging
import sys
import platform
from typing import Optional

logger = logging.getLogger(__name__)

# Track whether patches have already been applied to prevent duplicate execution
# during Streamlit's frequent script reruns.
_PATCHES_APPLIED = False


def get_os_platform() -> str:
    """Identify the current operating system platform.

    Returns a normalized string representing the OS:
    - 'windows' for Windows systems
    - 'macos' for macOS/Darwin systems
    - 'linux' for Linux distributions
    - 'unknown' for unrecognized platforms

    Returns:
        str: Normalized OS identifier.
    """
    system = platform.system().lower()

    if system == "windows":
        return "windows"
    elif system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    else:
        logger.warning("Unrecognized operating system: %s", system)
        return "unknown"


def apply_asyncio_patches() -> bool:
    """Apply necessary asyncio event loop policy patches for the current OS.

    Windows-specific patch:
        On Windows, the default ProactorEventLoop can cause issues with
        certain asynchronous libraries (like websockets or database drivers)
        when running inside Streamlit's execution model. This patch forces
        the use of the SelectorEventLoop, which is more compatible with
        Streamlit's threading model on Windows.

    macOS/Linux:
        No patches are currently required for Unix-like systems, as the
        default event loop policies are compatible with Streamlit.

    Returns:
        bool: True if patches were applied successfully, False if they were
              already applied or not needed.

    Side Effects:
        Modifies the global asyncio event loop policy if on Windows.
        Logs informational messages about the applied patches.
    """
    global _PATCHES_APPLIED

    # Prevent duplicate application of patches during Streamlit reruns
    if _PATCHES_APPLIED:
        logger.debug("OS compatibility patches already applied. Skipping.")
        return False

    current_os = get_os_platform()
    logger.info("Detecting OS platform for asyncio patches: %s", current_os)

    if current_os == "windows":
        try:
            # Check if the policy is already the SelectorEventLoopPolicy
            # to avoid unnecessary reassignment warnings.
            current_policy = asyncio.get_event_loop_policy()
            if not isinstance(current_policy, asyncio.WindowsSelectorEventLoopPolicy):
                logger.info(
                    "Windows detected. Applying WindowsSelectorEventLoopPolicy "
                    "to prevent ProactorEventLoop compatibility issues with Streamlit."
                )
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                _PATCHES_APPLIED = True
                return True
            else:
                logger.debug("WindowsSelectorEventLoopPolicy already active.")
                _PATCHES_APPLIED = True
                return False

        except Exception as e:
            logger.error(
                "Failed to apply Windows asyncio event loop policy: %s. "
                "Application may experience async compatibility issues.",
                e,
                exc_info=True,
            )
            return False

    elif current_os in ("macos", "linux"):
        logger.debug(
            "Unix-like OS detected (%s). No asyncio event loop patches required.",
            current_os,
        )
        _PATCHES_APPLIED = True
        return False

    else:
        logger.warning(
            "Unknown OS detected. Skipping asyncio patches. "
            "If async issues occur, manual intervention may be required."
        )
        _PATCHES_APPLIED = True
        return False


def reset_patches_state() -> None:
    """Reset the internal state tracking for testing purposes.

    This function should ONLY be used in unit tests to verify that
    the patching logic executes correctly on subsequent calls.
    """
    global _PATCHES_APPLIED
    _PATCHES_APPLIED = False
    logger.debug("OS compatibility patch state has been reset.")
