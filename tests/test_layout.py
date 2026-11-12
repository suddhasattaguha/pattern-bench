"""Pattern Bench v1.9 — independent pane views and resizable library (Python Playwright).
Run: python3 tests/test_layout.py"""
import os
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = 'file:///' + ROOT.replace(os.sep, '/').lstrip('/') + '/pattern-bench.html'
res = []
def check(name, cond):
    res.append(bool(cond)); print(('PASS ' if cond else 'FAIL ') + name)

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1400, 'height': 860})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL)
    ev = pg.evaluate
    views = lambda: ev("window.__debug.views()")
    for t in ['api-to-process', 'process-to-publish', 'consume-to-api']:
        ev(f"(()=>{{const d=window.__debug; d.append('{t}'); d.recordHistory();}})()")
    ev("window.__debug.dropVersion('a2p-contract-parallel',10,10)")
    pg.wait_for_timeout(200)
    v0 = views()

    # pan the copy pane only
    pg.mouse.move(1250, 780); pg.mouse.down(); pg.mouse.move(1150, 740, steps=4); pg.mouse.up()
    v1 = views()
    check('dragging the copy pane moves only the copy', v1['copy']['panX'] == v0['copy']['panX'] - 100 and v1['copy']['panY'] == v0['copy']['panY'] - 40 and v1['base'] == v0['base'])
    check('copy pane becomes the active pane', v1['active'] == 'copy')

    # pan the base pane only
    pg.mouse.move(1250, 120); pg.mouse.down(); pg.mouse.move(1300, 150, steps=4); pg.mouse.up()
    v2 = views()
    check('dragging the base pane moves only the base', v2['base']['panX'] == v1['base']['panX'] + 50 and v2['copy'] == v1['copy'])
    check('base pane becomes the active pane', v2['active'] == 'base')

    # wheel zoom per pane
    pg.mouse.move(900, 700); pg.mouse.wheel(0, -100)
    v3 = views()
    check('wheel over the copy zooms only the copy', v3['copy']['zoom'] > v2['copy']['zoom'] and v3['base']['zoom'] == v2['base']['zoom'])
    pg.mouse.move(900, 200); pg.mouse.wheel(0, 100)
    v4 = views()
    check('wheel over the base zooms only the base', v4['base']['zoom'] < v3['base']['zoom'] and v4['copy']['zoom'] == v3['copy']['zoom'])

    # toolbar zoom follows the pane touched last
    pg.click('#zoomIn'); v5 = views()
    check('toolbar zoom acts on the active (base) pane', v5['base']['zoom'] > v4['base']['zoom'] and v5['copy']['zoom'] == v4['copy']['zoom'])
    pg.mouse.click(1250, 780); pg.click('#zoomIn'); v6 = views()
    check('toolbar zoom acts on the copy after touching it', v6['copy']['zoom'] > v5['copy']['zoom'] and v6['base']['zoom'] == v5['base']['zoom'])
    check('zoom readout shows the active pane', pg.inner_text('#zoomReadout') == str(round(v6['copy']['zoom'] * 100)) + '%')

    pg.click('#zoomReset'); v7 = views()
    check('Reset view re-aligns both panes', v7['base'] == v7['copy'] and v7['base']['zoom'] == 1)

    # versioned block is still hit-testable after independent zoom
    pg.mouse.move(900, 700); pg.mouse.wheel(0, -100); pg.mouse.wheel(0, -100)
    r = ev("(()=>{const r=document.querySelector('#vworld .versioned').getBoundingClientRect();return [r.x+r.width/2,r.y+16]})()")
    pg.mouse.click(r[0], r[1])
    check('versioned block selectable in zoomed copy', pg.locator('#vworld .versioned.selected').count() == 1)
    pg.click('#zoomReset')

    # resizable library
    w = lambda: ev("document.querySelector('.palette').getBoundingClientRect().width")
    w0 = w()
    card0 = ev("(()=>{const c=[...document.querySelectorAll('#quadrantGrid .quad')[0].querySelectorAll('.palette-block')].map(e=>e.getBoundingClientRect());return [Math.round(c[0].width), c.filter(r=>r.top===c[0].top).length]})()")
    hx = w0 - 3
    pg.mouse.move(hx, 400); pg.mouse.down(); pg.mouse.move(hx + 260, 400, steps=5); pg.mouse.up()
    check('dragging the library edge widens it', abs(w() - (w0 + 260)) <= 2)
    check('canvas shrinks to match', abs(ev("document.getElementById('canvasWrap').getBoundingClientRect().left") - w()) <= 1)
    card = "(()=>{const c=[...document.querySelectorAll('#quadrantGrid .quad')[0].querySelectorAll('.palette-block')].map(e=>e.getBoundingClientRect());return [Math.round(c[0].width), c.filter(r=>r.top===c[0].top).length]})()"
    cw, per_row = ev(card)
    check('cards keep their size when the library widens (no zoom effect)', abs(cw - card0[0]) <= 1)
    check('wider library fits more cards per row', per_row > card0[1])
    pg.mouse.move(w() - 3, 400); pg.mouse.down(); pg.mouse.move(40, 400, steps=5); pg.mouse.up()
    wmin = w(); check('library has a minimum width', 180 <= wmin <= 260)
    pg.mouse.move(wmin - 3, 400); pg.mouse.down(); pg.mouse.move(1300, 400, steps=5); pg.mouse.up()
    wmax = w(); check('library has a maximum width', wmax <= 720 and ev("document.getElementById('canvasWrap').getBoundingClientRect().width") >= 300)
    pg.mouse.dblclick(wmax - 3, 400)
    check('double-click resets the width', abs(w() - w0) <= 1)

    # drop still lands on the right block when the library is wide
    pg.mouse.move(w0 - 3, 400); pg.mouse.down(); pg.mouse.move(w0 + 150, 400, steps=5); pg.mouse.up()
    ev("window.__debug.removeVersion(window.__debug.chainOrder()[0].dataset.id)")
    r = ev("(()=>{const r=window.__debug.chainOrder()[0].getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]})()")
    ev(f"window.__debug.dropVersion('a2p-process-switch',{r[0]},{r[1]})")
    check('version drop works with a wide library', ev("Object.values(window.__debug.versionOverrides())") == ['a2p-process-switch'])

    check('no page errors', not errs); print(errs)
    br.close()
print(sum(res), '/', len(res))
