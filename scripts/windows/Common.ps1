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

function Add-AgentPortableNodeToPath {
  $projectRoot = Get-AgentProjectRoot
  $toolsRoot = Join-Path $projectRoot ".tmp\tools"
  if (-not (Test-Path $toolsRoot)) {
    return $null
  }

  $nodeTool = Get-ChildItem $toolsRoot -Directory -Filter "node-v22.*-win-x64" -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending |
    Select-Object -First 1
  if ($null -eq $nodeTool) {
    return $null
  }

  $env:PATH = "$($nodeTool.FullName);$env:PATH"
  return $nodeTool.FullName
}

function Resolve-AgentPython {
  $projectRoot = Get-AgentProjectRoot
  $venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
  if (Test-Path $venvPython) {
    return $venvPython
  }

  $python = Get-Command "python" -ErrorAction SilentlyContinue
  if ($null -eq $python) {
    throw "Python was not found. Create a venv first: python -m venv .venv"
  }
  return $python.Source
}

function Resolve-AgentNpm {
  Add-AgentPortableNodeToPath | Out-Null

  $node = Get-Command "node" -ErrorAction SilentlyContinue
  if ($null -eq $node) {
    throw "Node.js was not found. Install Node.js 22 or place a Node 22 portable build under .tmp\tools."
  }

  $nodeVersion = (& $node.Source -p "process.versions.node").Trim()
  $nodeMajor = [int]($nodeVersion.Split(".")[0])
  if ($nodeMajor -ne 22) {
    throw "Node.js $nodeVersion is active, but Laiver requires Node.js 22.x. Put Node 22 first on PATH or use the portable Node under .tmp\tools."
  }

  $npm = Get-Command "npm.cmd" -ErrorAction SilentlyContinue
  if ($null -eq $npm) {
    throw "npm.cmd was not found after resolving Node.js."
  }
  return $npm.Source
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

function Test-AgentHttpOk {
  param(
    [Parameter(Mandatory = $true)][string]$Url
  )

  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
    return [int]$response.StatusCode -ge 200 -and [int]$response.StatusCode -lt 500
  }
  catch {
    return $false
  }
}

function Wait-AgentHttpOk {
  param(
    [Parameter(Mandatory = $true)][string]$Url,
    [int]$TimeoutSeconds = 40
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    if (Test-AgentHttpOk -Url $Url) {
      return $true
    }
    Start-Sleep -Seconds 1
  }
  return $false
}

function Get-AgentPortListeners {
  param([Parameter(Mandatory = $true)][int]$Port)

  return @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Test-AgentPortListening {
  param([Parameter(Mandatory = $true)][int]$Port)

  return @(Get-AgentPortListeners -Port $Port).Count -gt 0
}

function Get-AgentProcessCommandLine {
  param([Parameter(Mandatory = $true)][int]$ProcessId)

  try {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
    return [string]$process.CommandLine
  }
  catch {
    return ""
  }
}

function Test-AgentProcessLooksLocal {
  param([Parameter(Mandatory = $true)][int]$ProcessId)

  $projectRoot = Get-AgentProjectRoot
  $commandLine = Get-AgentProcessCommandLine -ProcessId $ProcessId
  if ([string]::IsNullOrWhiteSpace($commandLine)) {
    return $false
  }

  return $commandLine.Contains($projectRoot) -or
    $commandLine.Contains("uvicorn app.main:app") -or
    $commandLine.Contains("next dev") -or
    $commandLine.Contains("dev:web")
}

