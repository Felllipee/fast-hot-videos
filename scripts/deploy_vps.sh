#!/bin/bash
set -e

echo "🚀 Iniciando Configuração do Servidor (Fast Hot Videos)..."

# 1. Update System
echo "🔄 Atualizando sistema..."
sudo apt update && sudo apt upgrade -y

# 2. Install Dependencies
echo "📦 Instalando Python, Git e FFmpeg..."
sudo apt install -y python3-pip python3-venv git ffmpeg tmux htop unzip

# 3. Clone Repository
echo "📂 Baixando Código..."
if [ -d "fast-hot-videos" ]; then
    echo "⚠️ Pasta já existe. Atualizando..."
    cd fast-hot-videos
    git pull
else
    git clone https://github.com/felllipee/fast-hot-videos.git
    cd fast-hot-videos
fi

# 4. Setup Python Environment
echo "🐍 Configurando Python..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Create Systemd Service (Auto-Start)
echo "⚙️ Configurando Inicialização Automática..."
SERVICE_FILE="/etc/systemd/system/fasthot.service"
CURRENT_DIR=$(pwd)
USER_NAME=$(whoami)

sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=Fast Hot Videos Bot & Server
After=network.target

[Service]
User=$USER_NAME
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload
sudo systemctl enable fasthot

echo "✅ Instalação Concluída!"
echo "⚠️  IMPORTANTE:"
echo "1. Crie o arquivo .env:  nano .env"
echo "2. Cole suas configurações nele."
echo "3. Inicie o bot:        sudo systemctl start fasthot"
echo "4. Veja os logs:        sudo journalctl -u fasthot -f"
