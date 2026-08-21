param(
    [string]$Checkout = "D:\Documents\Project\idx-bei-forward-ca-provider"
)

$ErrorActionPreference = "Stop"
$repo = "https://github.com/nichsedge/idx-bei.git"
$pin = "75d6c0f74fa360d225794c70c383348977de6798"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git not found"
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv not found"
}

if (-not (Test-Path -LiteralPath $Checkout)) {
    git clone $repo $Checkout
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
uv sync --project $project
if ($LASTEXITCODE -ne 0) { throw "idx-bei uv sync failed" }

uv run --project $project python -c "from idx.core.client import IDXClient; c=IDXClient(); print(c.base_url)"
if ($LASTEXITCODE -ne 0) { throw "idx-bei import smoke test failed" }

Write-Host "IDX-BEI Forward CA provider prepared"
Write-Host "Checkout: $Checkout"
Write-Host "Commit:   $head"
Write-Host "No IDX provider/network data request was made by this setup script."
