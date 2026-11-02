' Prečica na desktopu poziva ovo: diže lokalni server bez prozora (ako već radi, novi se sam ugasi) i otvara aplikaciju.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run """C:\Program Files\nodejs\node.exe"" app_server.js", 0, False
WScript.Sleep 800
sh.Run "http://localhost:8765/"
