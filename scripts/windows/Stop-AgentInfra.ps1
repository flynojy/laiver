[CmdletBinding()]
param(
  [switch]$RemoveVolumes
)

. (Join-Path $PSScriptRoot "Common.ps1")

Assert-AgentCommand -Name "docker"

Invoke-AgentInProjectRoot {
  if ($RemoveVolumes) {
    & docker compose down -v
  } else {
    & docker compose stop postgres redis qdrant api web
  }
}
