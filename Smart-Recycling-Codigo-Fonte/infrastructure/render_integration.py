from pathlib import Path
import markdown
root=Path(__file__).resolve().parents[1]
page=root/'app/static/integration.html'
s=page.read_text(encoding='utf-8');prefix,rest=s.split('<article class="panel integration-guide">',1);_,suffix=rest.split('</article>',1)
body=markdown.markdown((root/'docs/INTEGRACAO.md').read_text(encoding='utf-8').split('\n',1)[1],extensions=['fenced_code','tables'])
body=body.replace('<table>','<div class="guide-table-wrap"><table class="guide-table">').replace('</table>','</table></div>')
page.write_text(prefix+'<article class="panel integration-guide">'+body+'</article>'+suffix,encoding='utf-8')
