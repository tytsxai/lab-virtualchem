from __future__ import annotations

from datetime import datetime

import pytest

from src.security.data_protection import (
    DataEncryption,
    EncryptionAlgorithm,
    EncryptionKey,
    GCM_HEADER,
    GCM_NONCE_SIZE,
)


def test_encrypt_data_unknown_key_id_raises_value_error():
    encryption = DataEncryption()
    with pytest.raises(ValueError, match="密钥不存在"):
        encryption.encrypt_data("hello", key_id="does_not_exist")


def test_decrypt_data_unknown_key_id_raises_value_error():
    encryption = DataEncryption()
    with pytest.raises(ValueError, match="密钥不存在"):
        encryption.decrypt_data(b"cipher", key_id="does_not_exist")


def test_encrypt_data_aes_invalid_key_length_raises_value_error():
    encryption = DataEncryption()
    encryption.encryption_keys["bad_aes"] = EncryptionKey(
        key_id="bad_aes",
        algorithm=EncryptionAlgorithm.AES256,
        key_data=b"short_key",
        created_at=datetime.now(),
    )
    with pytest.raises(ValueError, match="AES密钥长度必须"):
        encryption.encrypt_data("hello", key_id="bad_aes")


def test_decrypt_data_aes_gcm_invalid_length_raises_value_error():
    encryption = DataEncryption()
    encryption.encryption_keys["good_aes"] = EncryptionKey(
        key_id="good_aes",
        algorithm=EncryptionAlgorithm.AES256,
        key_data=b"\x00" * 32,
        created_at=datetime.now(),
    )

    # header + nonce + (missing tag/ciphertext)
    invalid_ciphertext = GCM_HEADER + (b"\x01" * GCM_NONCE_SIZE) + b"\x02"
    with pytest.raises(ValueError, match="AES-GCM 密文长度无效"):
        encryption.decrypt_data(invalid_ciphertext, key_id="good_aes")


def test_decrypt_data_legacy_cbc_too_short_raises_value_error():
    encryption = DataEncryption()
    encryption.encryption_keys["good_aes"] = EncryptionKey(
        key_id="good_aes",
        algorithm=EncryptionAlgorithm.AES256,
        key_data=b"\x00" * 32,
        created_at=datetime.now(),
    )

    # Not starting with GCM header -> legacy CBC path, but too short for IV.
    with pytest.raises(ValueError, match="AES-CBC 密文长度无效"):
        encryption.decrypt_data(b"\x00" * 15, key_id="good_aes")

