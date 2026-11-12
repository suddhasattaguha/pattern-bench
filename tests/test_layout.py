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

    # base mode: the base has the whole canvas, the copy is a small window
    check('Base Flow Design: base is the big view, copy hidden behind it', not pg.is_visible('#versionPane'))
    check('the copy shows as a small window at the bottom right', pg.is_visible('#miniView') and 'of-copy' in pg.get_attribute('#miniView', 'class')
          and 'at-bottom' in pg.get_attribute('#miniView', 'class') and pg.locator('#miniStage .cblock.versioned').count() == 1)
    pg.mouse.move(600, 760); pg.mouse.down(); pg.mouse.move(650, 790, steps=4); pg.mouse.up()
    v1 = views()
    check('dragging the canvas moves only the base', v1['base']['panX'] == v0['base']['panX'] + 50 and v1['copy'] == v0['copy'])
    pg.mouse.move(900, 300); pg.mouse.wheel(0, 100)
    v2 = views()
    check('wheel zooms only the base', v2['base']['zoom'] < v1['base']['zoom'] and v2['copy'] == v1['copy'])
    pg.click('#zoomIn'); v3 = views()
    check('toolbar zoom acts on the big view (base)', v3['base']['zoom'] > v2['base']['zoom'] and v3['copy'] == v2['copy'])
    mb = pg.locator('#miniView').bounding_box()
    pg.mouse.move(mb['x'] + 150, mb['y'] + 75); pg.mouse.wheel(0, -100)
    check('wheel over the small window changes nothing', views() == v3)

    # swap: clicking the small window switches to versioning mode
    pg.click('#miniView')
    check('clicking the small window swaps: copy becomes the big view', pg.is_visible('#versionPane'))
    check('…and switches the library to Versioned Artifacts', 'active' in pg.get_attribute('#tabVersioned', 'class') and pg.is_visible('#modeBanner'))
    check('the base is now the small window at the top right', 'at-top' in pg.get_attribute('#miniView', 'class')
          and pg.inner_text('#miniTag').lower() == 'base flow' and pg.locator('#miniStage .cblock').count() == 3)
    v4 = views()
    check('copy is the active pane', v4['active'] == 'copy')
    pg.mouse.move(900, 600); pg.mouse.down(); pg.mouse.move(800, 560, steps=4); pg.mouse.up()
    v5 = views()
    check('dragging the canvas moves only the copy', v5['copy']['panX'] == v4['copy']['panX'] - 100 and v5['copy']['panY'] == v4['copy']['panY'] - 40 and v5['base'] == v4['base'])
    pg.mouse.move(900, 600); pg.mouse.wheel(0, -100)
    v6 = views()
    check('wheel zooms only the copy', v6['copy']['zoom'] > v5['copy']['zoom'] and v6['base'] == v5['base'])
    pg.click('#zoomIn'); v7 = views()
    check('toolbar zoom acts on the big view (copy)', v7['copy']['zoom'] > v6['copy']['zoom'] and v7['base'] == v6['base'])
    check('zoom readout shows the big view', pg.inner_text('#zoomReadout') == str(round(v7['copy']['zoom'] * 100)) + '%')
    pg.click('#zoomReset'); v8 = views()
    check('Reset view re-aligns both views', v8['base'] == v8['copy'] and v8['base']['zoom'] == 1)

    # versioned block is still hit-testable after zooming the copy
    pg.mouse.move(900, 600); pg.mouse.wheel(0, -100); pg.mouse.wheel(0, -100)
    r = ev("(()=>{const r=document.querySelector('#vworld .versioned').getBoundingClientRect();return [r.x+r.width/2,r.y+16]})()")
    pg.mouse.click(r[0], r[1])
    check('versioned block selectable in zoomed copy', pg.locator('#vworld .versioned.selected').count() == 1)
    pg.click('#zoomReset')

    pg.click('#miniView')
    check('clicking the small window again returns to the base flow', not pg.is_visible('#versionPane') and 'active' in pg.get_attribute('#tabBaseFlow', 'class'))
    pg.click('#tabVersioned')
    check('the library tab swaps the views too', pg.is_visible('#versionPane'))
    pg.click('#tabBaseFlow')

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
