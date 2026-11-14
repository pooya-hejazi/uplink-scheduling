param([string]$Tectonic="tectonic", [string]$CacheDirectory, [string]$Python="python")
$ErrorActionPreference = "Stop"
if ($CacheDirectory) { $env:TECTONIC_CACHE_DIR=$CacheDirectory }
Push-Location -LiteralPath $PSScriptRoot
try {
    & $Python build_submission.py
    if ($LASTEXITCODE -ne 0) { throw "Submission source expansion failed ($LASTEXITCODE)" }
    foreach ($source in 'main_nature.tex', 'Supplementary_Information.tex') {
        & $Tectonic --keep-logs $source
        if ($LASTEXITCODE -ne 0) { throw "Tectonic failed on $source ($LASTEXITCODE)" }
    }
} finally { Pop-Location }

