# Registruje Windows zadatak EvroligaKvote (okida na 10 min, radi samo dok si prijavljen, bez administratorskih prava).
# Uklanjanje: Unregister-ScheduledTask -TaskName EvroligaKvote -Confirm:$false
$dir = $PSScriptRoot
$a = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument "`"$dir\pokreni.vbs`"" -WorkingDirectory $dir
$t = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 10)
$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 25)
$p = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName 'EvroligaKvote' -Action $a -Trigger $t -Settings $s -Principal $p -Description 'Prikupljanje kvota Evrolige (faza 1, samo snimanje)' -Force | Out-Null
Get-ScheduledTask -TaskName 'EvroligaKvote' | Select-Object TaskName, State
