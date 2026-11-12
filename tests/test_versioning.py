"""Pattern Bench v1.8 — versioned copy checks (Python Playwright).
Run: python3 tests/test_versioning.py"""
import json, os, tempfile
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = 'file:///' + ROOT.replace(os.sep, '/').lstrip('/') + '/pattern-bench.html'
D = tempfile.mkdtemp() + '/'
res = []
def check(name, cond):
    res.append(bool(cond)); print(('PASS ' if cond else 'FAIL ') + name)
def same(a, b, box=(261, 53, 1400, 860)):
    return ImageChops.difference(Image.open(a).convert('RGB').crop(box), Image.open(b).convert('RGB').crop(box)).getbbox() is None

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1400, 'height': 860}, accept_downloads=True)
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    dialogs = []; pg.on('dialog', lambda d: (dialogs.append(d.message), d.dismiss()))
    pg.goto(URL)
    ev = pg.evaluate
    n = lambda: ev("window.__debug.chainOrder().length")
    ov = lambda: ev("Object.values(window.__debug.versionOverrides())")
    split = lambda: ev("document.getElementById('canvasWrap').classList.contains('split')")
    pg.click('#tabVersioned')
    check('version cards unavailable with empty flow', pg.locator('.version-card.unavailable').count() == 17)
    check('every quadrant has versioned blocks', pg.locator('#versionGrid .quad-empty').count() == 0)
    check('exit quadrants hold the Process-to-API, -File and -Publish blocks', pg.locator('#versionGrid .quad:nth-child(3) .version-card').count() == 3 and pg.locator('#versionGrid .quad:nth-child(4) .version-card').count() == 6)
    check('entry quadrants hold the API-to-Process and File-to-Process blocks', pg.locator('#versionGrid .quad:nth-child(1) .version-card').count() == 4 and pg.locator('#versionGrid .quad:nth-child(2) .version-card').count() == 4)

    for t in ['api-to-process', 'process-to-publish', 'consume-to-api']:
        ev(f"(()=>{{const d=window.__debug; d.attachToChain(d.templatesById['{t}'],560,240); d.recordHistory();}})()")
    check('only versions of blocks in the flow are available', pg.locator('.version-card.unavailable').count() == 10)
    check('no split before first version', not split())

    # real drag-and-drop from the palette card onto the base block
    target = pg.evaluate("(()=>{const r=window.__debug.chainOrder()[0].getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]})()")
    pg.evaluate("""([sel,x,y])=>{const src=[...document.querySelectorAll('.version-card')].find(c=>c.textContent.includes('own Process v2'));
        const dt=new DataTransfer(); src.dispatchEvent(new DragEvent('dragstart',{dataTransfer:dt,bubbles:true}));
        const t=document.elementFromPoint(x,y); t.dispatchEvent(new DragEvent('drop',{dataTransfer:dt,clientX:x,clientY:y,bubbles:true}));}""", ['', target[0], target[1]])
    check('first drop creates split + version', split() and ov() == ['a2p-contract-parallel'])
    check('copy has one block per base block', pg.locator('#vworld .cblock').count() == 3)
    check('copy versioned block aligned to base x', ev("document.querySelector('#vworld .versioned').style.left === window.__debug.chainOrder()[0].style.left"))
    check('roles drawn: 1 primary, 1 side-effect', pg.locator('#vworld .node[data-role=primary]').count() == 1 and pg.locator('#vworld .node[data-role=side]').count() == 1)
    check('base flow itself unchanged', pg.locator('#world .versioned').count() == 0 and n() == 3)

    # replace with another variant on the same block
    ev("window.__debug.dropVersion('a2p-process-switch',10,10)")
    check('second version replaces the first', ov() == ['a2p-process-switch'])
    check('retired link drawn dotted', pg.locator('#vworld .flow-layer .link.retired').count() >= 1)

    # base edits flow through: rename + drag
    lbl = pg.locator('#world .cblock[data-id="' + ev("window.__debug.chainOrder()[0].dataset.id") + '"] .cblock-label')
    lbl.dblclick(); pg.keyboard.press('Control+a'); pg.keyboard.type('Order API'); pg.keyboard.press('Enter')
    check('base rename shows in copy', pg.inner_text('#vworld .versioned .cblock-label') == 'Order API')
    r = ev("(()=>{const r=window.__debug.chainOrder()[1].getBoundingClientRect();return [r.x+r.width/2,r.y+12]})()")
    pg.mouse.move(*r); pg.mouse.down(); pg.mouse.move(r[0]+80, r[1]+40, steps=4); pg.mouse.up()
    check('base drag moves copy', ev("document.querySelector('#vworld .versioned').style.left === window.__debug.chainOrder()[0].style.left"))

    # export -> clear (in-app confirm, no browser dialog) -> import
    copyHtml = lambda: __import__('re').sub(r'data-(base-id|seq|left-linked|right-linked|id)="[^"]*"', '', ev("document.getElementById('vworld').innerHTML")).replace(' selected', '')
    pg.mouse.click(700, 840); pg.wait_for_timeout(400); before = copyHtml()
    with pg.expect_download() as dl: pg.click('#exportBtn')
    dl.value.save_as(D + 'f.json'); f = json.load(open(D + 'f.json'))
    check('export includes versions', f['versions'] == [{'block': 0, 'variant': 'a2p-process-switch'}])
    pg.click('#clearCanvas'); pg.wait_for_timeout(100)
    check('clear asks in-app (no browser dialog)', pg.is_visible('#confirmBox') and not dialogs)
    pg.click('#confirmCancel'); check('cancel keeps flow', n() == 3 and split())
    pg.click('#clearCanvas'); pg.click('#confirmOk')
    check('clear removes flow and copy', n() == 0 and not split() and ov() == [])
    pg.set_input_files('#importFile', D + 'f.json'); pg.wait_for_timeout(300)
    pg.mouse.click(700, 840); pg.wait_for_timeout(300)
    check('import restores the versioned copy exactly', copyHtml() == before and ov() == ['a2p-process-switch'])

    # undo / redo across version actions
    ev("window.__debug.removeVersion(window.__debug.chainOrder()[0].dataset.id)")
    check('removing last version closes split', not split())
    pg.keyboard.press('Control+z'); check('undo brings version back', ov() == ['a2p-process-switch'] and split())
    pg.keyboard.press('Control+y'); check('redo removes it again', ov() == [])
    pg.keyboard.press('Control+z')

    # select + Delete key removes version only
    pg.locator('#vworld .versioned').click(position={'x': 100, 'y': 125})
    pg.keyboard.press('Delete')
    check('Delete on versioned block removes version, keeps base', ov() == [] and n() == 3)
    pg.keyboard.press('Control+z')

    # deleting the base block deletes its version (mirror)
    ev("window.__debug.removeChainBlock(window.__debug.chainOrder()[0])")
    check('deleting base block removes its version', ov() == [] and not split() and n() == 2)
    pg.keyboard.press('Control+z')
    check('undo restores block and version', n() == 3 and ov() == ['a2p-process-switch'])

    # wrong target / no target
    ev("window.__debug.removeChainBlock(window.__debug.chainOrder()[0])")
    ev("window.__debug.dropVersion('a2p-contract-shared',10,10)"); pg.wait_for_timeout(100)
    check('no API-to-Process -> rejected with message', 'first' in pg.inner_text('#toast') and ov() == [])
    pg.keyboard.press('Control+z')

    # invalid version entries rejected on import
    for bad, why in [({'block': 1, 'variant': 'a2p-contract-shared'}, "doesn't belong"),
                     ({'block': 0, 'variant': 'nope'}, 'Unknown versioned block')]:
        g = dict(f); g['versions'] = [bad]; json.dump(g, open(D + 'bad.json', 'w'))
        pg.set_input_files('#importFile', D + 'bad.json'); pg.wait_for_timeout(200)
        check('import rejects: ' + why, why in pg.inner_text('#toast'))

    # middle-block delete uses in-app confirm too
    ev("window.__debug.removeChainBlock(window.__debug.chainOrder()[1])")
    check('middle delete asks in-app', pg.is_visible('#confirmBox') and not dialogs)
    pg.keyboard.press('Escape'); check('Esc cancels', not pg.is_visible('#confirmBox') and n() == 3)

    # Process-to-API versions, with an upstream neighbour (links must reach both lanes)
    pg.click('#clearCanvas'); pg.click('#confirmOk')
    for t in ['api-to-process', 'process-to-api']:
        ev(f"(()=>{{const d=window.__debug; d.attachToChain(d.templatesById['{t}'],470,240); d.recordHistory();}})()")
    check('Process-to-API versions available once it is in the flow', pg.locator('.version-card.unavailable').count() == 10)
    for vid in ['p2a-contract-parallel', 'p2a-contract-switch', 'p2a-process-shared']:
        ev(f"window.__debug.dropVersion('{vid}',10,10)")
        check(vid + ' applies to Process-to-API', ov() == [vid])
    ys = ev("""(()=>{const ns=[...document.querySelectorAll('#vworld .flow-layer .node[data-type=process]')].map(n=>n.transform.baseVal[0].matrix.f);
        const ends=[...document.querySelectorAll('#vworld .flow-layer .link')].map(l=>l.tagName==='line'?+l.getAttribute('y2'):+l.getAttribute('d').trim().split(' ').pop());
        return {procs:ns.sort(), ends:ends}})()""")
    check('upstream links end on both process lanes', all(any(abs(e - y) < 0.5 for e in ys['ends']) for y in ys['procs']) and len(ys['procs']) == 2)
    check('no page errors', not errs); print(errs)
    br.close()
print(sum(res), '/', len(res))
