"""Pattern Bench — API boundary rule, new blocks/versions, library narrowing and layout.
Run: python3 tests/test_boundary.py"""
import json, os
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = 'file:///' + ROOT.replace(os.sep, '/').lstrip('/') + '/pattern-bench.html'
res = []
def check(name, cond):
    res.append(bool(cond)); print(('PASS ' if cond else 'FAIL ') + name)

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1400, 'height': 900})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    ev = pg.evaluate
    def flow(*tpls, versioning=False):
        pg.goto(URL)
        for t in tpls:
            ev(f"(()=>{{window.__debug.append('{t}'); window.__debug.recordHistory();}})()")
        pg.mouse.click(1300, 860)
        if versioning: pg.click('#tabVersioned')
    def drop(vid, i):
        r = ev(f"(()=>{{const r=window.__debug.chainOrder()[{i}].getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}})()")
        ev(f"window.__debug.dropVersion('{vid}',{r[0]},{r[1]})")
    types = lambda pane='#world': ev(f"[...document.querySelectorAll('{pane} .pcont-type')].map(t=>t.textContent)")
    click = lambda sel: ev(f"document.querySelector({json.dumps(sel)}).click()")
    shown = lambda: ev("[...document.querySelectorAll('#versionGrid .version-card:not(.off-flow):not(.not-suggested) .pb-label')].map(e=>e.textContent)")

    # ---------- an API joined by two blocks is a boundary ----------
    flow('api-to-process', 'process-to-api', 'api-to-process', 'process-to-api')
    check('a joined API is no end application: iPaaS | iPaaS (API + process) | end application',
          types() == ['IPAAS', 'IPAAS', 'END APPLICATION'])
    mid = ev("""(()=>{const c=window.__debug.chainOrder(); const k=c[1].dataset.id+':out';
      return [...document.querySelectorAll('#world .flow-layer .node')].filter(n=>n.dataset.skey===k).map(n=>n.getAttribute('class'))})()""")
    check('the middle API is drawn as iPaaS, in the downstream container', len(mid) == 1 and 'own-ipaas' in mid[0])
    flow('process-to-api', 'api-to-process', 'process-to-publish', 'consume-to-api')
    check('Process-to-API → API-to-Process: no longer one merged iPaaS', types() == ['IPAAS', 'IPAAS', 'MESSAGE BROKER', 'END APPLICATION'])
    pg.click('#tabVersioned')
    drop('p2a-contract-parallel', 0)
    check('versions keep the split in the copy', types('#vworld')[:2] == ['IPAAS', 'IPAAS'])

    # ripple through a boundary API asks for that API's version instead of flagging an end application
    flow('api-to-process', 'process-to-api', 'api-to-process', versioning=True)
    drop('a2p-contract-shared', 0)
    click('#vworld .ripple-card [data-ripple=pass]')
    click('#vworld .ripple-card [data-code=no]')
    forced = [d for d in ev("window.__debug.decisions()") if d.get('passed')]
    check('passed on to a boundary API: Process-to-API is asked to version that API, no ⚠',
          len(forced) == 1 and forced[0]['type'] == 'api' and forced[0]['options'] == ['p2a-contract-parallel', 'p2a-contract-switch']
          and pg.locator('#vworld .ibadge').count() == 0)

    # ---------- API-to-API ----------
    flow('api-to-api')
    check('API-to-API is an entry pattern card', 'API-to-API' in ev("[...document.querySelectorAll('#quadrantGrid .quad:first-child .pb-label')].map(e=>e.textContent)"))
    pg.click('#world .caller-card [data-caller=no]') if pg.locator('.caller-card').count() else None
    check('front API and backend API sit in two separate iPaaS containers', types() == ['IPAAS', 'IPAAS'])
    ev("window.__debug.append('api-to-process')")
    check('API-to-API → API-to-Process: front API | backend API + process', types() == ['IPAAS', 'IPAAS'])
    pg.click('#tabVersioned')
    check('API-to-API has two versions', all(v in shown() for v in ['Backend API v2 · own front API v2', 'Backend API v2 · same front API switches']))
    drop('a2a-own-backend', 0)
    check('Backend API v2 · own front API v2: two API lanes each side', ev("document.querySelectorAll('#vworld .flow-layer .node[data-type=api]').length") >= 4)

    # ---------- new versions ----------
    flow('process-to-publish', 'consume-to-api', versioning=True)
    drop('c2a-api-parallel', 1)
    check('Consume-to-API parallel: two queues from the same topic, two API lanes',
          ev("document.querySelectorAll('#vworld .flow-layer .node[data-type=queue]').length") == 2
          and ev("document.querySelectorAll('#vworld .flow-layer .node[data-type=api]').length") == 2)
    flow('api-to-process', 'process-to-publish', versioning=True)
    check('Process-to-Publish offers New Process v2 · own Topic v2 (process change)', 'New Process v2 · own Topic v2' in shown()
          and ev("document.querySelector('.quad[data-q=exit-process]').textContent").count('own Topic v2') == 1)
    drop('p2t-process-topic', 1)
    d = ev("window.__debug.decisions()")
    check('Process v2 asks upstream API-to-Process', [x['index'] for x in d] == [0])

    # ---------- library: only relevant cards, never greyed ----------
    flow('api-to-process', 'process-to-publish', 'consume-to-process', 'process-to-api', versioning=True)
    drop('p2a-process-shared', 3)
    pg.locator('#vworld .flow-layer .node[data-type=process]').first.click()
    vis = shown()
    check('after a version exists, a process click shows only the process versions of this flow (none greyed)',
          len(vis) == 4 and ev("[...document.querySelectorAll('#versionGrid .version-card.not-suggested')].every(c=>getComputedStyle(c).display==='none')"))
    pg.locator('#vworld .target-card .dc-side button').nth(1).click()
    check('Downstream keeps only that side in the library', sorted(shown()) == ['New Process v2 · own Topic v2', 'New Process v2 · same Topic'])
    check('quadrants without a match say so', pg.locator('#versionGrid .quad-empty:visible').count() >= 1
          and 'selection' in pg.locator('#versionGrid .quad-empty:visible').first.inner_text())

    # compact cards, hover help
    card = pg.locator('#versionGrid .version-card:not(.off-flow)').first
    check('version cards show the picture only (no visible text)', ev("(()=>{const l=document.querySelector('#versionGrid .version-card:not(.off-flow) .pb-label');return l.getBoundingClientRect().width<=1})()"))
    check('the name and description show on hover', '\n\n' in (card.get_attribute('title') or ''))

    # sticky axis headers
    flow('api-to-process', 'process-to-publish', 'consume-to-process', 'process-to-api', versioning=True)
    top0 = ev("document.querySelector('#versionGrid .vg-col').getBoundingClientRect().top")
    ev("document.getElementById('versionGrid').scrollTop = 400")
    pg.wait_for_timeout(100)
    top1 = ev("document.querySelector('#versionGrid .vg-col').getBoundingClientRect().top")
    check('axis headers stay visible while the quadrants scroll', ev("document.getElementById('versionGrid').scrollTop") > 0 and abs(top1 - top0) < 1)
    check('axis lines are bold', ev("getComputedStyle(document.querySelector('.quad[data-q=entry-process]')).borderRightWidth") == '3px')

    # ---------- arrows, card names, Δ badge, end application labels, print preview ----------
    flow('api-to-process', 'process-to-api')
    arrows = ev("document.querySelectorAll('#world .flow-layer .link-arrow').length")
    links = ev("document.querySelectorAll('#world .flow-layer .link').length")
    check('every link ends in an arrowhead', arrows == links and arrows > 0)
    tip = ev("""(()=>{const a=document.querySelector('#world .flow-layer .link-arrow'); const d=a.getAttribute('d'); return +d.slice(1).split(' ')[0]})()""")
    nodes = ev("[...document.querySelectorAll('#world .flow-layer .node')].map(n=>n.transform.baseVal.consolidate().matrix.e)")
    check('the arrowhead sits right before the receiving symbol', any(0 < x - tip < 40 for x in nodes))
    check('no chevrons in the middle of links any more', pg.locator('.link-mark').count() == 0)
    pg.click('#tabVersioned')
    check('version cards show the base pattern name', pg.locator('#versionGrid .version-card:not(.off-flow) .pb-sub').first.inner_text() in ('API-to-Process', 'Process-to-API')
          and ev("(()=>{const l=document.querySelector('#versionGrid .version-card:not(.off-flow) .pb-label');return l.getBoundingClientRect().width<=1})()"))
    pg.locator('#world .flow-layer .node[data-type=api]').nth(1).click()
    pg.click('#world .target-card .dc-mark')
    pg.locator('#vworld .dbadge').first.click()
    check('clicking the v1 Δ badge opens its card with "Remove the v1 Δ mark"', 'Remove' in pg.inner_text('#vworld .target-card .dc-mark'))
    pg.click('#vworld .target-card .dc-mark')
    check('…and removes it', pg.locator('#vworld .dbadge').count() == 0)
    flow('process-to-publish', 'consume-to-process', 'process-to-api', versioning=True)
    drop('c2p-contract-dual', 1)
    click('#vworld .ripple-card [data-ripple=absorb]')
    pg.locator('#vworld .dbadge').first.click()
    check('a ripple Δ offers to change the ripple answer', pg.locator('#vworld .target-card [data-action=ripple-again]').count() == 1)
    pg.click('#vworld .target-card [data-action=ripple-again]')
    check('…which reopens absorb / pass on', pg.locator('#vworld .ripple-card [data-ripple]').count() == 2)
    pg.click('#tabBaseFlow')
    pg.locator('#world .pcont-label.editable').last.click()
    check('an end application asks for its name and business process', pg.locator('.label-editor input[name=name]').count() == 1
          and pg.locator('.label-editor input[name=process]').count() == 1 and pg.locator('.label-editor input[name=platform]').count() == 0)
    pg.fill('.label-editor input[name=name]', 'S/4HANA'); pg.fill('.label-editor input[name=process]', 'Sales order creation'); pg.keyboard.press('Enter')
    check('the label shows the name and the business process', ev("[...document.querySelectorAll('#world .pcont-name')].pop().textContent") == 'S/4HANA'
          and ev("[...document.querySelectorAll('#world .pcont-proc')].map(t=>t.textContent)") == ['Sales order creation'])
    pg.locator('#world .pcont-label.editable').first.click()
    check('an iPaaS still asks for platform and asset', pg.locator('.label-editor input[name=platform]').count() == 1)
    pg.keyboard.press('Escape')
    pg.click('#printBtn')
    check('Print opens an in-app preview with Print / Download / Close', pg.is_visible('.print-host .pp-frame')
          and pg.locator('.print-host [data-pp]').count() == 3 and 'S/4HANA' in pg.inner_text('.print-host .ps-cols'))
    with pg.expect_download() as dl: pg.click('.print-host [data-pp=download]')
    html = open(dl.value.path()).read()
    check('Download sheet saves a standalone page with the sheet', html.startswith('<!doctype html>') and 'print-sheet' in html and 'S/4HANA' in html)
    pg.click('.print-host [data-pp=close]')
    check('Close returns to the app', not pg.is_visible('.print-host') and not ev("document.body.classList.contains('light-theme')"))

    check('no page errors', not errs); print(errs)
    br.close()
print(sum(res), '/', len(res))
