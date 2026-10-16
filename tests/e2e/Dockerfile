# Imagem dos testes de interface e ponta a ponta.
# A imagem oficial traz o Python e os navegadores do Playwright, mas não o
# pacote "playwright" do Python, que precisa ser instalado na mesma versão.
FROM mcr.microsoft.com/playwright/python:v1.56.0-noble

RUN python -m pip install --no-cache-dir --break-system-packages playwright==1.56.0

ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /projeto
