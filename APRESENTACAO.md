# Roteiro de apresentação — Parada

Duração sugerida: 6–8 minutos. Use somente os dados fictícios da demonstração.

1. **Problema e proposta (40 s).** Explique o tempo invisível por endereço e apresente o nome Parada e a campanha. Abra `campanha/cartaz.pdf`.
2. **Iniciar (30 s).** Na pasta do projeto, execute `./carregar_linux.sh` no Linux (Windows: `python demo.py --serve`) e abra `http://127.0.0.1:8000`. Entre como `admin@parada.test` com senha `Parada-demo-123`. O banco de demonstração é separado e preservado entre execuções.
3. **Dashboard (1 min).** Se a demonstração foi criada em outro mês, ajuste o filtro à sua data. Mostre gráficos diário, mensal e por endereço no período. Os roteiros A/B/C totalizam 161 minutos e R$ 37,50 com os parâmetros iniciais.
4. **Coleta (1 min).** Abra Roteiros e o roteiro A. Mostre a partida com 20 minutos entre chegada e saída, mas contribuição zero; destinos somam 75 minutos. Altere um horário, confira o recálculo e restaure o original.
5. **Histórico e relatório (40 s).** Abra Histórico e exporte CSV. Identifique endereço, horários, tempo e custo do roteiro. Explique que indicadores do roteiro se repetem por parada no CSV.
6. **Cadastros e parâmetros (1 min).** Em Equipe e pontos, mostre coordenadas e edição do consumo. Em Parâmetros, altere combustível de R$ 6 para R$ 8 e confira custo recalculado; restaure R$ 6. A jornada inicial é 8 horas.
7. **Perfis e auditoria (1 min).** Mostre a auditoria das alterações. Saia e entre como `motoristaa@parada.test`, com a mesma senha. Motorista vê apenas seus roteiros e não possui acesso à administração. Os campos de coleta funcionam em tela de celular. O gerente de demonstração é `gerente@parada.test`.
8. **Projeto preliminar (40 s).** Abra `entrega/Projeto-Preliminar-Parada.pdf`. Apresente os casos de uso, robustez e classes conceituais. Explique a associação Parada, que guarda horários diferentes para cada visita a um ponto.

Antes de entregar, preencha os nomes da dupla ou trio no documento. A entrega será o link do repositório GitHub, contendo o código, os diagramas e os documentos. Os bancos locais e arquivos ZIP são ignorados pelo Git.
