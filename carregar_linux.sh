#!/usr/bin/env sh
# Carrega o Parada no Linux. Usa somente Python e a biblioteca padrão.
set -eu

PARADA_SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd -- "$PARADA_SCRIPT_DIR"
PARADA_PYTHON_BIN=${PARADA_PYTHON:-python3}

if ! command -v "$PARADA_PYTHON_BIN" >/dev/null 2>&1; then
    printf '%s\n' 'Python 3.10+ não foi encontrado.'
    printf '%s\n' 'Fedora: sudo dnf install python3'
    printf '%s\n' 'Ubuntu/Debian: sudo apt install python3'
    printf '%s\n' 'Depois execute este script novamente.'
    exit 1
fi

exec "$PARADA_PYTHON_BIN" - "$@" <<'PY'
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import webbrowser

if sys.version_info < (3, 10):
    sys.exit('O Parada precisa de Python 3.10 ou superior.')
try:
    import sqlite3
except ImportError:
    sys.exit('Este Python não tem SQLite. Instale o pacote Python da sua distribuição.')

parser = argparse.ArgumentParser(
    prog='carregar_linux.sh',
    description='Carrega o Parada com os roteiros A/B/C e abre o painel no Linux.',
    epilog='Sem argumentos: demonstração pronta. Ctrl+C encerra o servidor. Nenhum banco existente é apagado.')
parser.add_argument('--normal', action='store_true', help='Usa o banco normal, sem inserir dados fictícios')
parser.add_argument('--sem-navegador', action='store_true', help='Não abre o navegador automaticamente')
parser.add_argument('--porta', type=int, help='Porta do servidor; padrão 8000, com alternativa até 8010 se ocupada')
parser.add_argument('--testar', action='store_true', help='Executa os testes e encerra, sem iniciar o painel')
args = parser.parse_args()

root = Path.cwd()
required = ('server.py', 'demo.py', 'index.html', 'app.js', 'style.css', 'privacidade.html')
missing = [name for name in required if not (root / name).is_file()]
if missing:
    parser.error('Arquivos ausentes: ' + ', '.join(missing) + '. Extraia o projeto inteiro antes de executar.')

if args.testar:
    result = subprocess.run([sys.executable, '-m', 'unittest', '-v'], cwd=root)
    if result.returncode:
        sys.exit(result.returncode)
    node = shutil.which('node')
    if node:
        for source in ('app.js', 'test_interface.cjs'):
            result = subprocess.run([node, '--check', source], cwd=root)
            if result.returncode:
                sys.exit(result.returncode)
    print('Testes aprovados.' + ('' if node else ' Node.js ausente; checagem opcional de JavaScript não executada.'))
    sys.exit(0)

import server
import demo

explicit_port = args.porta is not None or 'PORT' in os.environ
try:
    port = args.porta if args.porta is not None else int(os.environ.get('PORT', '8000'))
except ValueError:
    parser.error('A variável PORT precisa ser um número inteiro.')
if not 0 <= port <= 65535:
    parser.error('A porta precisa estar entre 0 e 65535.')

if args.normal:
    server.init_db()
    mode = 'Banco normal'
else:
    created = demo.create_demo()
    server.init_db()
    mode = 'Demonstração criada' if created else 'Demonstração existente preservada'

httpd = None
for candidate in ([port] if explicit_port else range(port, port + 11)):
    try:
        httpd = server.ThreadingHTTPServer(('127.0.0.1', candidate), server.Handler)
        break
    except OSError as error:
        if error.errno != 98:  # EADDRINUSE no Linux
            sys.exit(f'Não foi possível iniciar o servidor: {error}')
if httpd is None:
    sys.exit('Porta ocupada. Execute novamente com --porta 8001 (ou outra porta livre).')

url = f'http://127.0.0.1:{httpd.server_port}'
print('\nPARADA — inteligência em cada rota', flush=True)
print(f'{mode}: {server.DB_PATH}', flush=True)
print(f'Abra: {url}', flush=True)
if not args.normal:
    print('Contas: admin@parada.test | gerente@parada.test | motoristaa@parada.test', flush=True)
    print(f'Senha fictícia: {demo.PASSWORD}', flush=True)
    print('Roteiros A/B/C: 75, 41 e 45 minutos (161 minutos no total).', flush=True)
    print('Se a demonstração foi criada em outro mês, ajuste o filtro à data dos roteiros.', flush=True)
else:
    print('Configure o administrador inicial na tela de acesso, se ainda não houver um.', flush=True)
print('Documento: entrega/Projeto-Preliminar-Parada.pdf', flush=True)
print('Campanha: campanha/cartaz.pdf | Apresentação: APRESENTACAO.md', flush=True)
print('Mantenha este terminal aberto. Ctrl+C encerra o servidor.\n', flush=True)

if not args.sem_navegador and (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
    def open_panel():
        if not webbrowser.open(url):
            print(f'Abra manualmente no navegador: {url}', flush=True)
    timer = threading.Timer(0.5, open_panel)
    timer.daemon = True
    timer.start()
try:
    httpd.serve_forever()
except KeyboardInterrupt:
    print('\nParada encerrado. Os dados foram preservados.', flush=True)
finally:
    httpd.server_close()
PY
