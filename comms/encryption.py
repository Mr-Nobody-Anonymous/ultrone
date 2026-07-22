# Copyright (c) Ultrone Contributors. All rights reserved.
"""Simulated military-grade communications security."""

import hashlib
import hmac
import os
from typing import Tuple


def generate_keypair() -> Tuple[bytes, bytes]:
    """Generate a simulated public/private key pair for secure communications."""
    private_key = os.urandom(32)
    public_key = hashlib.sha256(private_key).digest()
    return public_key, private_key


def encrypt_message(message: str, key: bytes) -> str:
    """
    Simulate message encryption.
    
    In simulation mode, this applies a deterministic transformation
    that would represent real cryptographic encryption.
    """
    # Simulated encryption: HMAC-based with key derivation
    derived_key = hashlib.sha256(key).digest()
    signature = hmac.new(derived_key, message.encode(), hashlib.sha256).hexdigest()
    # Return encoded "ciphertext" (simulated)
    return f"{signature}:{message}"


def decrypt_message(ciphertext: str, key: bytes) -> str:
    """
    Simulate message decryption.
    
    In simulation mode, extracts the original message.
    """
    # Simulated decryption: extract original message
    if ":" in ciphertext:
        _, message = ciphertext.split(":", 1)
        return message
    return ciphertext


def verify_integrity(message: str, signature: str, key: bytes) -> bool:
    """Verify message integrity using HMAC."""
    expected_sig = hmac.new(
        hashlib.sha256(key).digest(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_sig, signature)