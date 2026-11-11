import json, re
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops
import os, tempfile
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D=tempfile.mkdtemp()+'/'
res=[]
def check(name,cond): res.append((name,bool(cond))); print(('PASS ' if cond else 'FAIL ')+name)
def same(a,b):
    # Canvas area only (palette has fade transitions). Since v1.9 the nested tiles overlap at
    # the joins, and the browser anti-aliases those edges slightly differently for a flow built
    # step by step vs one rebuilt in one go — a few hundred sub-visible pixels out of ~850k.
    # Exact equality of structure is checked separately (DOM-identical); here we only require
    # that nothing visible moved.
    import numpy as np
    box=(261,53,1400,800)
    d=np.array(ImageChops.difference(Image.open(a).convert('RGB').crop(box),Image.open(b).convert('RGB').crop(box))).sum(2)
    return int((d>0).sum()) < 600 and int((d>150).sum()) == 0
def worldstate(pg):
    h=pg.evaluate("document.getElementById('world').innerHTML")
    return re.sub(r'(data-id|data-seq|data-left-linked|data-right-linked)="[^"]*"','',h).replace(' selected','')
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1400,'height':800}, accept_downloads=True)
    errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.on('dialog', lambda d: d.accept())
    pg.goto('file:///'+ROOT.replace(os.sep,'/').lstrip('/')+'/pattern-bench.html'); pg.wait_for_timeout(300)
    check('undo/redo disabled at start', pg.is_disabled('#undoBtn') and pg.is_disabled('#redoBtn'))
    # build with mixed append/prepend
    for t in ['consume-to-process','process-to-api','process-to-publish','api-to-process']:
        pg.evaluate(f"(()=>{{const d=window.__debug; d.attachToChain(d.templatesById['{t}'],500,300); d.recordHistory();}})()")
    order=pg.evaluate("window.__debug.chainOrder().map(b=>b.dataset.tpl)")
    check('chain order (mixed prepend/append)', order==['process-to-publish','consume-to-process','process-to-api','api-to-process'])
    pg.mouse.click(1300,700); pg.wait_for_timeout(400)
    pg.screenshot(path=D+'A.png'); A=worldstate(pg)
    flow=pg.evaluate("window.__debug.serializeFlow()"); print(json.dumps(flow))
    for i in range(4): pg.click('#undoBtn')
    check('undo x4 -> empty', pg.evaluate("window.__debug.chainOrder().length")==0 and pg.is_disabled('#undoBtn'))
    for i in range(4): pg.click('#redoBtn')
    pg.mouse.click(1300,700); pg.wait_for_timeout(400); pg.screenshot(path=D+'B.png')
    check('redo x4 pixel-identical', same(D+'A.png',D+'B.png'))
    check('redo x4 DOM-identical', worldstate(pg)==A)
    # keyboard
    pg.keyboard.press('Control+z'); check('Ctrl+Z', pg.evaluate("window.__debug.chainOrder().length")==3)
    pg.keyboard.press('Control+y'); check('Ctrl+Y', pg.evaluate("window.__debug.chainOrder().length")==4)
    # drag whole flow then undo
    r=pg.evaluate("(()=>{const r=window.__debug.chainOrder()[1].getBoundingClientRect();return [r.x+r.width/2,r.y+15]})()")
    x0=pg.evaluate("window.__debug.chainOrder()[0].style.left")
    pg.mouse.move(*r); pg.mouse.down(); pg.mouse.move(r[0]+120,r[1]+80,steps=5); pg.mouse.up()
    moved=pg.evaluate("window.__debug.chainOrder()[0].style.left")
    pg.keyboard.press('Control+z')
    check(f'drag recorded & undone ({x0}->{moved}->back)', moved!=x0 and pg.evaluate("window.__debug.chainOrder()[0].style.left")==x0)
    # rename then undo
    lbl=pg.locator('.cblock[data-id="'+pg.evaluate('window.__debug.chainOrder()[2].dataset.id')+'"] .cblock-label'); lbl.dblclick(); pg.keyboard.type('Orders iFlow'); pg.keyboard.press('Enter')
    check('rename applied', pg.evaluate("window.__debug.serializeFlow().blocks[2].label")=='Orders iFlow')
    pg.keyboard.press('Control+z')
    check('rename undone', pg.evaluate("window.__debug.serializeFlow().blocks[2].label")=='Process-to-API')
    pg.keyboard.press('Control+y')
    # delete end block + undo
    pg.evaluate("window.__debug.removeChainBlock(window.__debug.chainOrder()[3])")
    check('delete end', pg.evaluate("window.__debug.chainOrder().length")==3)
    pg.keyboard.press('Control+z'); check('delete undone', pg.evaluate("window.__debug.chainOrder().length")==4)
    # export
    pg.mouse.click(1300,700); pg.wait_for_timeout(400); pg.screenshot(path=D+'A2.png')
    with pg.expect_download() as dl: pg.click('#exportBtn')
    dl.value.save_as(D+'flow.json'); f=json.load(open(D+'flow.json'))
    check('export file valid', f['format']=='pattern-bench-flow' and len(f['blocks'])==4 and f['blocks'][2]['label']=='Orders iFlow')
    pg.click('#clearCanvas'); pg.click('#confirmOk'); check('cleared', pg.evaluate("window.__debug.chainOrder().length")==0)
    pg.set_input_files('#importFile', D+'flow.json'); pg.wait_for_timeout(300)
    pg.mouse.click(1300,700); pg.wait_for_timeout(2700); pg.screenshot(path=D+'C.png')
    check('import pixel-identical', same(D+'A2.png',D+'C.png'))
    pg.keyboard.press('Control+z'); check('import undoable', pg.evaluate("window.__debug.chainOrder().length")==0)
    # bad files
    bad=dict(f); bad['blocks']=[f['blocks'][0], f['blocks'][2]]; bad.pop('buildOrder')
    json.dump(bad,open(D+'bad.json','w'))
    pg.set_input_files('#importFile', D+'bad.json'); pg.wait_for_timeout(300)
    t=pg.inner_text('#toast'); print(' toast:',t)
    check('mismatched chain rejected', 'don\'t fit' in t and pg.evaluate("window.__debug.chainOrder().length")==0)
    pg.screenshot(path=D+'error-toast.png')
    open(D+'junk.json','w').write('{not json')
    pg.set_input_files('#importFile', D+'junk.json'); pg.wait_for_timeout(300)
    check('junk rejected', 'not valid JSON' in pg.inner_text('#toast'))
    # light theme render of reimported flow
    pg.keyboard.press('Control+y'); pg.click('#themeToggle'); pg.mouse.click(1300,700); pg.wait_for_timeout(5200)
    pg.screenshot(path=D+'light.png')
    check('no page errors', not errs); print(errs)
    b.close()
print(sum(r[1] for r in res),'/',len(res))
