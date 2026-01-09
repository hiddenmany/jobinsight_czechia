$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$outputFile = "Combined_GEMINI.md"

# Get all .md files excluding the output file and Main_GEMINI.md (handled separately)
$otherFiles = Get-ChildItem -Filter "*.md" | Where-Object { $_.Name -ne $outputFile -and $_.Name -ne "Main_GEMINI.md" } | Select-Object -ExpandProperty Name

# Define order: Main first, then others
$filesToProcess = @("Main_GEMINI.md") + $otherFiles

Write-Host "Building Context..."
$content = @()

foreach ($file in $filesToProcess) {
    if (Test-Path $file) {
        Write-Host " + Adding: $file"
        $content += Get-Content -Path $file -Raw
        $content += "`n---`n" # Add separator
    } else {
        Write-Warning "File not found: $file"
    }
}

$content | Set-Content -Path $outputFile -Encoding UTF8
Write-Host "Done! Created $outputFile"