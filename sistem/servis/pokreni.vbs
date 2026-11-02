' Task Scheduler poziva ovo da se na svakih 10 min ne otvara prozor konzole.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run """C:\Program Files\nodejs\node.exe"" kvote_servis.js", 0, False
