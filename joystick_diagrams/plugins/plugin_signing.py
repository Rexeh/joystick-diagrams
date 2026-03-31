"""Plugin signing and verification using Ed25519.

Verifies that plugins are signed by the Joystick Diagrams developer
using an embedded public key. Unsigned plugins require explicit user trust.
"""

import base64
import hashlib
import logging
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

_logger = logging.getLogger(__name__)

_DEVELOPER_PUBLIC_KEY_B64 = "vsk7IsZ9nnfBLUHE4dOP+2sow3C1444UAKtwOGA6NPA="

SIGNATURE_FILENAME = "plugin.sig"
EXCLUDED_PATHS = {"plugin.sig", "__pycache__"}


def _get_public_key() -> Ed25519PublicKey | None:
    """Load the embedded developer public key."""
    if _DEVELOPER_PUBLIC_KEY_B64 == "REPLACE_WITH_REAL_PUBLIC_KEY_BASE64":
        _logger.debug("Developer public key not configured yet")
        return None

    try:
        key_bytes = base64.b64decode(_DEVELOPER_PUBLIC_KEY_B64)
        return Ed25519PublicKey.from_public_bytes(key_bytes)
    except Exception as e:
        _logger.error(f"Failed to load developer public key: {e}")
        return None


def compute_plugin_digest(plugin_path: Path) -> bytes:
    """Compute a deterministic SHA-256 digest of a plugin's contents.

    Iterates all files in the plugin directory (excluding plugin.sig
    and __pycache__), sorted by relative path, and builds a hash from
    each file's relative path and its SHA-256 content hash.
    """
    hasher = hashlib.sha256()

    all_files = sorted(
        f.relative_to(plugin_path)
        for f in plugin_path.rglob("*")
        if f.is_file() and not any(part in EXCLUDED_PATHS for part in f.parts)
    )

    for rel_path in all_files:
        # Skip files under excluded directories
        if any(part in EXCLUDED_PATHS for part in rel_path.parts):
            continue

        abs_path = plugin_path / rel_path
        file_hash = hashlib.sha256(abs_path.read_bytes()).hexdigest()
        hasher.update(str(rel_path).encode("utf-8"))
        hasher.update(file_hash.encode("utf-8"))

    return hasher.digest()


def is_plugin_signed(plugin_path: Path) -> bool:
    """Check whether a plugin directory contains a signature file."""
    return (plugin_path / SIGNATURE_FILENAME).is_file()


def verify_plugin_signature(plugin_path: Path) -> bool:
    """Verify a plugin's signature against the embedded developer public key.

    Returns True if the plugin has a valid signature from the developer.
    Returns False if unsigned, signature is invalid, or public key is not configured.
    """
    sig_file = plugin_path / SIGNATURE_FILENAME
    if not sig_file.is_file():
        _logger.debug(f"No signature file found in {plugin_path}")
        return False

    public_key = _get_public_key()
    if public_key is None:
        return False

    try:
        signature = base64.b64decode(sig_file.read_text(encoding="utf-8").strip())
    except Exception as e:
        _logger.warning(f"Failed to read signature file: {e}")
        return False

    digest = compute_plugin_digest(plugin_path)

    try:
        public_key.verify(signature, digest)
        _logger.info(f"Plugin signature verified for {plugin_path.name}")
        return True
    except InvalidSignature:
        _logger.warning(f"Invalid signature for plugin {plugin_path.name}")
        return False
    except Exception as e:
        _logger.error(f"Signature verification error: {e}")
        return False
