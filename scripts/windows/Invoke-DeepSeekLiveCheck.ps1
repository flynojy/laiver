[CmdletBinding()]
param(
  [string]$ApiKey = ""
)

. (Join-Path $PSScriptRoot "Common.ps1")

Assert-AgentCommand -Name "python"
Ensure-AgentEnvFile | Out-Null
Import-AgentDotEnv -Overwrite

if (-not [string]::IsNullOrWhiteSpace($ApiKey)) {
  [Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY", $ApiKey, "Process")
}

$effectiveApiKey = [Environment]::GetEnvironmentVariable("DEEPSEEK_API_KEY", "Process")
if ([string]::IsNullOrWhiteSpace($effectiveApiKey)) {
  throw "DEEPSEEK_API_KEY is not configured. Pass -ApiKey or set it in .env."
}

Invoke-AgentInProjectRoot {
  & python .\scripts\windows\Run-DeepSeekLiveCheck.py
}
