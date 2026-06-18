# e-INSS — Plataforma Nacional de Seguridade Social

Plataforma de gestão da seguridade social da Guiné-Bissau, desenvolvida pelo INSS.

---

## Stack técnica

| Componente      | Tecnologia                          |
|-----------------|-------------------------------------|
| Backend         | Python 3.12 / Django 5.x            |
| API             | Django REST Framework 3.15+         |
| Base de dados   | PostgreSQL 16                       |
| Cache / Fila    | Redis 7 + Celery 5                  |
| Autenticação    | JWT (SimpleJWT) + TOTP MFA          |
| Docs API        | drf-spectacular (Swagger / ReDoc)   |
| Frontend        | Django Templates + Tailwind + HTMX  |
| Containerização | Docker + Docker Compose             |

---

## Instalação rápida (Docker)

```bash
# 1. Clonar o repositório
git clone <repo_url> plateform_e_inss
cd plateform_e_inss

# 2. Copiar e configurar variáveis de ambiente
cp .env.example .env
# Editar .env com as suas credenciais

# 3. Construir e iniciar os contentores
docker compose up -d --build

# 4. Aplicar migrações
docker compose exec web python manage.py migrate

# 5. Criar dados de demonstração
docker compose exec web python manage.py seed_demo

# 6. Aceder ao portal
# Portal:  http://localhost:8000/auth/login/
# API:     http://localhost:8000/api/v1/docs/
# Admin:   http://localhost:8000/admin/
```

---

## Variáveis de ambiente (.env)

```env
SECRET_KEY=django-insecure-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

POSTGRES_DB=einss
POSTGRES_USER=einss
POSTGRES_PASSWORD=changeme
POSTGRES_HOST=db
POSTGRES_PORT=5432

REDIS_URL=redis://redis:6379/0

STATIC_ROOT=/app/staticfiles
MEDIA_ROOT=/app/media

INSS_PRIVATE_KEY_PATH=/app/keys/inss_private.pem
INSS_PUBLIC_KEY_PATH=/app/keys/inss_public.pem
```

---

## Comandos úteis

```bash
# Migrações
python manage.py makemigrations
python manage.py migrate

# Dados de demonstração (idempotente)
python manage.py seed_demo

# Testes
pytest tests/ -v

# Testes com cobertura
pytest tests/ --cov=apps --cov-report=html

# Worker Celery
celery -A config.celery worker --loglevel=info

# Scheduler Celery Beat
celery -A config.celery beat --loglevel=info

# Gerar esquema OpenAPI
python manage.py spectacular --file schema.yaml

# Qualidade de código
ruff check .
black --check .
mypy .
```

---

## Arquitetura dos lots

| Lot | Apps                        | Funcionalidades                                        |
|-----|-----------------------------|--------------------------------------------------------|
| 0   | config, base                | Setup Django, PostgreSQL, Redis, Celery                |
| 1   | accounts                    | Utilizadores, JWT, MFA TOTP, portais HTML              |
| 2   | affiliates                  | Afiliados, dependentes, NISS                           |
| 3   | employers, contributions    | Empregadores, cotizações, cálculo automático           |
| 4   | cards, verification         | Cartão de saúde, QR JWS, verificação, PDF              |
| 5   | audit, notifications        | Auditoria, notificações, seed_demo, OpenAPI            |

---

## Endpoints API principais

| Método | Endpoint                            | Descrição                         | Role        |
|--------|-------------------------------------|-----------------------------------|-------------|
| POST   | /api/v1/auth/login/                 | Autenticação JWT                  | Todos       |
| POST   | /api/v1/auth/mfa/verify/            | Verificação MFA                   | Todos       |
| GET    | /api/v1/affiliates/                 | Listar afiliados                  | AGENT/ADMIN |
| POST   | /api/v1/affiliates/                 | Criar afiliado                    | AGENT/ADMIN |
| GET    | /api/v1/employers/                  | Listar empregadores               | AGENT/ADMIN |
| GET    | /api/v1/contributions/              | Listar cotizações                 | EMPLOYER+   |
| GET    | /api/v1/cards/                      | Listar cartões                    | AGENT/ADMIN |
| POST   | /api/v1/verify/card/                | Verificar cartão por QR           | PROVIDER+   |
| GET    | /api/v1/audit/                      | Listar eventos de auditoria       | ADMIN       |
| GET    | /api/v1/notifications/              | Minhas notificações               | Autenticado |
| PATCH  | /api/v1/notifications/{id}/         | Marcar notificação como lida      | Autenticado |
| GET    | /api/v1/notifications/unread_count/ | Número de não lidas               | Autenticado |
| GET    | /api/v1/docs/                       | Swagger UI                        | Público     |
| GET    | /api/v1/redoc/                      | ReDoc                             | Público     |

---

## Credenciais demo (após seed_demo)

| Email                    | Password      | Role     |
|--------------------------|---------------|----------|
| admin@inss.gw            | admin123!     | ADMIN    |
| agent@inss.gw            | agent123!     | AGENT    |
| joao.silva@email.com     | citizen123!   | CITIZEN  |
| maria.costa@email.com    | citizen123!   | CITIZEN  |
| empresa.abc@email.com    | employer123!  | EMPLOYER |
| clinica.saude@email.com  | provider123!  | PROVIDER |

---

## Segurança (JWT, MFA, JWS QR)

### Autenticação JWT

- Tokens de acesso válidos por **15 minutos**
- Tokens de atualização válidos por **7 dias** (rotação automática)
- Fluxo com MFA: `login → pre_auth_token → /auth/mfa/verify/ → access_token`

### MFA TOTP

- Baseado em RFC 6238 (TOTP) via `pyotp`
- Compatível com Google Authenticator, Authy, etc.
- Configurável por utilizador

### QR Code JWS (Cartão de Saúde)

- Tokens assinados com RSA 2048 bits (JWS RS256)
- Válidos por **5 minutos**, rotação automática via Celery
- Verificação offline possível com a chave pública INSS
- Payload inclui: `niss`, `card_number`, `status`, `exp`, `jti`

### Auditoria

- Todos os eventos críticos registados em `AuditEvent`
- Captura: utilizador, IP, role, recurso, valores antes/depois
- Imutável via admin (sem add/change/delete permissions)
- Signals Django automáticos para Affiliate, HealthCard, Contribution

---

## Licença

Propriedade do Instituto Nacional de Segurança Social — Guiné-Bissau.
Uso reservado. Contacto: tech@inss.gw
