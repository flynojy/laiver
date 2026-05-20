[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$JobId,
  [string]$DatabaseUrl = "sqlite:///./apps/api/local.db",
  [string]$VenvPython = "E:\laiver-train\venv\Scripts\python.exe",
  [string]$HfHome = "E:\hf-cache"
)

. (Join-Path $PSScriptRoot "Common.ps1")

Invoke-AgentInProjectRoot {
  if (-not (Test-Path $VenvPython)) {
    throw "Training venv python not found at '$VenvPython'. Re-run the venv setup on E:\ first."
  }

  $hfHomePath = [System.IO.Path]::GetFullPath($HfHome)
  $env:HF_HOME = $hfHomePath
  if (-not $env:TRANSFORMERS_CACHE) { $env:TRANSFORMERS_CACHE = Join-Path $hfHomePath "hub" }
  if (-not $env:HF_HUB_CACHE)       { $env:HF_HUB_CACHE       = Join-Path $hfHomePath "hub" }
  if (-not $env:HF_DATASETS_CACHE)  { $env:HF_DATASETS_CACHE  = Join-Path $hfHomePath "datasets" }

  Write-Host "▶ launching fine-tune job"
  Write-Host "  job_id      : $JobId"
  Write-Host "  database    : $DatabaseUrl"
  Write-Host "  venv python : $VenvPython"
  Write-Host "  HF_HOME     : $env:HF_HOME"
  Write-Host ""
  Write-Host "  (worker runs in foreground; expect download + multi-step training)"
  Write-Host "  (output written to .tmp\fine-tuning\<job>\output\ which is junctioned to E:)"
  Write-Host ""

  & $VenvPython "scripts\local_finetune\run_job.py" `
    "--job-id" $JobId `
    "--database-url" $DatabaseUrl
}
