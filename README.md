# Liberação Escolar

Sistema web de liberação escolar para uma única instituição. Desenvolvido com TDD.
Status: **E1 — ambiente de desenvolvimento e testes** (sem regras de negócio ainda).

## Requisitos

- Docker e Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python 3.12+)
- Node.js 22+ e npm

## Configuração inicial

```bash
cp .env.example .env                 # credenciais do PostgreSQL local (fictícias)
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

Edite as senhas em `.env` e use a mesma senha nas URLs de `backend/.env`.

## Banco de dados (PostgreSQL via Docker)

```bash
docker compose up -d db
docker compose ps        # aguarde o status "healthy"
```

Na primeira inicialização do volume são criados dois bancos isolados:
`liberacao_dev` (desenvolvimento) e `liberacao_test` (testes).
Para recriar do zero: `docker compose down -v && docker compose up -d db`.

## Backend (FastAPI)

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload     # http://localhost:8000/health
```

### Testes do backend

```bash
cd backend
uv run pytest -m "not integration"   # unitários e API, sem banco
uv run pytest                        # suíte completa (exige PostgreSQL de teste)
uv run ruff check .                  # lint
```

Os testes usam `TEST_DATABASE_URL`, que deve apontar para um banco cujo nome termina em `_test`.
Nunca aponte para o banco de desenvolvimento.

## Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

### Testes do frontend

```bash
cd frontend
npm test             # Vitest + Testing Library
npm run lint
npm run typecheck
npm run build
```

## Convenções

- TDD: Red, Green, Refactor. O teste vem antes do código de produção.
- Somente dados fictícios em desenvolvimento e testes.
- O fuso da escola (`SCHOOL_TIMEZONE`) é explícito e nunca herdado da máquina.
- Segredos ficam em `.env` (ignorado pelo Git); apenas `.env.example` é versionado.

## Integração contínua

`.github/workflows/ci.yml` executa lint e testes do backend (com PostgreSQL de serviço)
e lint, typecheck, testes e build do frontend.


## Regras de domínio

Código puro em `backend/app/domain/`, sem banco nem framework:

| Módulo | Responsabilidade |
|---|---|
| `relogio.py` | `Relogio` injetável, data oficial da escola no fuso configurado, validação da data-alvo |
| `turno.py` | Limites por turno (13:00 e 19:00, **exclusivos**) |
| `vinculo.py` | Vínculo responsável-aluno vigente ou revogado |
| `estados.py` | Máquina de estados (`LIBERADO`, `CANCELADO`, sem registro) e tipos de ação |
| `avaliacao.py` | Orquestra data, vínculo, limite e transição para uma operação |

```bash
cd backend
uv run pytest tests/unit/domain -q   # só as regras de domínio, sem banco
```


## Banco de dados e migrações (E3)

Modelos SQLAlchemy 2.x em `backend/app/models/` e migrações Alembic em `backend/migrations/`.

```bash
cd backend
uv run alembic upgrade head      # aplica as migrações no banco de DATABASE_URL
uv run alembic check             # confirma que modelos e migrações não divergem
uv run alembic downgrade base    # desfaz tudo (apenas desenvolvimento)
```

Garantias aplicadas pelo próprio PostgreSQL:

- um único registro de liberação por aluno e data (`UNIQUE (aluno_id, data)`);
- um único vínculo ativo por responsável e aluno, e uma única matrícula aberta por aluno e ano letivo;
- turma e ano letivo coerentes na matrícula (FK composta);
- `historico_liberacoes` e `auditoria` são **append-only**: trigger bloqueia UPDATE, DELETE e TRUNCATE.

### Testes de integração

```bash
cd backend
uv run pytest tests/integration -q
```

Cada teste recria o schema do banco de teste e aplica as migrações. Por segurança, a suíte
**recusa rodar** se o nome do banco não terminar em `_test`.


## Autenticação (E4a)

Sessão no servidor, com cookie `sessao` (`HttpOnly`, `SameSite=Lax`, `Secure` por padrão).
Somente o **hash** do token fica no banco.

| Rota | Descrição |
|---|---|
| `POST /auth/login` | `{"email", "senha"}`. Define o cookie e devolve o usuário e o `csrf_token` |
| `GET /auth/me` | Usuário da sessão atual e o `csrf_token` |
| `POST /auth/logout` | Revoga a sessão. Exige o cabeçalho `X-CSRF-Token` |

- Toda requisição autenticada que **altera estado** (qualquer método diferente de GET, HEAD e OPTIONS) exige `X-CSRF-Token`.
- Sessão: 8 horas no total e 30 minutos de inatividade (configuráveis).
- Login: 5 falhas por e-mail em 15 minutos, ou 20 por IP, bloqueiam novas tentativas (HTTP 429 com `Retry-After`).
- Tentativas rejeitadas e eventos de login ficam na tabela `auditoria` (sem senha, token ou e-mail em claro).

### Configuração obrigatória

`backend/.env` precisa de `SECRET_KEY` com 32 caracteres ou mais (veja `backend/.env.example`).
Sem ela, a API **e o Alembic** se recusam a iniciar.

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Em desenvolvimento local sem HTTPS, use `COOKIE_SECURE=false`.