# Windows Setup

This project now has a Windows-first operating path. You do not need WSL.

## Recommended Stack

- Windows 11 or Windows 10
- PowerShell
- Node.js 20+
- Python 3.11+
- Docker Desktop for Windows
- Optional for Feishu callbacks: `ngrok` or `cloudflared`

## One-Time Setup

1. Copy the environment file.

```powershell
Copy-Item .env.example .env
```

2. Install JavaScript dependencies.

```powershell
npm.cmd install
```

3. Install the API package into your active Python environment.

```powershell
python -m pip install -e apps/api
```

4. Run the Windows environment doctor.

```powershell
npm.cmd run windows:doctor
```

## Preferred Windows Runtime Layout

- `apps/web`: run natively on Windows
- `apps/api`: run natively on Windows
- `PostgreSQL`, `Redis`, `Qdrant`: run with Docker Desktop

This keeps the application layer fully native while still using the intended infrastructure services.

## Start Infrastructure

1. Make sure Docker Desktop is installed and running.
2. Start PostgreSQL, Redis, and Qdrant.

```powershell
npm.cmd run windows:infra:up
```

This starts:

- `postgres`
- `redis`
- `qdrant`

If you want the Compose-defined API and web containers too, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\Start-AgentInfra.ps1 -IncludeAppContainers
```

## Configure PostgreSQL on Windows

Edit `.env` and set:

```env
DATABASE_URL=postgresql+psycopg://agent:agent@localhost:5432/agent_platform
AUTO_INIT_DB=false
```

The default local SQLite mode is still available, but for full-stack Windows operation you should switch to PostgreSQL.

## Run Migrations

After PostgreSQL is up and `.env` points at it:

```powershell
npm.cmd run windows:db:migrate
```

This runs:

```powershell
python -m alembic upgrade head
```

against `apps/api`.

## Start the API

For PostgreSQL-backed Windows development:

```powershell
npm.cmd run windows:dev:api
```

For a quick SQLite fallback:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\Start-AgentApi.ps1 -UseSqlite
```

## Start the Web App

```powershell
npm.cmd run windows:dev:web
```

## DeepSeek Live Check on Windows

Set your key in `.env`:

```env
DEEPSEEK_API_KEY=your_key_here
```

Then run:

```powershell
npm.cmd run windows:deepseek:check
```

You can also pass the key without writing it to disk:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\Invoke-DeepSeekLiveCheck.ps1 -ApiKey "your_key_here"
```

The check validates:

- completion
- streaming
- tool calling

## Feishu Callback on Windows

The API webhook route is:

```text
/api/v1/connectors/feishu/webhook/{connector_id}
```

To expose your Windows API to Feishu, start a tunnel:

```powershell
npm.cmd run windows:tunnel
```

If you want a specific provider:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\Start-AgentTunnel.ps1 -Provider ngrok
```

or

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\Start-AgentTunnel.ps1 -Provider cloudflared
```

To generate the callback URL and a connector config draft:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\Get-FeishuWebhookConfig.ps1 `
  -ConnectorId "<connector_id>" `
  -PublicBaseUrl "https://your-public-url"
```

For live Feishu usage, configure the connector with:

- `mode=live`
- `delivery_mode=webhook` and `reply_webhook_url`, or
- `delivery_mode=openapi` with `app_id`, `app_secret`, and `receive_id_type`
- `verification_token` matching the Feishu event subscription token

## Common Windows Commands

```powershell
npm.cmd run windows:doctor
npm.cmd run windows:infra:up
npm.cmd run windows:db:migrate
npm.cmd run windows:dev:api
npm.cmd run windows:dev:web
npm.cmd run windows:deepseek:check
npm.cmd run windows:infra:down
```

## Troubleshooting

### Docker is missing

Install Docker Desktop for Windows, then rerun:

```powershell
npm.cmd run windows:doctor
```

### `windows:db:migrate` fails

Check:

- PostgreSQL container is running
- `.env` uses the PostgreSQL `DATABASE_URL`
- `AUTO_INIT_DB=false`

### Feishu callbacks do not arrive

Check:

- your tunnel is online
- Feishu points to the exact callback URL
- `verification_token` matches on both sides
- local API is running on port `8000`
