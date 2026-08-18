from __future__ import annotations

import uvicorn


def run() -> None:
    """Inicia exclusivamente en loopback; nunca publica el servicio en la red local."""

    uvicorn.run("mailmap.api:app", host="127.0.0.1", port=8765, reload=False)


if __name__ == "__main__":
    run()
