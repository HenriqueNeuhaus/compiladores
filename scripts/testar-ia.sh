#!/usr/bin/env bash
# Valida o assistente de IA (Ollama + Llama 3.2) no Docker (Linux/macOS).
# Mesmas etapas de scripts/testar-ia.ps1.
set -u
falhou=0
registrar() { if [ "$2" = 0 ]; then echo "OK      $1"; else echo "FALHOU  $1"; falhou=1; fi; }

docker compose up -d --build --wait; registrar "1. Servicos no ar" $?
docker compose exec ollama ollama list | grep -q llama3.2 || docker compose exec ollama ollama pull llama3.2
docker compose exec ollama ollama list | grep -q llama3.2; registrar "2. Modelo llama3.2 instalado" $?
docker compose up -d --force-recreate ollama; sleep 5
docker compose exec ollama ollama list | grep -q llama3.2; registrar "3. Modelo continua no volume" $?
docker compose exec backend python -m app.demo_ia; r=$?
docker compose cp backend:/tmp/ia-demo.json docs/validacao/ia-demo.json
registrar "4. Explicacoes geradas pelo Llama 3.2" $r
docker compose stop ollama
curl -s -X POST localhost:8080/api/analisar -H 'Content-Type: application/json' -d '{"codigo":"x = 1"}' | grep -q '"sucesso":true'
registrar "5a. Analise funciona com o ollama parado" $?
test "$(curl -s -o /dev/null -w '%{http_code}' -X POST localhost:8080/api/ia/explicar -H 'Content-Type: application/json' -d '{"tipo":"pergunta","codigo":""}')" = 503
registrar "5b. IA parada responde 503" $?
docker compose start ollama
exit $falhou
