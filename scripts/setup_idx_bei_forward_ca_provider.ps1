param(
    [string]$Checkout = "D:\Documents\Project\idx-bei-forward-ca-provider"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$repo = "https://github.com/nichsedge/idx-bei.git"
$pin = "75d6c0f74fa360d225794c70c383348977de6798"

function Resolve-UvExecutable {
    $cmd = Get-Command uv -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $candidates = @(
        (Join-Path $HOME ".local\bin\uv.exe"),
        (Join-Path $HOME ".cargo\bin\uv.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            $dir = Split-Path -Parent $candidate
            if (($env:Path -split ';') -notcontains $dir) {
                $env:Path = "$dir;$env:Path"
            }
            return $candidate
        }
    }
    return $null
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git not found. Install Git for Windows first: https://git-scm.com/download/win"
}

$uv = Resolve-UvExecutable
if (-not $uv) {
    Write-Host "uv not found. Installing uv with Astral's official Windows installer..."
    try {
        $installer = Invoke-RestMethod -Uri "https://astral.sh/uv/install.ps1" -UseBasicParsing
        Invoke-Expression $installer
    }
    catch {
        throw "Automatic uv install failed: $($_.Exception.Message)"
    }

    $uv = Resolve-UvExecutable
    if (-not $uv) {
        throw "uv installer completed but uv.exe was not found in PATH, $HOME\.local\bin, or $HOME\.cargo\bin"
    }
}

Write-Host "Using uv: $uv"
& $uv --version
if ($LASTEXITCODE -ne 0) { throw "uv smoke test failed" }

# idx-bei currently requires Python >=3.13. Let uv manage an isolated 3.13 runtime
# so the user's system Python and IDX-Trade environment are not modified.
Write-Host "Ensuring isolated Python 3.13 is available through uv..."
& $uv python install 3.13
if ($LASTEXITCODE -ne 0) { throw "uv Python 3.13 installation failed" }

if (-not (Test-Path -LiteralPath $Checkout)) {
    Write-Host "Cloning pinned idx-bei provider checkout..."
    git clone $repo $Checkout
    if ($LASTEXITCODE -ne 0) { throw "idx-bei clone failed" }
}

$actualRepo = (git -C $Checkout remote get-url origin).Trim()
if ($LASTEXITCODE -ne 0) { throw "cannot read idx-bei origin" }
if ($actualRepo -notmatch "nichsedge/idx-bei") {
    throw "unexpected idx-bei origin: $actualRepo"
}

git -C $Checkout fetch --all --tags --prune
if ($LASTEXITCODE -ne 0) { throw "idx-bei fetch failed" }

git -C $Checkout checkout --detach $pin
if ($LASTEXITCODE -ne 0) { throw "idx-bei pinned checkout failed" }

$head = (git -C $Checkout rev-parse HEAD).Trim()
if ($head -ne $pin) {
    throw "idx-bei pin mismatch: $head != $pin"
}

$project = Join-Path $Checkout "python"
if (-not (Test-Path -LiteralPath $project)) {
    throw "idx-bei python project missing: $project"
}

Write-Host "Syncing isolated idx-bei provider environment..."
& $uv sync --project $project
if ($LASTEXITCODE -ne 0) { throw "idx-bei uv sync failed" }

Write-Host "Running provider import-only smoke test (no IDX request)..."
& $uv run --project $project python -c "from idx.core.client import IDXClient; c=IDXClient(); print(c.base_url)"
if ($LASTEXITCODE -ne 0) { throw "idx-bei import smoke test failed" }

Write-Host ""
Write-Host "IDX-BEI Forward CA provider prepared"
Write-Host "Checkout: $Checkout"
Write-Host "Commit:   $head"
Write-Host "uv:       $uv"
Write-Host "No IDX provider/network data request was made by this setup script."
