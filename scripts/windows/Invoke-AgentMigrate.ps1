[CmdletBinding()]
param(
  [string]$DatabaseUrl = ""
)

. (Join-Path $PSScriptRoot "Common.ps1")

Assert-AgentCommand -Name "python"
Ensure-AgentEnvFile | Out-Null
Import-AgentDotEnv -Overwrite

if (-not [string]::IsNullOrWhiteSpace($DatabaseUrl)) {
  [Environment]::SetEnvironmentVariable("DATABASE_URL", $DatabaseUrl, "Process")
}

$effectiveDatabaseUrl = [Environment]::GetEnvironmentVariable("DATABASE_URL", "Process")
if ([string]::IsNullOrWhiteSpace($effectiveDatabaseUrl)) {
  throw "DATABASE_URL is not configured."
}

[Environment]::SetEnvironmentVariable("AUTO_INIT_DB", "false", "Process")

Invoke-AgentInApiRoot {
  & python -m alembic upgrade head
}
