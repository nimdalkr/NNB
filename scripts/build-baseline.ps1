[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$msbuild='C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\MSBuild.exe'
if(-not(Test-Path -LiteralPath $msbuild)){throw 'Visual Studio 2022 C++ Build Tools are required'}
New-Item -ItemType Directory -Path "$root\logs","$root\artifacts\upstream" -Force | Out-Null
Push-Location $root
try {
  $upstream='4e96da0b7e31831ee97aaef153b2bef977a235e1'
  $stamp=(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[guid]::NewGuid().ToString('N').Substring(0,6)
  $snapshot=Join-Path $root "build\baseline-source-$stamp"
  New-Item -ItemType Directory -Path $snapshot | Out-Null
  $archive=Join-Path $snapshot 'upstream.tar'
  & git archive --format=tar --output=$archive $upstream
  if($LASTEXITCODE -ne 0){throw 'Could not extract pinned upstream source'}
  & tar -xf $archive -C $snapshot
  if($LASTEXITCODE -ne 0){throw 'Could not unpack pinned upstream source'}
  Push-Location $snapshot
  try {
    & $msbuild Locutus.sln /t:Build /p:Configuration=Release /p:Platform=Win32 /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0.26100.0 /m:2 /v:minimal /nologo *> "$root\logs\upstream-build-$stamp.log"
    if($LASTEXITCODE -ne 0){throw "Baseline build failed; see logs/upstream-build-$stamp.log"}
  } finally { Pop-Location }
  $stage=Join-Path $root "artifacts\baseline-$stamp"
  New-Item -ItemType Directory -Path $stage | Out-Null
  Copy-Item -LiteralPath "$snapshot\Release\Locutus.dll" -Destination "$stage\NNB.dll"
  Copy-Item -LiteralPath "$snapshot\Locutus.json" -Destination "$stage\Locutus.json"
  $commit=(& git rev-parse HEAD).Trim()
  @{upstream='https://github.com/bmnielsen/Locutus';upstreamCommit=$upstream;forkCommit=$commit;architecture='x86';toolset='v143';windowsSdk='10.0.26100.0';strategyCodeChanged=$false;sha256=(Get-FileHash "$stage\NNB.dll").Hash.ToLowerInvariant();nativeGameTested=$false;mapCacheRequired=$true} | ConvertTo-Json | Set-Content "$stage\provenance.json" -Encoding utf8
  if (-not (Test-Path -LiteralPath "$root\artifacts\upstream\NNB.dll")) {
    Copy-Item -LiteralPath "$stage\NNB.dll" -Destination "$root\artifacts\upstream\NNB.dll"
    Copy-Item -LiteralPath "$stage\provenance.json" -Destination "$root\artifacts\upstream\provenance.json"
  }
  Write-Output $stage
} finally {Pop-Location}
