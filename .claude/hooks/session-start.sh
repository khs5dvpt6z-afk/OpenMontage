#!/bin/bash
# OpenMontage — Claude Code bulut oturumu başlangıç betiği.
#
# Her yeni bulut oturumunda çalışan kurulumu yeniden üretir:
#   - .venv + Python bağımlılıkları + piper-tts
#   - remotion-composer npm paketleri
#   - Piper Türkçe ses modeli (tr_TR-dfki-medium, Hugging Face'ten)
#   - Remotion Chrome Headless Shell (remotion.media'dan, proxy üzerinden)
#   - Oturum ortamı: PATH (.venv/bin), NODE_USE_ENV_PROXY, NODE_EXTRA_CA_CERTS
#
# Gizli anahtar içermez. API anahtarları depoya değil, ortam ayarlarındaki
# gizli değişkenlere (environment secrets) ya da gitignore'daki .env'ye girer.
#
# Elle çalıştırma:  CLAUDE_CODE_REMOTE=true ./.claude/hooks/session-start.sh
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT"

PIPER_DIR="$HOME/.piper/models"
PIPER_VOICE="tr_TR-dfki-medium"
CA_BUNDLE="/root/.ccr/ca-bundle.crt"

# Kurulum günlükleri stderr'e gider; stdout oturum bağlamına eklenir.
log() { echo "[openmontage-setup] $*" >&2; }

# Node, HTTPS_PROXY'yi kendiliğinden kullanmaz; Remotion/HyperFrames
# indirmeleri bu iki değişken olmadan DNS hatasıyla düşer.
if [ -n "${HTTPS_PROXY:-}" ]; then
  export NODE_USE_ENV_PROXY=1
  [ -f "$CA_BUNDLE" ] && export NODE_EXTRA_CA_CERTS="$CA_BUNDLE"
fi

# 1) Python ortamı (make install, venv'i yoksa oluşturur).
if [ ! -x .venv/bin/python ] || ! .venv/bin/python -c "import yaml, pydantic, fastapi, pytest" 2>/dev/null; then
  log "Python bağımlılıkları kuruluyor (requirements-dev.txt, requirements.txt'yi de içerir)..."
  make install-dev >&2
fi
if ! .venv/bin/python -c "import piper" 2>/dev/null; then
  log "piper-tts kuruluyor..."
  .venv/bin/python -m pip install --quiet piper-tts >&2 || log "UYARI: piper-tts kurulamadı"
fi

# 2) Remotion npm paketleri.
if [ ! -d remotion-composer/node_modules ]; then
  log "remotion-composer npm paketleri kuruluyor..."
  (cd remotion-composer && npm install --no-audit --no-fund >&2)
fi

# 3) .env (yalnızca .env.example'daki boş şablon; gerçek anahtar yok).
if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
fi

# 4) Piper Türkçe ses modeli.
if [ ! -f "$PIPER_DIR/$PIPER_VOICE.onnx" ]; then
  log "Piper Türkçe ses modeli indiriliyor ($PIPER_VOICE)..."
  mkdir -p "$PIPER_DIR"
  .venv/bin/python -m piper.download_voices --data-dir "$PIPER_DIR" "$PIPER_VOICE" >&2 \
    || log "UYARI: ses modeli indirilemedi (huggingface.co ağ politikasında açık mı?)"
fi

# 5) Remotion Chrome Headless Shell.
if [ ! -d remotion-composer/node_modules/.remotion/chrome-headless-shell ]; then
  log "Remotion headless tarayıcısı indiriliyor..."
  (cd remotion-composer && npx remotion browser ensure >&2) \
    || log "UYARI: Remotion tarayıcısı indirilemedi (remotion.media ağ politikasında açık mı?)"
fi

# 6) Ortam değişkenlerini oturuma kalıcı yaz.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export VIRTUAL_ENV=\"$ROOT/.venv\""
    echo "export PATH=\"$ROOT/.venv/bin:\$PATH\""
    echo "export OPENMONTAGE_PIPER_TR_MODEL=\"$PIPER_DIR/$PIPER_VOICE.onnx\""
    if [ -n "${NODE_USE_ENV_PROXY:-}" ]; then
      echo "export NODE_USE_ENV_PROXY=1"
    fi
    if [ -n "${NODE_EXTRA_CA_CERTS:-}" ]; then
      echo "export NODE_EXTRA_CA_CERTS=\"$NODE_EXTRA_CA_CERTS\""
    fi
  } >> "$CLAUDE_ENV_FILE"
fi

log "Kurulum tamam."
