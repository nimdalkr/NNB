[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$msbuild='C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\MSBuild.exe'
if(-not(Test-Path -LiteralPath $msbuild)){throw 'Visual Studio 2022 C++ Build Tools are required'}
New-Item -ItemType Directory -Path "$root\logs","$root\artifacts\upstream" -Force | Out-Null
Push-Location $root
try {
  & $msbuild Locutus.sln /t:Build /p:Configuration=Release /p:Platform=Win32 /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0.26100.0 /m:2 /v:minimal /nologo *> logs/upstream-build.log
  if($LASTEXITCODE -ne 0){throw 'Baseline build failed; see logs/upstream-build.log'}
  $stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
  $stage=Join-Path $root "artifacts\baseline-$stamp"
  New-Item -ItemType Directory -Path $stage | Out-Null
  Copy-Item -LiteralPath "$root\Release\Locutus.dll" -Destination "$stage\NNB.dll"
  Copy-Item -LiteralPath "$root\Locutus.json" -Destination "$stage\Locutus.json"
  $commit=(& git rev-parse HEAD).Trim()
  $strategyChanges=@(& git diff 4e96da0b7e31831ee97aaef153b2bef977a235e1 --name-only -- Steamhammer BOSS BWTA BWEM BWEB BWAPILIB Locutus.json)
  @{upstream='https://github.com/bmnielsen/Locutus';upstreamCommit='4e96da0b7e31831ee97aaef153b2bef977a235e1';forkCommit=$commit;architecture='x86';toolset='v143';windowsSdk='10.0.26100.0';strategyCodeChanged=($strategyChanges.Count -gt 0);sha256=(Get-FileHash "$stage\NNB.dll").Hash.ToLowerInvariant();nativeGameTested=$false;mapCacheRequired=$true} | ConvertTo-Json | Set-Content "$stage\provenance.json" -Encoding utf8
  Write-Output $stage
} finally {Pop-Location}
