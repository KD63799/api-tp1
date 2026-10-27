# TP1 — Pilotage de Docker Engine par son API

## Contenu du dépôt
- docker_inventory.py : inventaire JSON + CSV (httpx, socket Unix, --all)
- docker-inventory.ps1 : inventaire PowerShell (Invoke-RestMethod -UnixSocket)
- docker_lifecycle.py : cycle de vie d'un conteneur et gestion des codes HTTP (201, 204, 304, 404, 409)

## Note sur le versionnement de l'API
Le démon Docker utilisé lors du TP est en version 29.1.3 (ApiVersion: 1.52, MinAPIVersion: 1.44). Le préfixe /v1.43/ initialement proposé étant inférieur à MinAPIVersion, il a été mis à jour vers /v1.52/ afin de respecter le contrat du démon.

## Exécution
    source ../.venv/bin/activate
    python3 docker_inventory.py --all
    pwsh ./docker-inventory.ps1
    python3 docker_lifecycle.py

---

## Réponses aux questions d'étape & Points d'analyse

### 1. Différence entre State et Status dans /containers/json
- **State** : Représente l'état machine discret et normalisé du conteneur sous forme d'énumération (created, running, paused, restarting, removing, exited, dead). Il est destiné à être parsé par des scripts d'automatisation.
- **Status** : Chaîne de caractères formatée pour la lecture humaine (ex. "Up 12 minutes", "Exited (0) 3 seconds ago"), utilisée notamment pour l'affichage direct de la commande CLI docker ps.

### 2. Pourquoi GET /containers/json et non GET /containers ?
Il s'agit d'un héritage historique des premières versions de l'API Docker (avant la formalisation stricte des conventions REST et l'utilisation systématique de l'en-tête Accept: application/json). À l'origine, le suffixe /json indiquait explicitement le format de représentation souhaité dans l'URI. Il a été conservé par souci de rétrocompatibilité, illustrant qu'une API industrielle réelle s'écarte parfois d'un design REST purement académique.

### 3. Gestion des erreurs avec raise_for_status() et exceptions
Dans docker_inventory.py, l'utilisation conjointe de httpx.ConnectError et r.raise_for_status() (httpx.HTTPStatusError) permet de séparer deux familles d'incidents :
- **Erreur de transport / réseau (ConnectError)** : Le socket Unix est inaccessible ou le démon est éteint (code retour 2). Une relance après démarrage du service ou correction des droits est envisageable.
- **Erreur applicative HTTP 4xx/5xx (HTTPStatusError)** : Le démon a bien répondu mais refuse la requête (version d'API obsolète, ressource introuvable, paramètres invalides — code retour 1). Il faut alors extraire et lire le champ message du corps JSON retourné par l'API.

### 4. Jointure côté client (Conteneurs / Images)
L'endpoint /containers/json fournit l'ImageID mais pas la taille de l'image (Size). Comme l'API Docker est orientée ressources (et non requêtes relationnelles ou GraphQL), il n'existe pas d'endpoint combiné : le client doit effectuer deux requêtes (GET /containers/json puis GET /images/json) et réaliser la jointure en mémoire via un dictionnaire indexé par Id.

### 5. Sémantique des codes HTTP dans le cycle de vie (docker_lifecycle.py)
Chaque code HTTP traduit l'état exact de la ressource et dicte la décision du script d'administration :
- **201 Created** : Ressource créée avec succès (POST /containers/create).
- **204 No Content** : Action exécutée avec succès sans corps de réponse (start ou delete).
- **304 Not Modified** : Le conteneur est déjà dans l'état cible (déjà démarré lors d'un start). Ce n'est pas une erreur mais une confirmation d'idempotence.
- **404 Not Found** : La ressource ciblée n'existe pas. Lors d'un DELETE, interpréter le 404 comme un succès garantit l'idempotence de la suppression.
- **409 Conflict** : L'état actuel du système empêche l'opération (nom de conteneur déjà utilisé à la création, ou tentative de suppression d'un conteneur en cours d'exécution avec force=false).
