# Imagen de Pensunet: interfaz Streamlit con los CSV agregados del repositorio.
# Construir:  docker build -t pensunet .
# Ejecutar:   docker run --rm -p 8501:8501 pensunet   → http://localhost:8501
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Metadatos primero para aprovechar la caché de capas.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
# Solo datos agregados (pensum, prerrequisitos y tasas); data/private no se copia.
COPY data/reference ./data/reference
COPY data/processed ./data/processed
COPY .streamlit ./.streamlit

# Instalación editable: el paquete localiza data/ relativo a src/ (programas.py).
RUN pip install -e ".[ui]" \
    && useradd --create-home --uid 1000 pensunet \
    && chown -R pensunet /app
USER pensunet

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=4)"

CMD ["streamlit", "run", "src/pensunet/ui/app.py", \
     "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
