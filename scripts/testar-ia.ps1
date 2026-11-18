# Valida o assistente de IA (Ollama + Llama 3.2) no Docker (Windows PowerShell).
# Uso, na pasta do projeto:   powershell -ExecutionPolicy Bypass -File scripts\testar-ia.ps1
#
# Etapas:
#   1. Sobe os servicos (backend, frontend e ollama)
#   2. Baixa o modelo llama3.2 se ainda nao estiver no volume (cerca de 2 GB, so na primeira vez)
#   3. Recria o conteiner do ollama e confere que o modelo continua no volume
#   4. Demonstracao: explica um no da AST, um erro sintatico, um token e uma pergunta
#      (respostas gravadas em docs\validacao\ia-demo.json)
#   5. Com o ollama parado, a analise continua funcionando e a IA responde "indisponivel"
#      (registro em docs\\validacao\\ia-sem-ollama.json)

$ErrorActionPreference = "Continue"
$resultados = [ordered]@{}

function Registrar($nome, $ok) {
    $resultados[$nome] = $(if ($ok) { "OK" } else { "FALHOU" })
}

Write-Host "=== 1. Subindo os servicos ===" -ForegroundColor Cyan
docker compose up -d --build --wait
Registrar "1. Servicos no ar (backend, frontend, ollama)" ($LASTEXITCODE -eq 0)

Write-Host ""
Write-Host "=== 2. Modelo llama3.2 ===" -ForegroundColor Cyan
$lista = docker compose exec ollama ollama list
if (-not ($lista -match "llama3.2")) {
    Write-Host "Baixando llama3.2 (cerca de 2 GB, so na primeira vez)..."
    docker compose exec ollama ollama pull llama3.2
}
$lista = docker compose exec ollama ollama list
Write-Host ($lista -join "`n")
Registrar "2. Modelo llama3.2 instalado" ($lista -match "llama3.2")

Write-Host ""
Write-Host "=== 3. Volume persiste depois de recriar o conteiner ===" -ForegroundColor Cyan
docker compose up -d --force-recreate ollama
Start-Sleep -Seconds 5
$lista = docker compose exec ollama ollama list
Write-Host ($lista -join "`n")
Registrar "3. Modelo continua no volume apos recriar" ($lista -match "llama3.2")

Write-Host ""
Write-Host "=== 4. Demonstracao (pode levar alguns minutos no processador) ===" -ForegroundColor Cyan
docker compose exec backend python -m app.demo_ia
$demoOk = ($LASTEXITCODE -eq 0)
docker compose cp backend:/tmp/ia-demo.json docs/validacao/ia-demo.json
Registrar "4. Explicacoes geradas pelo Llama 3.2" $demoOk
Write-Host "Respostas completas gravadas em docs\validacao\ia-demo.json (abra no VS Code ou no navegador)."

Write-Host ""
Write-Host "=== 5. Aplicacao sem a IA ===" -ForegroundColor Cyan
docker compose stop ollama
# A verificacao roda dentro do conteiner do backend (sem depender do PowerShell).
docker compose exec backend python -m app.demo_ia --sem-ia
$semIaOk = ($LASTEXITCODE -eq 0)
docker compose cp backend:/tmp/ia-sem-ollama.json docs/validacao/ia-sem-ollama.json
Registrar "5. Analise funciona e IA responde 503 com o ollama parado" $semIaOk
docker compose start ollama

Write-Host ""
Write-Host "=== Resumo ===" -ForegroundColor Cyan
$falhou = $false
foreach ($item in $resultados.GetEnumerator()) {
    $cor = $(if ($item.Value -eq "OK") { "Green" } else { "Red"; $falhou = $true })
    Write-Host ("{0,-50} {1}" -f $item.Key, $item.Value) -ForegroundColor $cor
}
if ($falhou) { exit 1 } else { exit 0 }
