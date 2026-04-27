Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-AgentProjectRoot {
  return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Get-AgentEnvPath {
  return Join-Path (Get-AgentProjectRoot) ".env"
}

function Ensure-AgentEnvFile {
  $projectRoot = Get-AgentProjectRoot
  $envPath = Join-Path $projectRoot ".env"
  if (Test-Path $envPath) {
    return $envPath
  }

  $examplePath = Join-Path $projectRoot ".env.example"
  if (-not (Test-Path $examplePath)) {
    throw "Missing .env.example at $examplePath"
  }

  Copy-Item $examplePath $envPath
  return $envPath
}

function Import-AgentDotEnv {
  param(
    [string]$Path = (Get-AgentEnvPath),
    [switch]$Overwrite
  )

  if (-not (Test-Path $Path)) {
    return
  }

  foreach ($line in Get-Content $Path) {
    if ([string]::IsNullOrWhiteSpace($line)) {
      continue
    }
    if ($line.TrimStart().StartsWith("#")) {
      continue
    }

    $parts = $line -split "=", 2
    if ($parts.Count -ne 2) {
      continue
    }

    $name = $parts[0].Trim()
    $value = $parts[1].Trim()
    $existing = [Environment]::GetEnvironmentVariable($name, "Process")
    if ($Overwrite -or [string]::IsNullOrWhiteSpace($existing)) {
      [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
  }
}

function Test-AgentCommand {
  param([Parameter(Mandatory = $true)][string]$Name)
  return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Assert-AgentCommand {
  param([Parameter(Mandatory = $true)][string]$Name)
  if (-not (Test-AgentCommand -Name $Name)) {
    throw "Required command '$Name' was not found on PATH."
  }
}

function Invoke-AgentInProjectRoot {
  param(
    [Parameter(Mandatory = $true)][scriptblock]$ScriptBlock
  )

  $projectRoot = Get-AgentProjectRoot
  Push-Location $projectRoot
  try {
    & $ScriptBlock
  }
  finally {
    Pop-Location
  }
}

function Invoke-AgentInApiRoot {
  param(
    [Parameter(Mandatory = $true)][scriptblock]$ScriptBlock
  )

  $apiRoot = Join-Path (Get-AgentProjectRoot) "apps\api"
  Push-Location $apiRoot
  try {
    & $ScriptBlock
  }
  finally {
    Pop-Location
  }
}

