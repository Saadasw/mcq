# Script to download and install Noto Sans Bengali font on Windows
# Requires administrator privileges

Write-Host "Installing Noto Sans Bengali font..." -ForegroundColor Green

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Warning: Not running as administrator. Font installation may require admin rights." -ForegroundColor Yellow
}

# Create temporary directory
$tempDir = Join-Path $env:TEMP "noto_bengali_$(Get-Date -Format 'yyyyMMddHHmmss')"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

try {
    # Download Noto Sans Bengali from Google Fonts CDN
    Write-Host "Downloading font files..." -ForegroundColor Yellow
    
    $fonts = @(
        @{Name="NotoSansBengali-Regular.ttf"; Url="https://github.com/google/fonts/raw/main/ofl/notosansbengali/NotoSansBengali-Regular.ttf"},
        @{Name="NotoSansBengali-Bold.ttf"; Url="https://github.com/google/fonts/raw/main/ofl/notosansbengali/NotoSansBengali-Bold.ttf"}
    )
    
    foreach ($font in $fonts) {
        $fontPath = Join-Path $tempDir $font.Name
        Write-Host "Downloading $($font.Name)..." -ForegroundColor Cyan
        try {
            Invoke-WebRequest -Uri $font.Url -OutFile $fontPath -UseBasicParsing
            Write-Host "  Downloaded successfully" -ForegroundColor Green
        } catch {
            Write-Host "  Failed to download: $_" -ForegroundColor Red
            continue
        }
        
        # Install font
        try {
            $fontDir = "C:\Windows\Fonts"
            $destPath = Join-Path $fontDir $font.Name
            
            if ($isAdmin) {
                Copy-Item -Path $fontPath -Destination $destPath -Force
                Write-Host "  Installed to $fontDir" -ForegroundColor Green
            } else {
                # Try to install for current user
                $userFontDir = Join-Path $env:LOCALAPPDATA "Microsoft\Windows\Fonts"
                New-Item -ItemType Directory -Force -Path $userFontDir | Out-Null
                Copy-Item -Path $fontPath -Destination (Join-Path $userFontDir $font.Name) -Force
                Write-Host "  Installed to user fonts directory" -ForegroundColor Green
            }
        } catch {
            Write-Host "  Failed to install: $_" -ForegroundColor Red
            Write-Host "  You may need to install manually by right-clicking the .ttf file and selecting Install" -ForegroundColor Yellow
        }
    }
    
    Write-Host ""
    Write-Host "Font installation complete!" -ForegroundColor Green
    Write-Host "You may need to restart your LaTeX compiler or rebuild the font cache." -ForegroundColor Yellow
    Write-Host "For MiKTeX, run: luaotfload-tool -u" -ForegroundColor Cyan
    
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
} finally {
    # Cleanup
    Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}
