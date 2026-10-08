FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# PyTorch CPU-only ANTES do laya, pelo índice da CPU: o laya encontra o torch já instalado
# e a imagem não puxa o CUDA (vários GB a menos). Mesma versão do Dockerfile do Laya 0.4.0.
ARG TORCH_VERSION=2.14.0
RUN pip install "torch==${TORCH_VERSION}" --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install -r requirements.txt \
    && python -c "import torch; assert torch.version.cuda is None, 'o torch com CUDA foi instalado'"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
