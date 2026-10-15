#!/usr/bin/env bash
# Executa todos os testes do projeto no Docker (Linux e macOS).
# Uso, na pasta do projeto:   bash scripts/testar.sh
#
# Etapas:
#   1. Implantação: constrói as imagens e sobe os serviços, esperando o healthcheck
#   2. Backend: testes unitários e dos endpoints (unittest)
#   3. Frontend: testes unitários dos módulos JavaScript (node --test)
#   4. Interface e ponta a ponta: Playwright contra http://frontend (Nginx + backend)

set -u
declare -a nomes resultados
falhou=0

executar() {
  local nome="$1"; shift
  echo; echo "=== $nome ==="
  if "$@"; then resultados+=("OK"); else resultados+=("FALHOU (código $?)"); falhou=1; fi
  nomes+=("$nome")
}

executar "1. Implantação (build + healthcheck)" docker compose up -d --build --wait
executar "2. Testes do backend"                 docker compose --profile testes run --rm testes-backend
executar "3. Testes do frontend"                docker compose --profile testes run --rm testes-frontend
executar "4. Testes de interface (Playwright)"  docker compose --profile testes run --rm testes-e2e

echo; echo "=== Resumo ==="
for i in "${!nomes[@]}"; do printf '%-42s %s\n' "${nomes[$i]}" "${resultados[$i]}"; done
echo; echo "A aplicação continua no ar em http://localhost:8080 (encerre com: docker compose down)."
exit $falhou
