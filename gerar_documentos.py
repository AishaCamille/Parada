"""Gera HTML imprimível a partir do documento. Ferramenta opcional: pip install markdown."""
import sys
from pathlib import Path
import markdown
root=Path(__file__).resolve().parent
css='''@page{size:A4;margin:20mm 17mm}*{box-sizing:border-box}body{font:11pt/1.55 Arial,sans-serif;color:#243d35;margin:0}h1{font-size:30pt;color:#087c67;line-height:1.15;margin:0 0 20px}h2{font-size:18pt;color:#087c67;border-bottom:1px solid #dbe6e0;padding-bottom:5px;margin-top:26px}h3{font-size:13pt;color:#143a32;margin-top:20px}h1,h2,h3{break-after:avoid}p,li{orphans:3;widows:3}table{border-collapse:collapse;width:100%;font-size:9pt;margin:15px 0}td,th{border:1px solid #dbe6e0;padding:7px 9px;vertical-align:top}th{background:#eaf6ef;text-align:left}tr{break-inside:avoid}img{display:block;max-width:100%;max-height:240mm;margin:15px auto;break-inside:avoid}a{color:#087c67}pre{white-space:pre-wrap;background:#eff5f2;padding:12px}code{font-size:9.5pt}blockquote{border-left:4px solid #36b996;padding-left:16px;color:#567367}footer{font-size:9pt;color:#6b8378;margin-top:25px}.diagram-page{break-before:page;break-after:page;margin:0}.diagram-page img{max-height:225mm}.campaign-page{break-before:page}'''
s=(root/'PROJETO_PRELIMINAR.md').read_text()
body=markdown.markdown(s,extensions=['tables','fenced_code'])
body=body.replace('src="diagramas/','src="../diagramas/').replace('src="campanha/','src="../campanha/')
import re
body=re.sub(r'<p>(<img[^>]+src="../diagramas/[^>]+>)</p>',r'<div class="diagram-page">\1</div>',body)
body=body.replace('<h2>6. Classes conceituais e persistência</h2>\n<div class="diagram-page">', '<div class="diagram-page"><h2>6. Classes conceituais e persistência</h2>')
body=body.replace('<p><img alt="Cartaz de divulgação"', '<p class="campaign-page"><img alt="Cartaz de divulgação"')
html='<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Projeto preliminar — Parada</title><style>'+css+'</style></head><body>'+body+'</body></html>'
(root/'entrega'/'Projeto-Preliminar-Parada.html').write_text(html)
(root/'campanha'/'cartaz.html').write_text('''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Campanha Parada</title><style>@page{size:1080px 1350px;margin:0}body{margin:0}img{display:block;width:1080px;height:1350px}</style></head><body><img src="cartaz.svg" alt="Cada minuto parado conta — Parada"></body></html>''')
