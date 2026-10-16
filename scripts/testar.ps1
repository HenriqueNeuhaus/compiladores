# Executa todos os testes do projeto no Docker (Windows PowerShell).
# Uso, na pasta do projeto:   powershell -ExecutionPolicy Bypass -File scripts\testar.ps1
#
# Etapas:
#   1. Implantação: constrói as imagens e sobe os serviços, esperando o healthcheck
#   2. Backend: testes unitários e dos endpoints (unittest)
#   3. Frontend: testes unitários dos módulos JavaScript (node --test)
#   4. Interface e ponta a ponta: Playwright contra http://frontend (Nginx + backend)

$ErrorActionPreference = "Continue"
$resultados = [ordered]@{}

function Executar($nome, [scriptblock]$bloco) {
    Write-Host ""
    Write-Host "=== $nome ===" -ForegroundColor Cyan
    & $bloco
    $ok = ($LASTEXITCODE -eq 0)
    $resultados[$nome] = $(if ($ok) { "OK" } else { "FALHOU (codigo $LASTEXITCODE)" })
}

Executar "1. Implantacao (build + healthcheck)" { docker compose up -d --build --wait }
Executar "2. Testes do backend"                 { docker compose --profile testes run --build --rm testes-backend }
Executar "3. Testes do frontend"                { docker compose --profile testes run --build --rm testes-frontend }
Executar "4. Testes de interface (Playwright)"  { docker compose --profile testes run --build --rm testes-e2e }

Write-Host ""
Write-Host "=== Resumo ===" -ForegroundColor Cyan
$falhou = $false
foreach ($item in $resultados.GetEnumerator()) {
    $cor = $(if ($item.Value -eq "OK") { "Green" } else { "Red"; $falhou = $true })
    Write-Host ("{0,-42} {1}" -f $item.Key, $item.Value) -ForegroundColor $cor
}
Write-Host ""
Write-Host "A aplicacao continua no ar em http://localhost:8080 (encerre com: docker compose down)."
if ($falhou) { exit 1 } else { exit 0 }
