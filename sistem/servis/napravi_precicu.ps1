# Pravi prečicu "Edgeline" na desktopu. Uklanjanje: samo obriši prečicu.
$dir = $PSScriptRoot
$desktop = [Environment]::GetFolderPath('Desktop')
$s = (New-Object -ComObject WScript.Shell).CreateShortcut("$desktop\Edgeline.lnk")
$s.TargetPath = "$env:WINDIR\System32\wscript.exe"
$s.Arguments = "`"$dir\pokreni_aplikaciju.vbs`""
$s.WorkingDirectory = $dir
$ikona = Join-Path (Split-Path (Split-Path $dir)) 'ikona.ico'
if (Test-Path $ikona) { $s.IconLocation = $ikona }
$s.Save()
"Prečica: $desktop\Edgeline.lnk"
