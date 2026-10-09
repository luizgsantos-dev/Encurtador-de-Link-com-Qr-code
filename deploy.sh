#!/usr/bin/env bash
# Deploy do stack "encurtador" no Swarm.
# Uso: ./deploy.sh
#
# Faz em sequência:
#   1. Exporta as variáveis do .env pro shell (docker stack deploy não lê o
#      .env sozinho pra resolver ${VAR}, diferente do `docker compose up`).
#   2. Builda as imagens locais (encurtador-api / encurtador-web).
#   3. Roda o stack deploy.
#   4. Força a recriação dos serviços, já que a tag da imagem continua
#      "latest" e o Swarm nem sempre percebe que o conteúdo mudou.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -f .env ]; then
  echo "Arquivo .env não encontrado em $(pwd). Abortando." >&2
  exit 1
fi

echo "==> Carregando variáveis do .env"
set -a
source .env
set +a

echo "==> Build das imagens (api + web)"
docker compose build api web

echo "==> Deploy do stack"
docker stack deploy -c docker-compose.yml -c docker-compose.prod.yml encurtador

echo "==> Forçando recriação dos serviços api e web"
docker service update --force encurtador_api
docker service update --force encurtador_web

echo "==> Concluído. Verifique com: docker service ps encurtador_api --no-trunc"
