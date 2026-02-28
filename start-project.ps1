param(
  [string]$Distro = "Ubuntu-22.04",
  [string]$FrontendPort = "8001",
  [string]$OpenAIKey = $env:OPENAI_API_KEY,
  [string]$Location = $env:FRONTEND_LOCATION
)
$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$drive = $ProjectPath.Substring(0,1).ToLower()
$rest = $ProjectPath.Substring(2).Replace("\","/")
$WslPath = "/mnt/$drive$rest"
$env:FRONTEND_PORT = $FrontendPort
if ($OpenAIKey) { $env:OPENAI_API_KEY = $OpenAIKey }
if ($Location) { $env:FRONTEND_LOCATION = $Location }
Start-Process -FilePath "wsl" -ArgumentList "-d $Distro -- bash -lc 'cd ""$WslPath"" && python3 app.py'" -WindowStyle Normal
Start-Process -FilePath "powershell" -ArgumentList "-NoExit -Command ""cd '$ProjectPath'; python .\frontend.py""" -WindowStyle Normal
Start-Process "http://localhost:$FrontendPort/"
