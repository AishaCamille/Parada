# Parada

MVP web para monitorar tempo parado em roteiros de entrega, conforme a Especificação de Requisitos — Trabalho2. O sistema usa **Python 3.10+ e SQLite**, sem dependências externas para executar.

## Executar

No Windows, dê dois cliques em `iniciar.bat`, ou execute `python server.py` no terminal. No Linux/macOS:

```sh
cd Parada
./carregar_linux.sh --normal
# Ou: python3 server.py
```

Abra **http://127.0.0.1:8000**. Configure o administrador inicial para administrar parâmetros e acessos. Depois use **Criar conta** para cadastrar um gerente e os motoristas da equipe. Se já houver gerente cadastrado, a configuração inicial continua disponível enquanto não existir administrador.

O banco normal é criado em `data/parada.sqlite3`. `Ctrl+C` encerra o servidor. A variável `PORT` permite escolher outra porta; `PARADA_DB` permite selecionar outro arquivo de banco.

## Carregar tudo no Linux

```sh
cd Parada
./carregar_linux.sh
```

O script verifica Python e SQLite, carrega os roteiros fictícios A/B/C, inicia o servidor e abre o painel no navegador. Se a porta 8000 estiver ocupada, tenta outra até 8010 e mostra o endereço escolhido. Funciona mesmo se for chamado de outra pasta. Não há bibliotecas externas a instalar para usar o MVP.

| Opção | Resultado |
| --- | --- |
| `--normal` | Usa o banco normal, sem inserir dados fictícios. |
| `--porta 8001` | Escolhe uma porta específica. |
| `--sem-navegador` | Inicia o servidor sem abrir o navegador. |
| `--testar` | Executa os testes e encerra. |
| `--help` | Mostra as opções disponíveis. |

`./iniciar.sh` é um atalho para o mesmo script. Mantenha o terminal aberto; `Ctrl+C` encerra o servidor e preserva os dados. Se não houver Python, o script indica o comando de instalação para Fedora ou Ubuntu/Debian.

## Demonstração pronta

```sh
python3 demo.py --serve
```

No Windows: `python demo.py --serve`. Abra o mesmo endereço; não execute os dois servidores simultaneamente na mesma porta. Use `--port 8001` se precisar de outra porta.

| Perfil | E-mail | Senha fictícia |
| --- | --- | --- |
| Administrador | admin@parada.test | Parada-demo-123 |
| Gerente | gerente@parada.test | Parada-demo-123 |
| Motorista A | motoristaa@parada.test | Parada-demo-123 |
| Motorista B/C | motoristab@parada.test / motoristac@parada.test | Parada-demo-123 |

A demonstração usa **banco separado**, `data/demonstracao.sqlite3`, preservado entre execuções. Inclui os roteiros A/B/C do PDF, com **75, 41 e 45 minutos**, total **161 minutos**; as partidas contribuem com zero. Os registros são criados na data da primeira execução. Se não estiverem no mês atual, ajuste o filtro. Com os parâmetros iniciais, o custo total é R$ 37,50 para as distâncias fictícias de 30, 20 e 25 km.

## Usar

1. Gerente cria conta com nome, telefone, e-mail e senha e copia o código da equipe.
2. Motorista cria sua conta com nome, telefone, documento, veículo, e-mail, senha e código recebido. Consumo é opcional. Ele entra em Meus roteiros, inicialmente filtrado para hoje.
3. Gerente ou administrador cadastra e edita motoristas e pontos em Equipe e pontos. Administrador também cadastra gerentes e cria acessos ligados a profissionais existentes.
4. Em Roteiros, selecione motorista, data e distância. Adicione os pontos na ordem do trajeto, começando pela partida.
5. Abra o roteiro e registre chegada e saída. Agora preenche o próximo horário disponível com a hora local do dispositivo. Correções ficam na auditoria.
6. Consulte Visão geral e Histórico para períodos de até 12 meses de calendário e exporte CSV. Os três gráficos mostram dia, mês e endereços no período; o gráfico de endereços exibe os sete maiores tempos. Histórico e CSV incluem todas as paradas depois da partida.
7. Administrador altera combustível, consumo padrão, adicional por km, jornada e posição inicial em Parâmetros. Consumo específico do veículo é editado no cadastro do motorista.

O tempo de cada ponto é `saída − chegada`. A partida sempre vale zero. Custo estimado = `distância × (combustível ÷ km/l + adicional/km)`. Jornada padrão: 8 horas. Indicadores são recalculados com os parâmetros atuais. No CSV, custo e distância do roteiro se repetem por parada: conte esses valores **uma vez por roteiro**.

Gerentes acessam sua equipe; motoristas acessam seus roteiros. Pontos de gerentes pertencem à equipe. Pontos do administrador e pontos legados sem proprietário são compartilhados para consulta, com edição restrita ao administrador. O aviso de privacidade está disponível antes e depois do login. Use dados fictícios na avaliação; os limites do protótipo e as pendências organizacionais para uma implantação real estão documentados no projeto preliminar.

## Entrega no GitHub

A entrega será pelo repositório [AishaCamille/Parada](https://github.com/AishaCamille/Parada), com código, testes, instruções, documentos e campanha. Os arquivos ZIP e os bancos locais ficam fora do versionamento.

Para obter e executar o projeto no Linux:

```sh
git clone https://github.com/AishaCamille/Parada.git
cd Parada
./carregar_linux.sh
```

Documentos de apoio incluídos no repositório:

- [Projeto preliminar em PDF](entrega/Projeto-Preliminar-Parada.pdf), com casos de uso, robustez, classes e rastreabilidade RF01–RF12, RN01–RN07 e RNF01–RNF06.
- [Fonte editável do projeto](PROJETO_PRELIMINAR.md) e [versão HTML imprimível](entrega/Projeto-Preliminar-Parada.html).
- [Todos os diagramas em PDF](diagramas/diagramas-completos.pdf), além dos SVGs e PDFs individuais na pasta `diagramas`.
- [Campanha](campanha/PLANO.md): cartaz em SVG, PNG e PDF, com mensagem, público, canais e legenda.
- [Roteiro da apresentação](APRESENTACAO.md) e [relatório de validação](VALIDACAO.md).

**Antes de enviar, preencha os nomes da dupla ou trio no documento.** O campo está marcado porque os integrantes não foram informados.

## Testar

Dentro da pasta `Parada`:

```sh
python3 -m unittest -v
node --check app.js
```

No Windows use `python` no lugar de `python3`. Os testes usam bancos temporários e incluem os exemplos do PDF, cálculos, controle de acesso, auditoria, consumo editável, CSV, limites de período e desempenho anual.

A verificação opcional em navegador real está em `test_interface.cjs`. Ela requer Node.js, Playwright e um navegador Chromium. Use uma instalação temporária da ferramenta, sem alterar as dependências do MVP:

```sh
npm install --prefix /tmp/parada-browser-tools playwright
NODE_PATH=/tmp/parada-browser-tools/node_modules node test_interface.cjs
```

Ajuste `PARADA_BROWSER` para o executável do seu navegador e `PARADA_PYTHON` para o Python, se necessário. O padrão nesta máquina é Brave e `python3`. O teste gera capturas desktop/móvel em `entrega` e usa um banco fictício temporário.

Para atualizar os diagramas SVG: `python3 gerar_diagramas.py`. Para atualizar o HTML do documento, a ferramenta opcional `gerar_documentos.py` usa o pacote `markdown`; instale-o em um ambiente Python de desenvolvimento. Abra o HTML no navegador e use Imprimir → Salvar como PDF, com A4 e gráficos de fundo. Os PDFs já estão incluídos para avaliação.
