# Crea y sube un video sobre una tendencia del día, sin intervención.
# Lo ejecuta la tarea programada de Windows (ver instalar_tarea_diaria.ps1).
# También puedes probarlo a mano:  powershell -ExecutionPolicy Bypass -File .\diario.ps1

$ErrorActionPreference = "Continue"
Set-Location -Path $PSScriptRoot
New-Item -ItemType Directory -Force -Path "logs" | Out-Null
$log = "logs\$(Get-Date -Format 'yyyy-MM-dd_HHmm').txt"

$prompt = @"
Ejecuta el MODO DIARIO de CLAUDE.md: elige la mejor tendencia de hoy, investígala,
crea el video y súbelo. Termina imprimiendo la URL de YouTube o el error exacto.
"@

# Solo se permiten estas herramientas: no se usa --dangerously-skip-permissions.
claude -p $prompt `
  --allowedTools "Bash(python scripts/*)" "Bash(python -m pip install *)" "Bash(ffmpeg *)" `
                 "Read" "Write" "Edit" "Glob" "Grep" "WebSearch" "WebFetch" `
  *>&1 | Tee-Object -FilePath $log

# Mantiene solo los últimos 30 logs
Get-ChildItem logs\*.txt | Sort-Object LastWriteTime -Descending | Select-Object -Skip 30 | Remove-Item
