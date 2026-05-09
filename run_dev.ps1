# Arranca o servidor sempre a partir desta pasta (evita importar outro pacote `app`).
# Porta 8010 por defeito: em 8000 costumam acumular-se vários uvicorn e o pedido cai na API errada (ex.: 0.2.0).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$port = if ($env:META_AUDITOR_PORT) { [int]$env:META_AUDITOR_PORT } else { 8010 }
for ($round = 0; $round -lt 6; $round++) {
    $pids = @(
        Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique |
            Where-Object { $_ -and $_ -ne 0 }
    )
    if ($pids.Count -eq 0) { break }
    foreach ($procId in $pids) {
        Write-Host "A terminar processo $procId (porta $port, ronda $($round + 1))..."
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
}
$still = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
if ($still.Count -gt 0) {
    Write-Host "AVISO: ainda ha escutas na porta $port. Feche outros terminais com uvicorn ou execute como administrador."
}

$Uvicorn = Join-Path $Root ".venv\Scripts\uvicorn.exe"
if (-not (Test-Path $Uvicorn)) {
    Write-Host "Crie o venv: py -3 -m venv .venv && .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
    exit 1
}
Write-Host "Meta-Auditor em http://127.0.0.1:$port/docs (META_AUDITOR_PORT para mudar a porta)"
& $Uvicorn "app.main:app" --reload --host 127.0.0.1 --port $port
