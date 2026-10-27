#!/usr/bin/env python3
"""TP1 — Inventaire des conteneurs via l'API Docker Engine (socket Unix).
Sorties : inventaire.json et inventaire.csv
Usage : python3 docker_inventory.py [--all]
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path
import httpx

DOCKER_SOCKET = "/var/run/docker.sock"
API_VERSION = "v1.52"


def make_client() -> httpx.Client:
    """Client HTTP branché sur le socket Unix du démon Docker."""
    transport = httpx.HTTPTransport(uds=DOCKER_SOCKET)
    return httpx.Client(transport=transport, base_url=f"http://docker/{API_VERSION}", timeout=10)


def format_ports(ports: list[dict]) -> str:
    """[{'PrivatePort':80,'PublicPort':8081,'Type':'tcp',...}] → '0.0.0.0:8081->80/tcp'."""
    rendu = set()
    for p in ports:
        if "PublicPort" in p:
            rendu.add(f"{p.get('IP', '0.0.0.0')}:{p['PublicPort']}->{p['PrivatePort']}/{p['Type']}")
        else:
            rendu.add(f"{p['PrivatePort']}/{p['Type']}")
    return ", ".join(sorted(rendu))


def collect(client: httpx.Client, include_stopped: bool) -> list[dict]:
    r = client.get("/containers/json", params={"all": str(include_stopped).lower()})
    r.raise_for_status()
    images = {i["Id"]: i for i in client.get("/images/json").raise_for_status().json()}
    inventaire = []
    for c in r.json():
        img = images.get(c["ImageID"], {})
        inventaire.append({
            "nom": c["Names"][0].lstrip("/"),
            "id": c["Id"][:12],
            "image": c["Image"],
            "image_taille_Mo": round(img.get("Size", 0) / 1_000_000, 1),
            "etat": c["State"],
            "statut": c["Status"],
            "ports": format_ports(c.get("Ports", [])),
        })
    return inventaire


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="inclure les conteneurs arrêtés")
    args = parser.parse_args()
    try:
        with make_client() as client:
            inventaire = collect(client, include_stopped=args.all)
    except httpx.ConnectError:
        print(
            f"[ERREUR] Démon Docker injoignable sur {DOCKER_SOCKET} "
            "(service arrêté ? pas dans le groupe docker ?)",
            file=sys.stderr,
        )
        return 2
    except httpx.HTTPStatusError as exc:
        detail = exc.response.json().get("message", exc.response.text)
        print(f"[ERREUR] API Docker {exc.response.status_code} : {detail}", file=sys.stderr)
        return 1

    Path("inventaire.json").write_text(
        json.dumps(inventaire, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    champs = ["nom", "id", "image", "image_taille_Mo", "etat", "statut", "ports"]
    with open("inventaire.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=champs)
        w.writeheader()
        w.writerows(inventaire)

    print(f"{len(inventaire)} conteneur(s) → inventaire.json / inventaire.csv")
    for c in inventaire:
        print(f" - {c['nom']:<10} {c['etat']:<8} {c['image']:<20} {c['ports']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
