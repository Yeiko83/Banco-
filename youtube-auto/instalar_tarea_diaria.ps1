# Registra en el Programador de tareas de Windows la ejecución diaria de diario.ps1.
# Uso (PowerShell normal, no hace falta administrador):
#   powershell -ExecutionPolicy Bypass -File .\instalar_tarea_diaria.ps1 -Hora "18:00"
# Para quitarla:  Unregister-ScheduledTask -TaskName "YouTubeAutoDiario" -Confirm:$false

param([string]$Hora = "18:00")

$script = Join-Path $PSScriptRoot "diario.ps1"
$accion = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`"" `
  -WorkingDirectory $PSScriptRoot
$disparador = New-ScheduledTaskTrigger -Daily -At $Hora
# StartWhenAvailable: si el PC estaba apagado a esa hora, se ejecuta al encenderlo.
$opciones = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun `
  -ExecutionTimeLimit (New-TimeSpan -Hours 2) -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries

Register-ScheduledTask -TaskName "YouTubeAutoDiario" -Action $accion -Trigger $disparador `
  -Settings $opciones -Description "Crea y sube un video de tendencia a YouTube" -Force | Out-Null

Write-Host "Tarea 'YouTubeAutoDiario' creada: todos los días a las $Hora."
Write-Host "Pruébala ya con:  Start-ScheduledTask -TaskName YouTubeAutoDiario"
