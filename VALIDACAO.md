# Validação — Parada

Execução local em 28/09/2026, com dados fictícios e bancos temporários. Ambiente: Linux, Python 3.14.7, Node.js 24 e navegador Brave/Chromium.

## Resultado dos testes

`python3 -m unittest -v`: **5 testes aprovados**, sem falhas, em 1,667 segundo na execução final.

| Teste | Evidência |
| --- | --- |
| Fluxo principal e acesso | Cadastro, autenticação, montagem do roteiro, partida zero, tempo/custo/jornada, correção de ponto, parâmetros, CSV, auditoria e consulta anual. |
| Limites do período e consultas em lote | Aceita ano comum e bissexto; rejeita período invertido e aniversário de 12 meses; agregação usa três consultas de dados. |
| Autocadastro e isolamento de equipes | Código de convite, rollback de cadastro duplicado, roteiros por equipe, bloqueios por perfil, configuração inicial após gerente e logout invalidando sessão. |
| Exemplos do enunciado e preservação da demonstração | A = 75 min, B = 41 min, C = 45 min; total 161 min; partida zero mesmo com horários; banco existente preservado; regra de contagem editável. |
| Edição do veículo e isolamento de pontos | Consumo recalcula custo, valor inválido rejeitado, equipe externa não altera motorista/ponto nem inclui ponto privado em roteiro; validação de identificadores e campos obrigatórios. |

`node --check app.js`, `node --check test_interface.cjs` e compilação dos módulos Python: aprovados. `git diff --check`: aprovado.

## Navegador real

`test_interface.cjs`: aprovado em **desktop 1440 × 1000** e **celular 390 × 844**, locale pt-BR, sem exceções JavaScript.

Foram verificados login/logout, cadastro e edição de motorista, consumo, campos de vínculo conforme perfil, edição de parâmetros e recálculo no painel, histórico, download CSV, perfil de gerente, isolamento do motorista, gravação e preservação de segundos, aviso de privacidade e ausência de transbordamento horizontal na página móvel. Tabelas utilizam rolagem interna.

Capturas em `entrega/painel-desktop.png`, `entrega/painel-celular.png` e `entrega/roteiro-celular.png`. Os testes usam banco separado e não alteram dados do usuário.

## Inicialização no Linux

`carregar_linux.sh` e o atalho `iniciar.sh`: sintaxe shell aprovada e teste de inicialização HTTP aprovado. Foi verificada execução em pasta com espaços e a partir de outro diretório, carga dos três roteiros com 161 minutos, preservação do banco no reinício, banco normal separado com `--normal`, seleção de porta com `--porta 0` e encerramento por Ctrl+C. O teste usou arquivos e bancos temporários e não abriu navegador.

## Desempenho anual — RNF03

Período: 01/01/2025–31/12/2025. Banco sintético: 10 motoristas, **3.650 roteiros e 14.600 pontos**. Consulta HTTP autenticada do dashboard, incluindo leitura completa da resposta de 6.972.165 bytes: **0,1696 segundo**, HTTP 200. Limite da especificação: inferior a 3 segundos.

A medição é uma amostra neste equipamento, com servidor e navegador cliente na mesma máquina; não é garantia para outros volumes ou ambientes. A consulta carrega parâmetros, paradas e roteiros em lote. Reproduza com `python3 benchmark_dashboard.py`; o script usa dados fictícios em banco temporário.

## Documentos e entrega

Projeto preliminar: PDF com **12 páginas**, incluindo os quatro diagramas, regras, RF01–RF12, RN01–RN07, RNF01–RNF06 e casos de uso UC01–UC08. Cada diagrama também possui PDF individual de uma página; o PDF conjunto tem quatro páginas. Campanha em SVG, PNG e PDF, com plano e legenda. Há um roteiro de apresentação e demonstração executável.

Os PDFs foram conferidos por extração de texto, contagem de páginas e presença das seções. Capturas do sistema e da campanha foram inspecionadas visualmente. A entrega pelo GitHub inclui o código e os documentos; o `.gitignore` exclui bancos locais, dependências temporárias, caches e arquivos ZIP.

## Limites explicitados

O MVP é destinado à avaliação local. O aviso de privacidade e a especificação descrevem as medidas técnicas e as pendências organizacionais de uma implantação real, especialmente responsável, contato, retenção e atendimento aos titulares. Não se declara conformidade jurídica completa com a LGPD. A identificação da dupla ou trio precisa ser preenchida antes da entrega.
