# Parada

MVP web para monitorar o tempo parado em roteiros de entrega. O sistema usa Python 3.10+ e SQLite, sem instalação de dependências.

## Executar

No Windows, dê dois cliques em [iniciar.bat](iniciar.bat). Ele inicia o servidor e abre o painel no navegador. Mantenha a janela aberta enquanto usa o sistema; `Ctrl+C` encerra o servidor.

Também é possível iniciar pelo terminal:

```powershell
python server.py
```

Abra **http://127.0.0.1:8000**. Na tela inicial, use **Criar conta** e escolha **Gerente** ou **Motorista**. Em um banco vazio, também é possível configurar primeiro o administrador pelo botão específico. O banco é criado automaticamente em `data/parada.sqlite3`.

## Usar

1. Cadastre o **gerente** com nome, telefone, e-mail e senha. No painel, copie o **código da equipe**.
2. Antes de entrar, o motorista escolhe **Criar conta → Motorista** e informa nome, telefone, documento, veículo, e-mail, senha e o código recebido do gerente. O consumo é opcional. Ele entra diretamente em **Meus roteiros**, com filtro inicial para hoje.
3. O gerente cadastra endereços em **Equipe e pontos** e acompanha apenas seus motoristas.
4. Em **Roteiros**, crie um roteiro para um motorista e uma data. Adicione os pontos na ordem do trajeto, começando pela partida.
5. Registre chegada e saída em cada ponto. O botão **Agora** preenche o próximo horário disponível com a hora local do dispositivo.
6. Consulte **Visão geral** e **Histórico** para os recortes de até 12 meses. Exporte o período em CSV.
7. Em **Parâmetros**, o administrador altera combustível, consumo, custo adicional por km, jornada e posição a partir da qual a parada é contada.

O tempo de cada ponto é `saída - chegada`. A partida sempre vale zero. O custo estimado é `distância × (preço do combustível ÷ km/l do veículo + custo adicional por km)`. O percentual de jornada usa a jornada configurada; começa em 8 horas por dia.

Os perfis são **motorista**, **gerente** e **administrador**. Motoristas veem apenas seus roteiros e podem registrar seus horários. Gerentes convidam motoristas pelo código da equipe e cadastram roteiros e pontos. Administradores também gerenciam contas, gerentes, parâmetros e auditoria. Todo novo motorista precisa de um gerente. Cadastros antigos são preservados; códigos de equipe são gerados automaticamente para gerentes existentes ao iniciar o servidor.

## Testar

```powershell
python -m unittest -v
node --check app.js
```

Os testes usam banco temporário. O sistema opera em `127.0.0.1` para uso e avaliação local. Antes de publicar em rede, configure HTTPS, política de backup, recuperação de acesso e política de retenção e eliminação de dados pessoais. Não use dados pessoais reais em demonstrações.

O documento preliminar está em [PROJETO_PRELIMINAR.md](PROJETO_PRELIMINAR.md). Os quatro diagramas também estão reunidos em [diagramas-completos.pdf](diagramas/diagramas-completos.pdf). Há PDFs individuais e SVGs na pasta [diagramas](diagramas). Para regenerar os SVGs, execute `python gerar_diagramas.py`.
