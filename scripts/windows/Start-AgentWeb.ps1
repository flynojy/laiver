[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot "Common.ps1")

Assert-AgentCommand -Name "npm.cmd"
Ensure-AgentEnvFile | Out-Null
Import-AgentDotEnv -Overwrite

Invoke-AgentInProjectRoot {
  & npm.cmd run dev:web
}
