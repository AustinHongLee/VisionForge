@echo off
setlocal EnableExtensions EnableDelayedExpansion

chcp 65001 >nul
title VisionForge dev launcher

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
pushd "%ROOT%" || (
  echo [ERROR] Could not enter repo root: %ROOT%
  pause
  exit /b 1
)

set "CHECK_ONLY="
if /i "%~1"=="--check" set "CHECK_ONLY=1"

echo ==================================================
echo   VisionForge one-click dev launcher
echo   Root: %CD%
echo ==================================================
echo.

echo [1/8] Checking required project files...
if not exist "pyproject.toml" (
  echo     [ERROR] pyproject.toml not found. Run this from the repo root.
  goto fail
)
if not exist "ui\package.json" (
  echo     [ERROR] ui\package.json not found.
  goto fail
)
echo     OK

echo [2/8] Stopping stale VisionForge dev processes...
if defined CHECK_ONLY (
  echo     skipped in --check mode
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$root = (Resolve-Path '.').Path; Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and (($_.CommandLine -match 'visionforge_app\.api') -or (($_.Name -match '^(electron|node)(\.exe)?$') -and ($_.CommandLine -like ('*' + $root + '*')))) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('     stopped PID ' + $_.ProcessId + ' (' + $_.Name + ')') }"
  if errorlevel 1 (
    echo     [WARN] stale-process cleanup had a non-fatal error.
  ) else (
    echo     cleanup done
  )
)

echo [3/8] Syncing Python workspace...
where uv >nul 2>&1
if errorlevel 1 (
  if not exist ".venv\Scripts\python.exe" (
    echo     [ERROR] uv is not on PATH and .venv is missing.
    echo     Install uv, or run uv sync once before using this launcher.
    goto fail
  )
  echo     uv not found; using existing .venv
) else (
  uv sync
  if errorlevel 1 (
    echo     [ERROR] uv sync failed.
    goto fail
  )
)
if not exist ".venv\Scripts\python.exe" (
  echo     [ERROR] .venv\Scripts\python.exe was not created.
  goto fail
)

echo [4/8] Verifying Python imports...
".venv\Scripts\python.exe" -c "import visionforge_app.api, visionforge_providers, openai" >nul 2>&1
if errorlevel 1 (
  echo     [ERROR] Python deps are incomplete. Try deleting .venv and rerun this file.
  goto fail
)
echo     OK

echo [5/8] Preparing local runtime paths...
if not exist "_devproj" mkdir "_devproj" >nul 2>&1
set "VISIONFORGE_PYTHON=%CD%\.venv\Scripts\python.exe"
set "VISIONFORGE_PROJECT=%CD%\_devproj"
echo     VISIONFORGE_PROJECT=%VISIONFORGE_PROJECT%
echo     VISIONFORGE_PYTHON=%VISIONFORGE_PYTHON%

if exist "provider-config.json" (
  set "VISIONFORGE_PROVIDER_CONFIG=%CD%\provider-config.json"
  echo     provider config: !VISIONFORGE_PROVIDER_CONFIG!
) else (
  set "VISIONFORGE_PROVIDER_CONFIG="
  echo     provider config: not found; fixture provider will be used
)

echo [6/8] Checking provider-config safety...
if exist "provider-config.json" (
  where git >nul 2>&1
  if errorlevel 1 (
    findstr /x /c:"provider-config.json" ".gitignore" >nul 2>&1
    if errorlevel 1 (
      echo     [ERROR] provider-config.json is not listed in .gitignore.
      echo     Refusing to launch to avoid accidentally exposing a key.
      goto fail
    )
  ) else (
    git check-ignore -q provider-config.json >nul 2>&1
    if errorlevel 1 (
      echo     [ERROR] provider-config.json is not ignored by Git.
      echo     Refusing to launch to avoid accidentally exposing a key.
      goto fail
    )
  )
)
echo     OK

echo [7/8] Installing UI dependencies...
if not exist "ui\node_modules" (
  call :pnpm --dir .\ui install
  if errorlevel 1 goto fail
) else (
  echo     ui\node_modules exists
)

echo [8/8] Verifying Electron install...
if not exist "ui\node_modules\electron\dist\electron.exe" (
  echo     Electron binary missing; rebuilding electron package...
  call :pnpm --dir .\ui rebuild electron
  if errorlevel 1 goto fail
)
if not exist "ui\node_modules\electron\dist\electron.exe" (
  echo     [ERROR] Electron binary is still missing after rebuild.
  echo     Try deleting ui\node_modules, then rerun this launcher.
  goto fail
)
echo     OK

if defined CHECK_ONLY (
  echo.
  echo Startup check OK. Run start-visionforge.bat without --check to launch.
  goto success
)

echo.
echo Launching VisionForge. Close the Electron window or press Ctrl+C here to stop.
echo.
call :pnpm --dir .\ui dev
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo [ERROR] Electron dev server exited with code %EXIT_CODE%.
  goto fail
)

goto success

:pnpm
set "BUNDLED_PNPM=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\pnpm.cmd"
if exist "%BUNDLED_PNPM%" (
  call "%BUNDLED_PNPM%" %*
  exit /b %ERRORLEVEL%
)

where pnpm.cmd >nul 2>&1
if not errorlevel 1 (
  for /f "delims=" %%v in ('pnpm.cmd --version 2^>nul') do set "PNPM_VERSION=%%v"
  if "!PNPM_VERSION!"=="11.7.0" (
    call pnpm.cmd %*
    exit /b %ERRORLEVEL%
  )
  echo     [WARN] PATH pnpm is !PNPM_VERSION!, but this project requires 11.7.0.
)

where corepack >nul 2>&1
if not errorlevel 1 (
  call corepack pnpm@11.7.0 %*
  exit /b %ERRORLEVEL%
)

echo     [ERROR] pnpm 11.7.0 was not found.
echo     Enable corepack or use the bundled Codex runtime pnpm.
exit /b 1

:success
echo.
echo Done.
pause
popd >nul 2>&1
endlocal
exit /b 0

:fail
echo.
echo Startup failed. The window is staying open so the error can be read.
pause
popd >nul 2>&1
endlocal
exit /b 1
