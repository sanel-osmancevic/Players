' Task Scheduler poziva ovo da se na svakih 10 min ne otvara prozor konzole; čeka kraj, da se pokretanja ne preklapaju.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run """C:\Program Files\nodejs\node.exe"" tik.js", 0, True
