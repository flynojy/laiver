[CmdletBinding()]
param(
  [string]$Model = "qwen3:14b",
  [string]$BaseUrl = "http://127.0.0.1:11434",
  [int]$NumCtx = 1024,
  [int]$NumPredict = 32,
  [switch]$SkipGenerate
)

. (Join-Path $PSScriptRoot "Common.ps1")

function Write-CheckLine {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Status,
    [Parameter(Mandatory = $true)][string]$Detail
  )
  [PSCustomObject]@{
    Name = $Name
    Status = $Status
    Detail = $Detail
  }
}

function Get-OllamaErrorDetail {
  param([object]$ErrorRecord)

  if ($null -eq $ErrorRecord -or $null -eq $ErrorRecord.Exception) {
    return "Unknown Ollama check error."
  }

  $detail = [string]$ErrorRecord.Exception.Message
  if ($ErrorRecord.ErrorDetails -and -not [string]::IsNullOrWhiteSpace($ErrorRecord.ErrorDetails.Message)) {
    $detail = [string]$ErrorRecord.ErrorDetails.Message
  }
  $response = $ErrorRecord.Exception.Response
  if ($null -eq $response) {
    return $detail
  }

  try {
    $stream = $response.GetResponseStream()
    if ($null -eq $stream) {
      return $detail
    }
    $reader = [System.IO.StreamReader]::new($stream)
    $body = $reader.ReadToEnd()
    if (-not [string]::IsNullOrWhiteSpace($body)) {
      return $body
    }
  }
  catch {
    return $detail
  }

  return $detail
}

$checks = New-Object System.Collections.Generic.List[object]

if (-not (Test-AgentCommand -Name "ollama")) {
  $checks.Add((Write-CheckLine -Name "Ollama CLI" -Status "FAIL" -Detail "ollama was not found on PATH."))
  $checks | Format-Table -AutoSize
  exit 1
}

try {
  $versionOutput = & ollama --version 2>&1
  $version = ([string]::Join(" ", @($versionOutput))).Trim()
  if ([string]::IsNullOrWhiteSpace($version)) {
    $version = "ollama command returned no version output."
  }
  $checks.Add((Write-CheckLine -Name "Ollama CLI" -Status "OK" -Detail $version))
}
catch {
  $checks.Add((Write-CheckLine -Name "Ollama CLI" -Status "FAIL" -Detail (Get-OllamaErrorDetail $_)))
}

try {
  $tags = Invoke-RestMethod -Uri "$BaseUrl/api/tags" -Method Get -TimeoutSec 10
  $models = @($tags.models)
  $match = $models | Where-Object { $_.model -eq $Model -or $_.name -eq $Model } | Select-Object -First 1
  if ($match) {
    $detail = "$($match.model) / $($match.details.parameter_size) / $($match.details.quantization_level)"
    $checks.Add((Write-CheckLine -Name "Ollama API" -Status "OK" -Detail "$BaseUrl is responding."))
    $checks.Add((Write-CheckLine -Name "Model" -Status "OK" -Detail $detail))
  }
  else {
    $available = ($models | ForEach-Object { $_.model }) -join ", "
    $checks.Add((Write-CheckLine -Name "Model" -Status "FAIL" -Detail "Missing $Model. Available: $available"))
  }
}
catch {
  $checks.Add((Write-CheckLine -Name "Ollama API" -Status "FAIL" -Detail (Get-OllamaErrorDetail $_)))
}

if (Test-AgentCommand -Name "nvidia-smi") {
  try {
    $gpu = (& nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv,noheader,nounits).Trim()
    $checks.Add((Write-CheckLine -Name "GPU" -Status "OK" -Detail $gpu))
  }
  catch {
    $checks.Add((Write-CheckLine -Name "GPU" -Status "WARN" -Detail "nvidia-smi exists but did not return GPU status."))
  }
}
else {
  $checks.Add((Write-CheckLine -Name "GPU" -Status "WARN" -Detail "nvidia-smi was not found."))
}

if (-not $SkipGenerate) {
  try {
    $payload = @{
      model = $Model
      messages = @(@{ role = "user"; content = "Please reply with exactly: ollama-ok /no_think" })
      stream = $false
      think = $false
      options = @{
        num_ctx = $NumCtx
        num_predict = $NumPredict
        temperature = 0.1
      }
    } | ConvertTo-Json -Depth 8

    $started = Get-Date
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/chat" -Method Post -ContentType "application/json" -Body $payload -TimeoutSec 180
    $elapsed = [math]::Round(((Get-Date) - $started).TotalSeconds, 2)
    $content = [string]$response.message.content
    $checks.Add((Write-CheckLine -Name "Generate" -Status "OK" -Detail "$elapsed sec; $content"))
  }
  catch {
    $detail = Get-OllamaErrorDetail $_
    $checks.Add((Write-CheckLine -Name "Generate" -Status "FAIL" -Detail $detail))
  }
}

$checks | Format-Table -AutoSize

$failed = @($checks | Where-Object { $_.Status -eq "FAIL" })
if ($failed.Count -gt 0) {
  exit 1
}

Write-Host "Ollama local model check passed."
