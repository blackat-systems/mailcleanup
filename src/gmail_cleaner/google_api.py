from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
METADATA_HEADERS = [
    "From",
    "Subject",
    "Date",
    "List-Unsubscribe",
    "List-Unsubscribe-Post",
    "Authentication-Results",
    "DKIM-Signature",
]


def gmail_service(credentials_file: Path, token_file: Path):
    credentials: Credentials | None = None
    if token_file.exists():
        credentials = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not credentials_file.exists():
                raise FileNotFoundError(
                    f"Falta {credentials_file}. Descargá allí el cliente OAuth de escritorio."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
            credentials = flow.run_local_server(port=0)
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(credentials.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def label_ids_by_name(service: Any, names: list[str]) -> set[str]:
    wanted = {name.casefold() for name in names}
    response = service.users().labels().list(userId="me").execute()
    return {
        str(label["id"])
        for label in response.get("labels", [])
        if str(label.get("name", "")).casefold() in wanted
    }


def iter_message_ids(service: Any, query: str, max_messages: int) -> Iterator[str]:
    token: str | None = None
    yielded = 0
    while yielded < max_messages:
        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                maxResults=min(500, max_messages - yielded),
                pageToken=token,
            )
            .execute()
        )
        for message in response.get("messages", []):
            yield str(message["id"])
            yielded += 1
            if yielded >= max_messages:
                return
        token = response.get("nextPageToken")
        if not token:
            return


def get_metadata(service: Any, message_id: str) -> dict[str, Any]:
    return (
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=METADATA_HEADERS,
        )
        .execute()
    )


def trash_messages(service: Any, message_ids: list[str]) -> None:
    for start in range(0, len(message_ids), 1000):
        chunk = message_ids[start : start + 1000]
        (
            service.users()
            .messages()
            .batchModify(
                userId="me",
                body={"ids": chunk, "addLabelIds": ["TRASH"]},
            )
            .execute()
        )
