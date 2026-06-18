# Cahier des charges technique — Plateforme e-INSS

> **À l'attention de Claude.** Ce document est un brief de réalisation. Construis la plateforme décrite ci-dessous en suivant la stack, l'architecture, le modèle de données et les contrats d'API imposés. Procède par étapes (voir §13 — Plan de livraison), demande validation à la fin de chaque lot, et n'invente pas de fonctionnalités hors périmètre. Quand une décision n'est pas spécifiée, choisis l'option la plus simple, sécurisée et documentée, et signale-la.

---

## 1. Contexte et objectif

L'Institut National de Sécurité Sociale (INSS) de la République de Guinée-Bissau souhaite une plateforme nationale de protection sociale dématérialisée, **e-INSS**. La plateforme gère l'affiliation des assurés, les cotisations, et délivre une **Carte d'Assurance Maladie Digitale** vérifiable en temps réel par les prestataires de soins.

**Objectif de ce projet :** livrer une application web complète (backend + frontend + API) couvrant l'ensemble des espaces (citoyen, entreprise, agent INSS, prestataire) et le module carte digitale.

---

## 2. Stack technique imposée

| Couche | Technologie | Version cible |
|---|---|---|
| Langage backend | Python | 3.12+ |
| Framework | Django + Django REST Framework | Django 5.x, DRF 3.15+ |
| Base de données | PostgreSQL | 16+ |
| Authentification API | JWT (djangorestframework-simplejwt) | dernière stable |
| Génération PDF | WeasyPrint | dernière stable |
| QR Code | `qrcode` + `Pillow` | dernière stable |
| Cryptographie token | `PyJWT` (JWS signé) + `cryptography` | dernière stable |
| Tâches asynchrones | Celery + Redis | dernière stable |
| Frontend | Django Templates + HTMX + Tailwind CSS | — |
| Tests | pytest + pytest-django + factory_boy | dernière stable |
| Conteneurisation | Docker + docker-compose | — |
| Qualité | ruff (lint), black (format), mypy (typage) | dernière stable |

**Contraintes :**
- API REST versionnée sous `/api/v1/`.
- Interface utilisateur en **portugais** (langue par défaut), architecture i18n prête pour ajout de langues.
- Conception **mobile-first** et responsive.
- Aucune donnée personnelle en clair dans le QR Code.

---

## 3. Architecture générale

Organiser le projet en **applications Django modulaires**, une par domaine métier :

```
einss/
├── config/              # settings (base, dev, prod), urls, wsgi/asgi, celery
├── apps/
│   ├── accounts/        # utilisateurs, rôles, authentification, MFA
│   ├── affiliates/      # assurés, ayants-droit, statuts
│   ├── employers/       # entreprises, rattachement des employés
│   ├── contributions/   # cotisations, périodes, paiements
│   ├── cards/           # carte digitale, génération PDF, QR, tokens
│   ├── verification/    # service de vérification des droits (prestataires)
│   ├── audit/           # journalisation des actions et vérifications
│   └── notifications/   # notifications assurés (changement de statut)
├── templates/           # templates Django (espaces citoyen, entreprise, agent)
├── static/              # Tailwind, JS, assets
├── tests/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── manage.py
```

**Principes :**
- Séparation nette entre logique métier (services) et vues/serializers.
- Chaque app expose ses serializers, viewsets, services et tests.
- Les secrets et clés cryptographiques sont gérés via variables d'environnement (jamais en dur).

---

## 4. Acteurs et rôles

| Rôle | Description | Accès principal |
|---|---|---|
| `CITIZEN` | Assuré affilié | Espace citoyen : carte, documents, cotisations |
| `DEPENDENT` | Ayant-droit rattaché | Carte rattachée à l'assuré principal |
| `EMPLOYER` | Entreprise affiliante | Vérifier un employé, déclarer les cotisations |
| `AGENT` | Agent INSS | Gestion des affiliés, émission/suspension/révocation des cartes |
| `PROVIDER` | Prestataire de soins | Vérification des droits par scan du QR Code |
| `ADMIN` | Administrateur | Gestion complète, configuration, audit |

Implémenter un modèle d'autorisation basé sur les rôles (RBAC) avec **principe du moindre privilège**.

---

## 5. Modèle de données (entités principales)

Décrire les modèles Django suivants. Les champs listés sont indicatifs et à compléter selon les bonnes pratiques.

### 5.1 `accounts.User`
- `email` (unique), `password` (haché), `role` (énumération des rôles), `is_active`, `mfa_enabled`, `last_login`.
- Hérite de `AbstractBaseUser`. Authentification par email.

### 5.2 `affiliates.Affiliate`
- `user` (FK), `insss_number` (unique, format `NNN-NNN-NNN`), `health_number` (unique),
- `first_name`, `last_name`, `birth_date`, `photo`,
- `status` : `ACTIVE`, `RETIRED`, `DEPENDENT`, `SUSPENDED`, `REVOKED`,
- `primary_affiliate` (FK nullable, pour les ayants-droit),
- `created_at`, `updated_at`.

### 5.3 `employers.Employer`
- `name`, `registration_number` (unique), `address`, `contact_email`,
- relation M2M avec `Affiliate` (employés rattachés).

### 5.4 `contributions.Contribution`
- `affiliate` (FK), `period` (mois/année), `amount` (Decimal, devise XOF),
- `status` : `PENDING`, `PAID`, `LATE`, `due_date`, `paid_at`.

### 5.5 `cards.HealthCard`
- `affiliate` (OneToOne), `card_number` (unique), `issued_at`, `valid_from`, `valid_until`,
- `state` : `ACTIVE`, `SUSPENDED`, `REVOKED`,
- `current_token_jti` (identifiant du token QR en cours), `token_rotated_at`.

### 5.6 `verification.VerificationLog`
- `card` (FK), `provider` (FK User PROVIDER), `verified_at`, `result` (`VALID`, `INVALID`, `EXPIRED`, `SUSPENDED`), `ip_address`.

### 5.7 `audit.AuditEvent`
- `actor` (FK User), `action`, `target_type`, `target_id`, `timestamp`, `metadata` (JSON), `ip_address`.

**Règle :** toute action sensible (émission, suspension, révocation, vérification, changement de statut) génère un `AuditEvent` ou un `VerificationLog` horodaté.

---

## 6. Module Carte d'Assurance Maladie Digitale

### 6.1 Contenu de la carte
Nom et prénom, numéro INSS, numéro d'assurance maladie, date de naissance, statut, dates de validité, photo, QR Code, mention de signature numérique INSS.

### 6.2 Génération
- **Automatique** à l'affiliation (signal Django sur création d'`Affiliate` actif → création `HealthCard` + tâche Celery de génération).
- Carte disponible en **affichage web responsive**, **export PDF** (WeasyPrint) et **données pour wallet mobile** (endpoint JSON).

### 6.3 Mécanique du QR Code (sécurité centrale)
- Le QR encode un **token JWS signé** (clé privée INSS), contenant uniquement : `jti` (identifiant unique), `card_number`, `status`, `exp` (expiration courte, ex. 5 min), `iat`.
- **Aucune donnée personnelle en clair** dans le QR.
- Le `jti` est stocké côté serveur (`current_token_jti`) ; à chaque rotation, l'ancien `jti` est invalidé.
- La vérification se fait **côté serveur** : décodage + vérification de signature + contrôle que le `jti` est l'actif et non expiré + lecture de l'état des droits en base.
- **Rotation** : régénération périodique du token (tâche Celery) pour neutraliser la réutilisation de captures d'écran.

### 6.4 Design de la carte (PDF + écran)
- En-tête avec logo INSS, couleurs institutionnelles (bleu `#1F3864`, blanc, doré `#B8860B`).
- Photo ronde à gauche, QR Code à droite, bande inférieure avec numéro INSS.
- Style moderne, minimaliste, lisible, contraste conforme WCAG AA.

---

## 7. Contrats d'API (REST `/api/v1/`)

Implémenter au minimum les endpoints suivants, tous documentés (OpenAPI / drf-spectacular).

### Authentification
| Méthode | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/login/` | Connexion, renvoie tokens JWT |
| POST | `/api/v1/auth/refresh/` | Rafraîchit le token d'accès |
| POST | `/api/v1/auth/mfa/verify/` | Vérifie le second facteur |

### Cartes
| Méthode | Endpoint | Accès | Description |
|---|---|---|---|
| GET | `/api/v1/cards/{insss_number}/` | Assuré, Agent | Récupère la carte digitale |
| GET | `/api/v1/cards/{insss_number}/pdf/` | Assuré, Agent | Génère le PDF de la carte |
| POST | `/api/v1/cards/{insss_number}/token/` | Assuré | Émet/renouvelle le token QR |
| PATCH | `/api/v1/cards/{insss_number}/state/` | Agent | Suspend/révoque la carte |

### Vérification (prestataires)
| Méthode | Endpoint | Accès | Description |
|---|---|---|---|
| POST | `/api/v1/verify/` | Prestataire | Vérifie un token QR, renvoie l'état des droits |

**Réponse type de `/verify/` :**
```json
{
  "result": "VALID",
  "full_name": "João Silva",
  "insss_number": "004-589-221",
  "status": "ACTIVE",
  "valid_until": "2027-12-31",
  "verified_at": "2026-06-10T12:00:00Z"
}
```

### Assurés / Entreprises / Cotisations
- CRUD `affiliates`, `employers`, `contributions` selon les rôles (viewsets DRF avec permissions par rôle).
- `GET /api/v1/employers/{id}/employees/{insss_number}/status/` : vérification du statut d'un employé.

---

## 8. Interfaces utilisateur (templates)

### Espace Citoyen
- Tableau de bord, **Ma carte** (affichage + bouton wallet + téléchargement PDF), **Mes documents**, **Mes cotisations**, historique des vérifications.

### Espace Entreprise
- Liste des employés rattachés, vérification du statut d'un employé, déclaration des cotisations.

### Espace Agent INSS
- Recherche d'affiliés, gestion des affiliations, émission/suspension/révocation de carte, consultation de l'audit.

### Interface Prestataire
- Page de scan du QR (caméra ou saisie token), affichage du résultat de vérification (vert/rouge), sans exposition de données superflues.

Toutes les interfaces : responsive, mobile-first, en portugais, navigation claire.

---

## 9. Sécurité (exigences obligatoires)

| Domaine | Exigence |
|---|---|
| Mots de passe | Hachage Django (PBKDF2/Argon2), politique de complexité |
| MFA | Authentification forte pour l'accès à la carte |
| Chiffrement repos | Chiffrement des données personnelles sensibles |
| Transport | HTTPS/TLS obligatoire, en-têtes de sécurité (HSTS, CSP) |
| Token QR | JWS signé, expiration courte, rotation, `jti` invalidable |
| Habilitations | RBAC strict, permissions DRF par rôle |
| Audit | Journalisation horodatée de toute action sensible |
| Minimisation | Aucune donnée superflue dans QR/carte/API |
| Anti-bruteforce | Rate limiting sur login et `/verify/` |
| Protection OWASP | CSRF, XSS, injection (ORM), validation stricte des entrées |

---

## 10. Exigences non fonctionnelles

- **Performance** : vérification d'un QR en < 2 secondes.
- **Disponibilité** : service de vérification cible 99,5 %.
- **Scalabilité** : conçu pour une montée en charge nationale.
- **Accessibilité** : WCAG AA sur les interfaces citoyennes.
- **Maintenabilité** : code typé (mypy), linté (ruff), formaté (black), modulaire.
- **Couverture de tests** : ≥ 80 % sur la logique métier (services, génération/vérification token).

---

## 11. Configuration et déploiement

- `docker-compose` avec services : `web` (Django/Gunicorn), `db` (PostgreSQL), `redis`, `worker` (Celery), `beat` (Celery scheduler).
- Settings séparés : `base.py`, `dev.py`, `prod.py`.
- Variables d'environnement via fichier `.env` (fournir un `.env.example`).
- Migrations Django versionnées.
- Commande de **seed** (`manage.py seed_demo`) créant des comptes de démonstration pour chaque rôle et quelques affiliés/cartes de test.
- `README.md` : installation, lancement (`docker-compose up`), exécution des tests, comptes de démo.

---

## 12. Données de démonstration attendues

Au moins : 1 admin, 1 agent, 1 entreprise avec 2 employés, 3 assurés (dont 1 retraité et 1 ayant-droit), des cotisations sur 3 mois, des cartes générées, et quelques logs de vérification — pour permettre une démonstration immédiate.

---

## 13. Plan de livraison (procéder lot par lot, validation à chaque étape)

**Lot 0 — Fondations**
Initialisation du projet Django, structure des apps, Docker, PostgreSQL, settings, CI qualité (ruff/black/mypy), modèle `User` + rôles + authentification JWT + MFA.

**Lot 1 — Domaine métier**
Modèles `Affiliate`, `Employer`, `Contribution` + migrations + admin Django + serializers + viewsets CRUD avec permissions par rôle + tests.

**Lot 2 — Carte digitale**
Modèle `HealthCard`, génération automatique (signal + Celery), service de token JWS, génération QR, export PDF (WeasyPrint), endpoints cartes + tests sécurité du token.

**Lot 3 — Vérification**
Endpoint `/verify/`, `VerificationLog`, rate limiting, interface prestataire (scan), tests de bout en bout du parcours de vérification.

**Lot 4 — Interfaces**
Espaces citoyen, entreprise, agent (templates + HTMX + Tailwind), i18n portugais, responsive.

**Lot 5 — Audit, notifications, finitions**
`AuditEvent`, notifications de changement de statut, durcissement sécurité, seed de démo, documentation OpenAPI, README, couverture de tests.

**À chaque lot :** livrer le code, expliquer brièvement les choix, lister ce qui reste, et attendre la validation avant de poursuivre.

---

## 14. Critères d'acceptation (Definition of Done)

- [ ] Le projet démarre via `docker-compose up` sans erreur.
- [ ] Un assuré peut se connecter, voir sa carte, la télécharger en PDF et générer un QR.
- [ ] Un prestataire peut scanner/soumettre un token et obtenir un résultat de vérification correct en < 2 s.
- [ ] Un token expiré, révoqué ou non actif est rejeté.
- [ ] Aucune donnée personnelle n'est présente en clair dans le QR.
- [ ] Un agent peut suspendre/révoquer une carte, ce qui invalide immédiatement les vérifications.
- [ ] Toutes les actions sensibles sont journalisées.
- [ ] Les permissions par rôle sont respectées (un rôle ne peut pas accéder aux ressources d'un autre).
- [ ] Tests verts, couverture ≥ 80 % sur la logique métier.
- [ ] Documentation OpenAPI accessible et README complet.

---

*Fin du cahier des charges. Commence par le Lot 0 et demande validation avant de passer au Lot 1.*
