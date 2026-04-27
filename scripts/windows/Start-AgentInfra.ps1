[CmdletBinding()]
param(
  [switch]$Build,
  [switch]$IncludeAppContainers
)

. (Join-Path $PSScriptRoot "Common.ps1")

Assert-AgentCommand -Name "docker"
Ensure-AgentEnvFile | Out-Null
Import-AgentDotEnv

$services = if ($IncludeAppContainers) {
  @("postgres", "redis", "qdrant", "api", "web")
} else {
  @("postgres", "redis", "qdrant")
}

Invoke-AgentInProjectRoot {
  if ($Build) {
    & docker compose up --build -d @services
  } else {
    & docker compose up -d @services
  }
}
