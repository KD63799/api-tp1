#!/usr/bin/env python3
"""TP1 — Créer, démarrer, arrêter, supprimer un conteneur par l'API Docker.
Illustre la lecture des codes 201/204/304/404/409."""
import sys
from typing import Optional
import httpx

NAME, IMAGE, TAG = "tp1-demo", "nginx", "alpine"
client = httpx.Client(
    transport=httpx.HTTPTransport(uds="/var/run/docker.sock"),
    base_url="http://docker/v1.52",
    timeout=120,
)


def pull() -> None:
    with client.stream("POST", "/images/create", params={"fromImage": IMAGE, "tag": TAG}) as r:
        r.raise_for_status()
        for _ in r.iter_lines():
            pass
    print(f"[pull] image {IMAGE}:{TAG} disponible")


def create() -> Optional[str]:
    r = client.post("/containers/create", params={"name": NAME}, json={"Image": f"{IMAGE}:{TAG}"})
    if r.status_code == 409:
        print(f"[create] 409 Conflict : {r.json()['message']}")
        return None
    r.raise_for_status()
    cid = r.json()["Id"]
    print(f"[create] 201 Created → id {cid[:12]}")
    return cid


def start() -> None:
    r = client.post(f"/containers/{NAME}/start")
    print(f"[start] {r.status_code} ({'déjà démarré' if r.status_code == 304 else 'démarré'})")
    if r.status_code not in (204, 304):
        r.raise_for_status()


def remove(force: bool) -> None:
    r = client.delete(f"/containers/{NAME}", params={"force": str(force).lower()})
    if r.status_code == 404:
        print("[delete] 404 : déjà absent → idempotence, on continue")
    elif r.status_code == 409:
        print(f"[delete] 409 : {r.json()['message']} (conteneur actif, force=false)")
    elif r.status_code == 204:
        print("[delete] 204 : supprimé")
    else:
        r.raise_for_status()


if __name__ == "__main__":
    pull()
    create()
    create()             # → 409 attendu (démonstration)
    start()
    start()              # → 304 attendu
    remove(force=False)  # → 409 attendu (il tourne)
    remove(force=True)   # → 204
    remove(force=True)   # → 404 attendu (déjà parti)
    sys.exit(0)
