[CmdletBinding()]
param([int]$Port=8830)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
try {
  $state=Invoke-RestMethod "http://127.0.0.1:$Port/api/state" -TimeoutSec 2
  if ($state.catalog -and $state.profiles) { Write-Output "NNB editor already running: http://127.0.0.1:$Port"; exit 0 }
} catch {}
New-Item -ItemType Directory -Path "$root/logs" -Force | Out-Null
$python=(Get-Command python).Source
Start-Process -FilePath $python -ArgumentList @('tools/editor_server.py','--port',"$Port") -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput "$root/logs/editor-server.out.log" -RedirectStandardError "$root/logs/editor-server.err.log" | Out-Null
Write-Output "NNB editor: http://127.0.0.1:$Port"
