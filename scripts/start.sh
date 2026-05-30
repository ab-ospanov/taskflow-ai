#!/bin/bash
set -e
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Создан .env — заполните переменные и запустите снова."
  exit 1
fi

# Загружаем .env явно, перезаписывая shell-переменные
set -a
source .env
set +a

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

python -m bot.main &
BOT_PID=$!

echo ""
echo "✅ TaskFlow AI запущен!"
echo "   Дашборд:  http://localhost:8000"
echo "   API docs: http://localhost:8000/docs"
echo ""

trap "kill $BACKEND_PID $BOT_PID 2>/dev/null" EXIT
wait
