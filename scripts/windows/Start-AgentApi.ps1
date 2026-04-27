[CmdletBinding()]
param(
  [int]$Port = 8000,
  [switch]$UseSqlite
)

. (Join-Path $PSScriptRoot "Common.ps1")

Assert-AgentCommand -Name "python"
Ensure-AgentEnvFile | Out-Null
Import-AgentDotEnv -Overwrite

if ($UseSqlite) {
  [Environment]::SetEnvironmentVariable("DATABASE_URL", "sqlite:///./apps/api/local.db", "Process")
  [Environment]::SetEnvironmentVariable("AUTO_INIT_DB", "true", "Process")
} else {
  $databaseUrl = [Environment]::GetEnvironmentVariable("DATABASE_URL", "Process")
  if (-not [string]::IsNullOrWhiteSpace($databaseUrl) -and -not $databaseUrl.StartsWith("sqlite")) {
    [Environment]::SetEnvironmentVariable("AUTO_INIT_DB", "false", "Process")
  }
}

Invoke-AgentInProjectRoot {
  & python -m uvicorn app.main:app --reload --host 0.0.0.0 --port $Port --app-dir apps/api
}
