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

$ErrorActionPreference = "Continue"
$resultados = [ordered]@{}

function Registrar($nome, $ok) {
    $resultados[$nome] = $(if ($ok) { "OK" } else { "FALHOU" })
}

function Postar($url, $corpo) {
    $bytes = [Text.Encoding]::UTF8.GetBytes(($corpo | ConvertTo-Json -Compress))
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Method Post -Uri $url -Body $bytes -ContentType "application/json" -TimeoutSec 240
        return @{ status = [int]$r.StatusCode; texto = [Text.Encoding]::UTF8.GetString($r.RawContentStream.ToArray()) }
    } catch {
        $codigo = 0
        if ($_.Exception.Response) { $codigo = [int]$_.Exception.Response.StatusCode }
        return @{ status = $codigo; texto = "$($_.ErrorDetails.Message)" }
    }
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
$analise = Postar "http://localhost:8080/api/analisar" @{ codigo = "resultado = 10 + 5 * 2" }
$ia = Postar "http://localhost:8080/api/ia/explicar" @{ tipo = "pergunta"; codigo = ""; pergunta = "teste" }
Write-Host "Analise com o ollama parado: HTTP $($analise.status)"
Write-Host "Assistente com o ollama parado: HTTP $($ia.status)"
Registrar "5a. Analise funciona com o ollama parado" ($analise.status -eq 200 -and $analise.texto -match '"sucesso":true')
Registrar "5b. IA parada responde 503 com mensagem" ($ia.status -eq 503 -and $ia.texto -match "ia_indisponivel")
docker compose start ollama

Write-Host ""
Write-Host "=== Resumo ===" -ForegroundColor Cyan
$falhou = $false
foreach ($item in $resultados.GetEnumerator()) {
    $cor = $(if ($item.Value -eq "OK") { "Green" } else { "Red"; $falhou = $true })
    Write-Host ("{0,-50} {1}" -f $item.Key, $item.Value) -ForegroundColor $cor
}
if ($falhou) { exit 1 } else { exit 0 }
