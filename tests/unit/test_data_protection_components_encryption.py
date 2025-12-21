from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from src.security.data_protection import (
    DataBackup,
    DataClassification,
    DataEncryption,
    DataMasking,
    DataProtection,
    EncryptionKey,
    EncryptionAlgorithm,
)


def test_data_encryption_generate_and_rotate_key_round_trip():
    encryption = DataEncryption()

    new_key_id = encryption.generate_key(EncryptionAlgorithm.FERNET, key_id="k1")
    assert new_key_id == "k1"
    assert encryption.get_key_info("k1") is not None

    encrypted = encryption.encrypt_data("hello", key_id="k1")
    assert encryption.decrypt_data(encrypted, key_id="k1") == b"hello"

    rotated_key_id = encryption.rotate_key("k1", new_key_id="k2")
    assert rotated_key_id == "k2"
    assert encryption.get_key_info("k1") is not None
    assert encryption.get_key_info("k1").is_active is False
    assert encryption.get_key_info("k2") is not None


def test_data_encryption_list_keys_contains_defaults():
    encryption = DataEncryption()
    key_ids = {key.key_id for key in encryption.list_keys()}
    assert "default_fernet" in key_ids
    assert "default_aes" in key_ids


def test_data_encryption_rotate_unknown_key_raises():
    encryption = DataEncryption()
    with pytest.raises(ValueError, match="密钥不存在"):
        encryption.rotate_key("missing")


def test_data_encryption_unsupported_algorithm_raises():
    encryption = DataEncryption()
    encryption.encryption_keys["bad_algo"] = EncryptionKey(
        key_id="bad_algo",
        algorithm=EncryptionAlgorithm.RSA2048,
        key_data=b"unused",
        created_at=datetime.now(),
    )
    with pytest.raises(ValueError, match="不支持的加密算法"):
        encryption.encrypt_data("hello", key_id="bad_algo")
    with pytest.raises(ValueError, match="不支持的加密算法"):
        encryption.decrypt_data(b"cipher", key_id="bad_algo")


def test_data_encryption_generate_key_auto_id_and_aes_branch():
    encryption = DataEncryption()
    key_id = encryption.generate_key(EncryptionAlgorithm.AES256)
    assert key_id.startswith("aes256_")
    assert encryption.get_key_info(key_id) is not None


def test_data_encryption_generate_key_unsupported_algorithm_raises():
    encryption = DataEncryption()
    with pytest.raises(ValueError, match="不支持的算法"):
        encryption.generate_key(EncryptionAlgorithm.RSA2048)


def test_data_encryption_legacy_cbc_invalid_padding_raises():
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    encryption = DataEncryption()
    key = b"\x00" * 32
    iv = b"\x01" * 16
    plaintext = b"A" * 15 + b"\x00"  # last byte => padding_length=0 (invalid)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()

    with pytest.raises(ValueError, match="AES-CBC 填充无效"):
        encryption._decrypt_legacy_cbc(iv + ciphertext, key)


def test_data_encryption_legacy_cbc_valid_padding_round_trip():
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    encryption = DataEncryption()
    key = b"\x00" * 32
    iv = b"\x02" * 16
    plaintext = b"A" * 15 + b"\x01"  # padding_length=1

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()

    assert encryption._decrypt_legacy_cbc(iv + ciphertext, key) == b"A" * 15


def test_data_masking_default_rules_and_inference():
    masking = DataMasking()

    masked_email = masking.mask_data("alice@example.com", "email")
    assert "***@" in masked_email

    masked_phone = masking.mask_data("13812345678", "phone")
    assert "****" in masked_phone

    data = {"email_address": "bob@example.com", "phone": "13812345678", "note": 123}
    masked = masking.mask_dict(data, ["email_address", "phone", "note"])
    assert masked["email_address"] != data["email_address"]
    assert masked["phone"] != data["phone"]
    assert masked["note"] == 123


def test_data_backup_create_and_restore_encrypted_file(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    source = source_dir / "data.txt"
    source.write_text("secret", encoding="utf-8")

    backup = DataBackup(str(backup_dir))
    backup_path = backup.create_backup(str(source), backup_name="b1", encrypt=True)
    assert backup_path.endswith(".encrypted")
    assert os.path.exists(backup_path)

    restore_dir = tmp_path / "restore"
    restore_dir.mkdir()
    restored = restore_dir / "restored.txt"
    assert backup.restore_backup(backup_path, str(restored), decrypt=True) is True
    assert restored.read_text(encoding="utf-8") == "secret"


def test_data_backup_list_backups_and_cleanup(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    source = source_dir / "data.txt"
    source.write_text("secret", encoding="utf-8")

    backup = DataBackup(str(backup_dir))
    backup.create_backup(str(source), backup_name="b1", encrypt=False)

    backups = backup.list_backups()
    assert len(backups) == 1
    assert backups[0]["encrypted"] is False

    # 清理阈值=0天 => 立即清理
    cleaned = backup.cleanup_old_backups(days=0)
    assert cleaned == 1
    assert backup.list_backups() == []


def test_data_backup_directory_zip_round_trip(tmp_path: Path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    source_dir = tmp_path / "src_dir"
    source_dir.mkdir()
    (source_dir / "a.txt").write_text("A", encoding="utf-8")

    backup = DataBackup(str(backup_dir))
    backup_path = backup.create_backup(str(source_dir), backup_name="dir1", encrypt=False)
    assert backup_path.endswith(".zip")
    assert os.path.exists(backup_path)

    restore_dir = tmp_path / "restore_dir"
    restore_dir.mkdir()
    assert backup.restore_backup(backup_path, str(restore_dir), decrypt=False) is True
    assert (restore_dir / "a.txt").read_text(encoding="utf-8") == "A"


def test_data_protection_protect_unprotect_dict_with_masking():
    protection = DataProtection()
    protection.classify_data("d1", DataClassification.SECRET, _owner="u1")

    raw = {"email": "alice@example.com", "phone": "13812345678"}
    protected = protection.protect_data(raw, data_id="d1", encrypt=True, mask=True)
    assert isinstance(protected, (bytes, bytearray))

    unprotected = protection.unprotect_data(protected, _data_id="d1", decrypt=True)
    assert isinstance(unprotected, dict)
    assert unprotected["email"] != raw["email"]
    assert unprotected["phone"] != raw["phone"]


def test_data_protection_unprotect_returns_original_on_decrypt_failure():
    protection = DataProtection()
    bogus = b"not-a-valid-fernet-token"
    assert protection.unprotect_data(bogus, _data_id="d1", decrypt=True) == bogus


def test_data_protection_create_and_restore_data_backup(tmp_path: Path):
    protection = DataProtection(backup_dir=str(tmp_path))
    backup_path = protection.create_data_backup({"x": 1}, backup_name="d1")
    assert backup_path.endswith(".backup.encrypted")
    restored = protection.restore_data_backup(backup_path)
    assert restored == {"x": 1}


def test_data_protection_report_contains_key_counts(tmp_path: Path):
    protection = DataProtection(backup_dir=str(tmp_path))
    report = protection.get_protection_report()
    assert report["encryption_keys"] >= 2
    assert report["masking_rules"] >= 1
    assert "classification_distribution" in report
