from __future__ import annotations

import ctypes
import os
import tempfile
from contextlib import suppress
from ctypes import wintypes
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol, cast

from mailmap.session_model import validate_session_account_key

SECRET_STORE_FORMAT_VERSION = 1

_FORMAT_MAGIC = b"MAILCLEANUP-DPAPI\x00"
_FORMAT_VERSION_BYTES = 2
_MAX_PLAINTEXT_BYTES = 64 * 1024
_MAX_ENCRYPTED_BYTES = 128 * 1024
_CRYPTPROTECT_UI_FORBIDDEN = 0x1


class SecretStoreErrorCode(StrEnum):
    UNAVAILABLE = "unavailable"
    ENCRYPT_FAILED = "encrypt_failed"
    DECRYPT_FAILED = "decrypt_failed"
    IO_FAILED = "io_failed"
    CORRUPT = "corrupt"


class SecretStoreError(RuntimeError):
    def __init__(self, code: SecretStoreErrorCode) -> None:
        if not isinstance(code, SecretStoreErrorCode):
            raise TypeError("code must be a SecretStoreErrorCode")
        self.code = code
        super().__init__(code.value)

    def __repr__(self) -> str:
        return f"SecretStoreError(code={self.code.value!r})"


class DataProtectorPort(Protocol):
    def protect(self, plaintext: bytes) -> bytes: ...

    def unprotect(self, ciphertext: bytes) -> bytes: ...


class _DpapiBackendPort(Protocol):
    def protect(self, plaintext: bytes, *, flags: int) -> bytes: ...

    def unprotect(self, ciphertext: bytes, *, flags: int) -> bytes: ...


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _input_blob(data: bytes) -> tuple[_DataBlob, Any]:
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    pointer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
    blob = _DataBlob(len(data), pointer)
    return blob, buffer


class _CtypesDpapiBackend:
    def __init__(self) -> None:
        if os.name != "nt":
            raise SecretStoreError(SecretStoreErrorCode.UNAVAILABLE)
        try:
            win_dll = cast(Any, ctypes.WinDLL)
            self._crypt32 = win_dll("crypt32", use_last_error=True)
            self._kernel32 = win_dll("kernel32", use_last_error=True)
            self._crypt32.CryptProtectData.argtypes = [
                ctypes.POINTER(_DataBlob),
                wintypes.LPCWSTR,
                ctypes.POINTER(_DataBlob),
                wintypes.LPVOID,
                wintypes.LPVOID,
                wintypes.DWORD,
                ctypes.POINTER(_DataBlob),
            ]
            self._crypt32.CryptProtectData.restype = wintypes.BOOL
            self._crypt32.CryptUnprotectData.argtypes = [
                ctypes.POINTER(_DataBlob),
                ctypes.POINTER(wintypes.LPWSTR),
                ctypes.POINTER(_DataBlob),
                wintypes.LPVOID,
                wintypes.LPVOID,
                wintypes.DWORD,
                ctypes.POINTER(_DataBlob),
            ]
            self._crypt32.CryptUnprotectData.restype = wintypes.BOOL
            self._kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
            self._kernel32.LocalFree.restype = wintypes.HLOCAL
        except Exception:
            raise SecretStoreError(SecretStoreErrorCode.UNAVAILABLE) from None

    def protect(self, plaintext: bytes, *, flags: int) -> bytes:
        input_blob, input_buffer = _input_blob(plaintext)
        output_blob = _DataBlob()
        try:
            result = self._crypt32.CryptProtectData(
                ctypes.byref(input_blob),
                None,
                None,
                None,
                None,
                flags,
                ctypes.byref(output_blob),
            )
            del input_buffer
            if not result:
                code = (
                    SecretStoreErrorCode.UNAVAILABLE
                    if ctypes.get_last_error() == 2
                    else SecretStoreErrorCode.ENCRYPT_FAILED
                )
                raise SecretStoreError(code)
            return bytes(ctypes.string_at(output_blob.pbData, output_blob.cbData))
        except SecretStoreError:
            raise
        except Exception:
            raise SecretStoreError(SecretStoreErrorCode.ENCRYPT_FAILED) from None
        finally:
            if output_blob.pbData:
                self._kernel32.LocalFree(
                    ctypes.cast(output_blob.pbData, wintypes.HLOCAL)
                )

    def unprotect(self, ciphertext: bytes, *, flags: int) -> bytes:
        input_blob, input_buffer = _input_blob(ciphertext)
        output_blob = _DataBlob()
        description = wintypes.LPWSTR()
        try:
            result = self._crypt32.CryptUnprotectData(
                ctypes.byref(input_blob),
                ctypes.byref(description),
                None,
                None,
                None,
                flags,
                ctypes.byref(output_blob),
            )
            del input_buffer
            if not result:
                code = (
                    SecretStoreErrorCode.UNAVAILABLE
                    if ctypes.get_last_error() == 2
                    else SecretStoreErrorCode.DECRYPT_FAILED
                )
                raise SecretStoreError(code)
            return bytes(ctypes.string_at(output_blob.pbData, output_blob.cbData))
        except SecretStoreError:
            raise
        except Exception:
            raise SecretStoreError(SecretStoreErrorCode.DECRYPT_FAILED) from None
        finally:
            if output_blob.pbData:
                self._kernel32.LocalFree(
                    ctypes.cast(output_blob.pbData, wintypes.HLOCAL)
                )
            if description:
                self._kernel32.LocalFree(ctypes.cast(description, wintypes.HLOCAL))


class WindowsDpapiProtector:
    def __init__(self, backend: _DpapiBackendPort | None = None) -> None:
        self._backend = backend or _CtypesDpapiBackend()

    def protect(self, plaintext: bytes) -> bytes:
        if not isinstance(plaintext, bytes) or not 0 < len(plaintext) <= _MAX_PLAINTEXT_BYTES:
            raise SecretStoreError(SecretStoreErrorCode.ENCRYPT_FAILED)
        try:
            encrypted = self._backend.protect(
                plaintext,
                flags=_CRYPTPROTECT_UI_FORBIDDEN,
            )
        except SecretStoreError:
            raise
        except Exception:
            raise SecretStoreError(SecretStoreErrorCode.ENCRYPT_FAILED) from None
        if not isinstance(encrypted, bytes) or not encrypted:
            raise SecretStoreError(SecretStoreErrorCode.ENCRYPT_FAILED)
        return encrypted

    def unprotect(self, ciphertext: bytes) -> bytes:
        if (
            not isinstance(ciphertext, bytes)
            or not 0 < len(ciphertext) <= _MAX_ENCRYPTED_BYTES
        ):
            raise SecretStoreError(SecretStoreErrorCode.DECRYPT_FAILED)
        try:
            plaintext = self._backend.unprotect(
                ciphertext,
                flags=_CRYPTPROTECT_UI_FORBIDDEN,
            )
        except SecretStoreError:
            raise
        except Exception:
            raise SecretStoreError(SecretStoreErrorCode.DECRYPT_FAILED) from None
        if not isinstance(plaintext, bytes) or not 0 < len(plaintext) <= _MAX_PLAINTEXT_BYTES:
            raise SecretStoreError(SecretStoreErrorCode.DECRYPT_FAILED)
        return plaintext


class WindowsSecretStore:
    def __init__(
        self,
        directory: Path | None = None,
        protector: DataProtectorPort | None = None,
    ) -> None:
        self._directory = directory or self.default_directory()
        self._protector = protector or WindowsDpapiProtector()

    @staticmethod
    def default_directory() -> Path:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise SecretStoreError(SecretStoreErrorCode.UNAVAILABLE)
        return Path(local_app_data) / "MailCleanup" / "credentials"

    @property
    def directory(self) -> Path:
        return self._directory

    def credential_path(self, account_key: str) -> Path:
        validated = validate_session_account_key(account_key)
        return self._directory / f"{validated}.credential"

    def save(self, account_key: str, plaintext: bytes) -> None:
        path = self.credential_path(account_key)
        if not isinstance(plaintext, bytes) or not 0 < len(plaintext) <= _MAX_PLAINTEXT_BYTES:
            raise SecretStoreError(SecretStoreErrorCode.CORRUPT)
        try:
            ciphertext = self._protector.protect(plaintext)
        except SecretStoreError:
            raise
        except Exception:
            raise SecretStoreError(SecretStoreErrorCode.ENCRYPT_FAILED) from None
        if not isinstance(ciphertext, bytes) or not 0 < len(ciphertext) <= _MAX_ENCRYPTED_BYTES:
            raise SecretStoreError(SecretStoreErrorCode.ENCRYPT_FAILED)
        envelope = (
            _FORMAT_MAGIC
            + SECRET_STORE_FORMAT_VERSION.to_bytes(_FORMAT_VERSION_BYTES, "big")
            + ciphertext
        )

        temporary_path: Path | None = None
        descriptor: int | None = None
        try:
            self._directory.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{account_key}.",
                suffix=".tmp",
                dir=self._directory,
            )
            temporary_path = Path(temporary_name)
            with os.fdopen(descriptor, "wb") as temporary_file:
                descriptor = None
                temporary_file.write(envelope)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, path)
            temporary_path = None
        except Exception:
            raise SecretStoreError(SecretStoreErrorCode.IO_FAILED) from None
        finally:
            if descriptor is not None:
                with suppress(OSError):
                    os.close(descriptor)
            if temporary_path is not None:
                with suppress(OSError):
                    temporary_path.unlink(missing_ok=True)

    def load(self, account_key: str) -> bytes | None:
        path = self.credential_path(account_key)
        try:
            envelope = path.read_bytes()
        except FileNotFoundError:
            return None
        except OSError:
            raise SecretStoreError(SecretStoreErrorCode.IO_FAILED) from None
        header_length = len(_FORMAT_MAGIC) + _FORMAT_VERSION_BYTES
        if len(envelope) <= header_length or not envelope.startswith(_FORMAT_MAGIC):
            raise SecretStoreError(SecretStoreErrorCode.CORRUPT)
        version = int.from_bytes(
            envelope[len(_FORMAT_MAGIC) : header_length],
            "big",
        )
        if version != SECRET_STORE_FORMAT_VERSION:
            raise SecretStoreError(SecretStoreErrorCode.CORRUPT)
        ciphertext = envelope[header_length:]
        if len(ciphertext) > _MAX_ENCRYPTED_BYTES:
            raise SecretStoreError(SecretStoreErrorCode.CORRUPT)
        try:
            return self._protector.unprotect(ciphertext)
        except SecretStoreError:
            raise
        except Exception:
            raise SecretStoreError(SecretStoreErrorCode.DECRYPT_FAILED) from None

    def delete(self, account_key: str) -> None:
        path = self.credential_path(account_key)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            raise SecretStoreError(SecretStoreErrorCode.IO_FAILED) from None
