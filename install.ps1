$repoUrl = "https://github.com/cambrianminds/gh-tui.git"
$installDir = Join-Path $env:USERPROFILE ".gh-tui"
$binDir = Join-Path $installDir "bin"

Write-Host "Installing gh-tui..." -ForegroundColor Cyan

# Check if git and python are installed
if (-not (Get-Command "git" -ErrorAction SilentlyContinue)) {
    Write-Error "Git is not installed or not in PATH."
    exit 1
}
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH."
    exit 1
}

# Clone or update
if (Test-Path $installDir) {
    Write-Host "Updating existing installation in $installDir..."
    Push-Location $installDir
    git pull
} else {
    Write-Host "Cloning repository to $installDir..."
    git clone $repoUrl $installDir
    Push-Location $installDir
}

# Setup venv and dependencies
Write-Host "Setting up Python virtual environment..."
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt -q

# Create wrapper script
Write-Host "Creating executable wrapper..."
if (-not (Test-Path $binDir)) {
    New-Item -ItemType Directory -Force -Path $binDir | Out-Null
}

$batPath = Join-Path $binDir "gh-tui.cmd"
$batContent = "@echo off`n`"$installDir\venv\Scripts\python.exe`" `"$installDir\app.py`" %*"
Set-Content -Path $batPath -Value $batContent

# Update PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notmatch [regex]::Escape($binDir)) {
    Write-Host "Adding $binDir to user PATH..." -ForegroundColor Yellow
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$binDir", "User")
    $env:Path = "$env:Path;$binDir"
    Write-Host "Path updated. You may need to restart your terminal for changes to take effect in new windows." -ForegroundColor Yellow
}

Pop-Location
Write-Host ""
Write-Host "Installation complete! You can now run 'gh-tui' from anywhere in your terminal." -ForegroundColor Green
