# Gera meta-auditor-entrega-*.zip na raiz do repo — sem .venv, caches, .env, dados locais.
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$stamp = Get-Date -Format "yyyyMMdd-HHmm"
$StageName = "meta-auditor-entrega-$stamp"
$Stage = Join-Path $env:TEMP $StageName

if (Test-Path $Stage) {
    Remove-Item $Stage -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $Stage | Out-Null

# Copiar projeto excluindo pastas pesadas / IDE (ajuste /XD se precisar)
$rc = Start-Process -FilePath "robocopy" -ArgumentList @(
    "`"$Root`"", "`"$Stage`"", "/E",
    "/XD", ".venv", ".git", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cursor", ".idea", ".vscode", "node_modules",
    "/NFL", "/NDL", "/NJH", "/NJS", "/NP"
) -Wait -PassThru -NoNewWindow

if ($rc.ExitCode -ge 8) {
    throw "robocopy falhou com código $($rc.ExitCode)"
}

# Segredos e dados de runtime nunca no pacote institucional
Remove-Item (Join-Path $Stage ".env") -Force -ErrorAction SilentlyContinue
$db = Join-Path $Stage "data\meta_auditor.db"
if (Test-Path $db) {
    Remove-Item $db -Force
}
$raw = Join-Path $Stage "data\raw"
if (Test-Path $raw) {
    Get-ChildItem $raw -Filter "*.json" -ErrorAction SilentlyContinue | Remove-Item -Force
}
$ev = Join-Path $Stage "data\evidence"
if (Test-Path $ev) {
    Get-ChildItem $ev -Filter "*.png" -ErrorAction SilentlyContinue | Remove-Item -Force
}

Get-ChildItem $Stage -Directory -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item $_.FullName -Recurse -Force }

Get-ChildItem $Stage -Filter "*.pyc" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force

# Material interno de empacotamento — não vai para revisores
Remove-Item (Join-Path $Stage "ENTREGA.md") -Force -ErrorAction SilentlyContinue

# Evitar incluir ZIPs de entregas anteriores se estiverem na árvore copiada
Get-ChildItem $Stage -Filter "meta-auditor-entrega*.zip" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force

$zipName = "$StageName.zip"
$zipPath = Join-Path $Root $zipName
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $zipPath -Force
Remove-Item $Stage -Recurse -Force

Write-Host ""
Write-Host "Pacote de entrega criado:"
Write-Host "  $zipPath"
Write-Host ""
Write-Host "Validação sugerida: smoke test + Docker (README)."
Write-Host ""
