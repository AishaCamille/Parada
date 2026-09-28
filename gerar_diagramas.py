"""Gera diagramas SVG independentes de bibliotecas externas."""
from pathlib import Path
from html import escape

OUT = Path(__file__).resolve().parent / "diagramas"
OUT.mkdir(exist_ok=True)


class Canvas:
    def __init__(self, width, height, title, subtitle):
        self.width, self.height = width, height
        self.items = []
        self.text(54, 63, title, 29, "#143a32", 800)
        self.text(54, 91, subtitle, 14, "#6d817a")

    def text(self, x, y, value, size=14, color="#263d37", weight=500, anchor="start"):
        self.items.append(f'<text x="{x}" y="{y}" fill="{color}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{escape(value)}</text>')

    def line(self, x1, y1, x2, y2, arrow=False, dashed=False):
        marker = ' marker-end="url(#arrow)"' if arrow else ""
        dash = ' stroke-dasharray="6 5"' if dashed else ""
        self.items.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#7aa69a" stroke-width="2"{marker}{dash}/>')

    def path(self, d, arrow=False):
        marker = ' marker-end="url(#arrow)"' if arrow else ""
        self.items.append(f'<path d="{d}" fill="none" stroke="#7aa69a" stroke-width="2"{marker}/>')

    def box(self, x, y, w, h, title, lines=(), kind="entity"):
        colors = {"actor": ("#e8f5ed", "#087f63"), "boundary": ("#eaf2fb", "#2f6399"),
                  "control": ("#fff2e8", "#a75620"), "entity": ("#f2f8f5", "#2e715c")}
        bg, stroke = colors[kind]
        self.items.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="13" fill="{bg}" stroke="{stroke}" stroke-width="1.5"/>')
        self.text(x+16, y+29, title, 16, stroke, 700)
        for i, line in enumerate(lines):
            self.text(x+16, y+53+i*20, line, 13, "#50655d")

    def oval(self, x, y, w, h, label):
        self.items.append(f'<ellipse cx="{x+w/2}" cy="{y+h/2}" rx="{w/2}" ry="{h/2}" fill="#f2f8f5" stroke="#288a6c" stroke-width="1.6"/>')
        self.text(x+w/2, y+h/2+5, label, 14, "#17493b", 600, "middle")

    def save(self, filename):
        header=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}" role="img" aria-label="{escape(filename)}">
<defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="8" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 z" fill="#7aa69a"/></marker></defs>
<rect width="100%" height="100%" fill="#ffffff"/>
<rect x="25" y="25" width="{self.width-50}" height="{self.height-50}" rx="20" fill="#ffffff" stroke="#e2eae5" stroke-width="2"/>
'''
        (OUT / filename).write_text(header+"\n".join(self.items)+"\n</svg>\n", encoding="utf-8")


def use_cases():
    c=Canvas(1250,790,"Casos de uso","Atores e funções do MVP Parada")
    actors=[("Motorista",145), ("Gerente",385), ("Administrador",625)]
    for name,y in actors:
        c.box(65,y,190,74,name,kind="actor")
    cases=[("Autenticar",305,140),("Registrar horários",305,235),("Consultar histórico",305,330),
           ("Consultar dashboard",305,425),("Exportar CSV",305,520),("Cadastrar motoristas e pontos",730,170),
           ("Montar roteiros",730,270),("Gerenciar usuários",730,370),("Configurar parâmetros",730,470),
           ("Consultar auditoria",730,570)]
    for label,x,y in cases:c.oval(x,y,390 if x==730 else 320,58,label)
    # Relações agrupadas para conservar a legibilidade visual.
    c.path("M255 180 L295 180 L295 169 L305 169")
    c.path("M255 181 L277 181 L277 264 L305 264")
    c.path("M255 181 L269 181 L269 359 L305 359")
    c.path("M255 182 L261 182 L261 454 L305 454")
    c.path("M255 183 L265 183 L265 549 L305 549")
    c.path("M255 422 L284 422 L284 169 L305 169")
    c.path("M255 422 L290 422 L290 264 L305 264")
    c.path("M255 422 L298 422 L298 359 L305 359")
    c.line(255,423,305,454)
    c.line(255,424,305,549)
    c.path("M255 422 L690 422 L690 199 L730 199")
    c.path("M255 425 L700 425 L700 299 L730 299")
    c.path("M255 662 L710 662 L710 399 L730 399")
    c.path("M255 665 L720 665 L720 499 L730 499")
    c.path("M255 668 L730 668 L730 599")
    c.text(65,754,"Gerente também consulta relatórios; administrador também executa os casos do gerente.",13,"#6d817a")
    c.save("casos-de-uso.svg")


def robustness_routes():
    c=Canvas(1250,630,"Robustez · montagem e coleta","Ator → interface → controle → entidades persistidas")
    c.box(55,260,195,85,"Gerente / Motorista",["gestão / coleta autorizada"],"actor")
    c.box(320,145,220,84,"Tela de roteiros",["data, motorista, pontos"],"boundary")
    c.box(320,385,220,84,"Tela de horários",["chegada e saída"],"boundary")
    c.box(615,145,230,84,"Controle de roteiro",["valida ordem e vínculos"],"control")
    c.box(615,385,230,84,"Controle de horários",["valida e calcula"],"control")
    c.box(950,125,230,77,"Roteiro",["data, motorista, distância"])
    c.box(950,225,230,77,"Ponto",["endereço, coordenadas"])
    c.box(950,325,230,77,"Parada",["ordem, chegada, saída"])
    c.box(950,425,230,77,"Auditoria",["alterações e ator"])
    for a,b,d,e in [(250,299,320,187),(250,311,320,427),(540,187,615,187),(540,427,615,427),
                     (845,187,950,164),(845,187,950,264),(845,187,950,364),(845,427,950,364),(845,427,950,464)]:c.line(a,b,d,e,True)
    c.save("robustez-roteiro.svg")


def robustness_dashboard():
    c=Canvas(1250,620,"Robustez · consultas e parâmetros","Dados agregados por período e configuração editável")
    c.box(55,170,190,75,"Usuário",["consulta período"],"actor")
    c.box(55,410,190,75,"Administrador",["altera parâmetros"],"actor")
    c.box(310,170,230,80,"Dashboard / histórico",["filtro e gráficos"],"boundary")
    c.box(310,410,230,80,"Tela de parâmetros",["valores editáveis"],"boundary")
    c.box(610,170,230,80,"Controle de consulta",["agrega dia, mês, ponto"],"control")
    c.box(610,410,230,80,"Controle de parâmetros",["valida e registra"],"control")
    c.box(950,120,230,75,"Roteiro",["data e distância"])
    c.box(950,225,230,75,"Parada + ponto",["horários e endereço"])
    c.box(950,330,230,75,"Parâmetros",["custo e jornada"])
    c.box(950,435,230,75,"Auditoria",["alteração registrada"])
    for a,b,d,e in [(245,207,310,210),(245,448,310,450),(540,210,610,210),(540,450,610,450),
                     (840,210,950,157),(840,210,950,262),(840,210,950,367),(840,450,950,367),(840,450,950,472)]:c.line(a,b,d,e,True)
    c.save("robustez-consultas.svg")


def classes():
    c=Canvas(1330,950,"Classes conceituais","Entidades, atributos principais e relações do domínio")
    # As linhas são desenhadas antes das classes para ficarem atrás dos cartões.
    c.line(300,215,445,215,True);c.text(348,202,"1 → 0..*",12)
    c.line(730,215,865,215,True);c.text(765,202,"1 → 0..*",12)
    c.line(1080,320,1080,430,True);c.text(1093,390,"1 ponto / parada",12)
    c.line(185,485,185,330,True);c.text(196,375,"representa",12)
    c.line(185,585,185,680,True)
    c.line(295,540,445,745,True);c.text(335,650,"registra",12)
    c.line(560,680,560,330,True);c.text(573,520,"calcula",12)
    c.path("M310 520 L395 520 L395 880 L815 880 L815 755 L865 755",True)
    c.text(540,897,"produz auditoria",12)
    c.path("M70 755 L45 755 L45 215 L70 215",True)
    c.text(51,633,"equipe",12)
    c.box(70,130,240,200,"Motorista",["id, nome, telefone", "documento, veículo", "km por litro", "gerente responsável"])
    c.box(445,130,285,200,"Roteiro",["id, data", "motorista responsável", "distância total", "tempo total parado*", "custo estimado*"])
    c.box(865,130,340,190,"Parada",["id, ordem no roteiro", "chegada, saída", "tempo parado*"])
    c.box(865,430,340,150,"Ponto",["id, endereço", "latitude, longitude", "gerente proprietário (opcional)"])
    c.box(70,430,240,155,"Usuário",["id, nome, e-mail", "perfil, senha hash"])
    c.box(70,680,240,155,"Gerente",["id, nome, telefone", "e-mail, equipe"])
    c.box(445,680,285,170,"Parâmetro",["combustível, consumo padrão", "custo extra por km", "jornada e regra de contagem"])
    c.box(865,680,340,170,"Auditoria",["instante, ator", "entidade, ação", "antes e depois"])
    c.text(70,906,"* Atributos calculados a partir de horários, distância e parâmetros persistidos.",13,"#6d817a")
    c.save("classes-conceituais.svg")


if __name__ == "__main__":
    use_cases()
    robustness_routes()
    robustness_dashboard()
    classes()
    print(f"Diagramas salvos em {OUT}")
