#!/usr/bin/env bash
# ==============================================================================
# gemini-peer-review: Script de Instalação e Sincronização via uv
# LaBiOmicS / UMC - Prof. Dr. Fabiano Bezerra Menegidio
# ==============================================================================
set -e

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "==> [1/3] Verificando ambiente e instalador uv..."

if ! command -v uv &> /dev/null; then
    echo "Aviso: 'uv' não encontrado no PATH. Instalando via script oficial Astral..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

echo "✔ uv detectado: $(uv --version)"

echo "==> [2/3] Sincronizando dependências Python via uv (PEP 621)..."
cd "$PLUGIN_DIR"
uv sync

echo "==> [3/4] Instalando e ativando no Antigravity CLI (Gemini)..."
if command -v agy &> /dev/null; then
    agy plugin install "$PLUGIN_DIR"
    agy plugin enable academic-peer-review || true
    echo "✔ Plugin validado no Antigravity CLI:"
    agy plugin validate "$PLUGIN_DIR" --strict
else
    echo "Aviso: 'agy' CLI não encontrado no PATH. Copiando para diretórios padrão de plugins..."
    mkdir -p "$HOME/.gemini/antigravity-cli/plugins" "$HOME/.gemini/extensions"
    cp -r "$PLUGIN_DIR" "$HOME/.gemini/antigravity-cli/plugins/academic-peer-review"
    cp -r "$PLUGIN_DIR" "$HOME/.gemini/extensions/academic-peer-review"
fi

echo "==> [4/4] Verificando integração com Claude Code..."
if command -v claude &> /dev/null; then
    mkdir -p "$HOME/.claude/plugins"
    cp -r "$PLUGIN_DIR" "$HOME/.claude/plugins/academic-peer-review"
    echo "✔ Plugin validado no Claude Code:"
    claude plugin validate "$PLUGIN_DIR"
fi

echo ""
echo "================================================================================"
echo "✔ Instalação concluída com sucesso para Antigravity (Gemini) e Claude Code!"
echo "  - Plugin registrado: academic-peer-review"
echo "  - Ambiente virtual uv: $PLUGIN_DIR/.venv"
echo "  - Para testar: uv run skills/paper-review/scripts/stat_and_integrity_audit.py --help"
echo "================================================================================"
