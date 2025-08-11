param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("update", "status", "logs", "help")]
    [string]$Action
)

# Server configuration
$global:ServerHost = "192.168.100.227"
$global:ServerUser = "archy"
$global:ServerPort = 22
$global:RemotePath = "~/MotuCalliLib"

function Show-Help {
    Write-Host " MotuCalliLib Remote Update Tool" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\remote_update.ps1 -Action [action]"
    Write-Host ""
    Write-Host "Actions:"
    Write-Host "  update   - Upload code and restart service"
    Write-Host "  status   - Check service status"
    Write-Host "  logs     - View real-time logs"
    Write-Host "  help     - Show help information"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\remote_update.ps1 -Action update"
    Write-Host "  .\remote_update.ps1 -Action status"
    Write-Host ""
    Write-Host "Server: $global:ServerUser@$global:ServerHost"
}

function Upload-Files {
    Write-Host " Uploading files to server..." -ForegroundColor Blue
    
    # Upload main files
    $files = @("app_new.py", "requirements.txt", "logger.py")
    
    foreach ($file in $files) {
        if (Test-Path $file) {
            Write-Host "  Uploading: $file"
            & scp -P $global:ServerPort $file "$($global:ServerUser)@$($global:ServerHost):$($global:RemotePath)/"
        }
    }
    
    # Upload directories
    if (Test-Path "static") {
        Write-Host "  Uploading: static/"
        & scp -r -P $global:ServerPort static "$($global:ServerUser)@$($global:ServerHost):$($global:RemotePath)/"
    }
    
    if (Test-Path "templates") {
        Write-Host "  Uploading: templates/"
        & scp -r -P $global:ServerPort templates "$($global:ServerUser)@$($global:ServerHost):$($global:RemotePath)/"
    }
    
    Write-Host " File upload completed" -ForegroundColor Green
}

function Update-App {
    Write-Host " Updating server application..." -ForegroundColor Blue
    
    $commands = @(
        "cd $($global:RemotePath)",
        "sudo systemctl stop motucallilib",
        "source .venv/bin/activate",
        "pip install -r requirements.txt",
        "sudo systemctl start motucallilib"
    )
    
    $commandScript = $commands -join " && "
    & ssh -p $global:ServerPort "$($global:ServerUser)@$($global:ServerHost)" $commandScript
    
    Write-Host " Application update completed" -ForegroundColor Green
}

function Get-Status {
    Write-Host " Checking service status..." -ForegroundColor Blue
    & ssh -p $global:ServerPort "$($global:ServerUser)@$($global:ServerHost)" "sudo systemctl status motucallilib --no-pager"
}

function Get-Logs {
    Write-Host "📋 Viewing real-time logs (Press Ctrl+C to exit)..." -ForegroundColor Blue
    & ssh -p $global:ServerPort "$($global:ServerUser)@$($global:ServerHost)" "sudo journalctl -u motucallilib -f"
}

# Main program
Write-Host " MotuCalliLib Remote Update Tool" -ForegroundColor Cyan
Write-Host "Server: $global:ServerUser@$global:ServerHost" -ForegroundColor Yellow
Write-Host ""

switch ($Action.ToLower()) {
    "help" {
        Show-Help
    }
    "update" {
        Upload-Files
        Update-App
        Get-Status
        Write-Host ""
        Write-Host " Update completed! Access URL: http://$global:ServerHost" -ForegroundColor Green
    }
    "status" {
        Get-Status
    }
    "logs" {
        Get-Logs
    }
    default {
        Write-Host "❌ Unknown action: $Action" -ForegroundColor Red
        Show-Help
    }
}