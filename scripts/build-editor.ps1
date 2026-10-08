[CmdletBinding()]
param()
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$msbuild='C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/MSBuild/Current/Bin/MSBuild.exe'
Push-Location $root
try {
  New-Item -ItemType Directory -Path logs -Force | Out-Null
  & $msbuild Locutus.sln /t:Build /p:Configuration=Release /p:Platform=Win32 /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0.26100.0 /m:3 /v:minimal /nologo *> logs/editor-build.log
  if ($LASTEXITCODE -ne 0) { throw 'Editor DLL build failed; see logs/editor-build.log' }
  & cmake -S tools/native-check -B build/native-check -A Win32 *> logs/native-check-configure.log
  if ($LASTEXITCODE -ne 0) { throw 'Native checker configure failed' }
  & cmake --build build/native-check --config Release *> logs/native-check-build.log
  if ($LASTEXITCODE -ne 0) { throw 'Native checker build failed' }
  & build/native-check/Release/nnb-native-smoke.exe Release/Locutus.dll
  if ($LASTEXITCODE -ne 0) { throw 'Editor DLL smoke failed' }
  & python -m unittest discover -s tools -p test_*.py
  if ($LASTEXITCODE -ne 0) { throw 'Editor regression checks failed' }
  & python tools/build_provenance.py
  if ($LASTEXITCODE -ne 0) { throw 'Could not record build provenance' }
  Write-Output 'NNB editor DLL and rule preview are ready. No game was started.'
} finally { Pop-Location }
