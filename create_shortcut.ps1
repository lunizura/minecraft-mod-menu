$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("C:\Users\asus\Desktop\Minecraft Mod Menu.lnk")
$Shortcut.TargetPath = "C:\Users\asus\Desktop\Minecraft_Mod_Menu.exe"
$Shortcut.WorkingDirectory = "C:\Users\asus\.gemini\antigravity\scratch\mc-mod-menu"
$Shortcut.Description = "Minecraft All-in-One Mod Menu and World Editor"
$Shortcut.IconLocation = "C:\Users\asus\.gemini\antigravity\scratch\mc-mod-menu\assets\icon.ico,0"
$Shortcut.Save()
Write-Host "Shortcut created successfully at C:\Users\asus\Desktop\Minecraft Mod Menu.lnk"
