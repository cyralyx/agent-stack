Set oWS = WScript.CreateObject("WScript.Shell")
Set oFS = CreateObject("Scripting.FileSystemObject")

'exe and icon paths
exePath = "C:\Users\willi\AppData\Local\Programs\AgentStack\AgentStack.exe"
iconPath = "C:\Users\willi\AppData\Local\Programs\AgentStack\logo.ico"
desktop = oWS.SpecialFolders("Desktop")

'ensure icon exists at exe dir (from resources/app)
iconSrc = "C:\Users\willi\AppData\Local\Programs\AgentStack\resources\app\logo.ico"
If Not oFS.FileExists(iconPath) And oFS.FileExists(iconSrc) Then
  oFS.CopyFile iconSrc, iconPath, True
End If

Set lnk = oWS.CreateShortcut(desktop & "\AgentStack.lnk")
lnk.TargetPath = exePath
lnk.WorkingDirectory = "C:\Users\willi\AppData\Local\Programs\AgentStack"
lnk.IconLocation = iconPath
lnk.Description = "AgentStack — Hermes brain + OpenClaw hands + Obsidian memory"
lnk.Save

WScript.Echo "Desktop shortcut created: " & desktop & "\AgentStack.lnk"
