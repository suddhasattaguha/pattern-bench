"""Pattern Bench — dependency between versioned blocks (Python Playwright).
Run: python3 tests/test_dependency.py"""
import os
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
    def flow(*tpls):
        pg.goto(URL)
        for t in tpls:
            ev(f"(()=>{{const d=window.__debug; d.append('{t}'); d.recordHistory();}})()")
        pg.click('#tabVersioned')   # versioning mode: the copy gets the big view
    def drop(vid, idx):
        r = ev(f"(()=>{{const r=window.__debug.chainOrder()[{idx}].getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}})()")
        ev(f"window.__debug.dropVersion('{vid}',{r[0]},{r[1]})")
    dec = lambda: ev("window.__debug.decisions()")
    ov = lambda: ev("Object.fromEntries(window.__debug.chainOrder().map((b,i)=>[i, window.__debug.versionOverrides()[b.dataset.id]||null]))")
    sugg = lambda: sorted(ev("[...document.querySelectorAll('.version-card.suggested')].map(c=>c.querySelector('.pb-label').textContent)"))

    # --- upstream: S/4 API changes, process gets v2 in parallel ---
    flow('api-to-process', 'process-to-api')
    drop('p2a-contract-parallel', 1)
    d = dec()
    check('downstream API change with Process v2 opens one upstream decision', len(d) == 1 and d[0]['index'] == 0 and d[0]['type'] == 'process')
    check('suggests the two process-change options of API-to-Process', d[0]['options'] == ['a2p-process-parallel', 'a2p-process-switch'])
    check('impacted block marked pending in the copy', pg.locator('#vworld .cblock.pending').count() == 1)
    check('question card shown on the canvas', pg.locator('#vworld .decision-card').count() == 1 and 'Process v2 is new' in pg.inner_text('#vworld .decision-card'))
    check('card offers both options', pg.locator('#vworld .decision-card .dc-opt').count() == 2)
    check('library highlights the suggestions', sugg() == ['New Process v2 · own API v2', 'New Process v2 · same API'])
    check('other library cards dimmed', pg.locator('.version-card.not-suggested').count() == len(ev("Object.keys(window.__debug.variantsById)")) - 2)
    check('Versioned tab shows the pending count', pg.get_attribute('#tabVersioned', 'data-pending') == '1')
    card = pg.locator('#vworld .decision-card').bounding_box(); pane = pg.locator('#versionPane').bounding_box()
    check('new card fits inside the copy pane', card['y'] + card['height'] <= pane['y'] + pane['height'] and card['y'] >= pane['y'])

    # decide later -> pill stays, reopen
    pg.click('#vworld .decision-card [data-action=later]')
    check('Decide later collapses to a pending pill', pg.locator('#vworld .decision-pill').count() == 1 and pg.locator('#vworld .decision-card').count() == 0)
    check('block stays marked pending', pg.locator('#vworld .cblock.pending').count() == 1 and len(dec()) == 1)
    pg.click('#vworld .decision-pill')
    check('pill reopens the question', pg.locator('#vworld .decision-card').count() == 1)
    pg.click('#vworld .decision-card .dc-close')
    check('the × also leaves the decision open as a pill', pg.locator('#vworld .decision-pill').count() == 1 and pg.locator('#vworld .decision-card').count() == 0)
    pg.click('#vworld .decision-pill')
    pg.mouse.click(950, 170)
    check('clicking empty canvas closes the card to a pill', pg.locator('#vworld .decision-pill').count() == 1 and len(dec()) == 1)
    pg.click('#vworld .decision-pill')

    # show in library
    pg.click('#vworld .decision-card [data-action=library]')
    check('Show in library keeps the Versioned tab with the suggestion in view', 'active' in (pg.get_attribute('#tabVersioned', 'class') or '')
          and pg.locator('.version-card.suggested').first.is_visible())

    # pick an option
    pg.click('#vworld .decision-card .dc-opt[data-variant=a2p-process-switch]')
    check('picking an option applies it to the impacted block', ov() == {'0': 'a2p-process-switch', '1': 'p2a-contract-parallel'})
    check('decision resolved: no card, no pending mark, no highlight', len(dec()) == 0 and pg.locator('#vworld .decision-card, #vworld .cblock.pending').count() == 0 and sugg() == [])
    check('pending count cleared', pg.get_attribute('#tabVersioned', 'data-pending') is None)
    pg.keyboard.press('Control+z')
    check('undo brings the open decision back', len(dec()) == 1 and pg.locator('#vworld .decision-card').count() == 1)

    # a version that keeps the shared process opens no version decision — but its
    # contract change reaches that process, so the neighbour is asked absorb / pass on
    drop('p2a-contract-switch', 1)
    check('Target API v2 · same Process opens no version decision, only the ripple question',
          [(x.get('kind'), x['index']) for x in dec()] == [('ripple', 0)])
    # process v2 with v1 retired also opens the decision
    drop('p2a-process-shared', 1)
    check('New Process v2 · same target API opens the upstream decision', [x['options'] for x in dec()] == [['a2p-process-parallel', 'a2p-process-switch']])

    # conflicting version on the neighbour stays pending
    drop('a2p-contract-shared', 0)
    d = dec()
    check('neighbour version without Process v2 stays pending', len(d) == 1 and d[0]['current'] == 'a2p-contract-shared')
    check('card says the current version keeps Process unchanged', 'keeps Process unchanged' in pg.inner_text('#vworld .decision-card'))

    # --- downstream: inbound API change gives Process v2, Process-to-Publish must decide ---
    flow('api-to-process', 'process-to-publish')
    drop('a2p-contract-parallel', 0)
    d = dec()
    check('impact also runs downstream', len(d) == 1 and d[0]['index'] == 1 and d[0]['side'] == 'downstream')
    check('downstream suggestion is Process-to-Publish’s process change', d[0]['options'] == ['p2t-process-shared', 'p2t-process-topic'])

    # --- stops at the direct neighbour ---
    flow('api-to-process', 'process-to-api', 'api-to-process')
    drop('p2a-contract-parallel', 1)
    check('a change on both shared connectors asks both direct neighbours', sorted(x['index'] for x in dec()) == [0, 2])
    check('each neighbour gets its own card', pg.locator('#vworld .decision-card').count() == 2)
    flow('api-to-process', 'process-to-api', 'api-to-process')
    drop('a2p-contract-parallel', 2)
    check('the block two steps away is not asked (no chain)', [x['index'] for x in dec()] == [1])

    # --- Consume-to-API: a new topic upstream asks the relay to switch ---
    flow('process-to-publish', 'consume-to-api')
    drop('p2t-contract-switch', 0)
    d = dec()
    check('Topic v2 upstream asks Consume-to-API, suggesting the subscription switch', len(d) == 1 and d[0]['options'] == ['c2a-topic-switch'])
    check('card offers that one option', pg.locator('#vworld .decision-card .dc-opt').count() == 1)
    # --- API-to-Publish: Topic v2 asks the downstream Consume-to-Process ---
    flow('api-to-publish', 'consume-to-process')
    drop('a2t-topic-switch', 0)
    check('API-to-Publish Topic v2 asks Consume-to-Process with its three topic options',
          [x['options'] for x in dec()] == [['c2p-contract-parallel', 'c2p-contract-dual', 'c2p-contract-switch']])
    drop('a2t-api-parallel', 0)
    check('API v2 next to v1 on the same topic opens nothing downstream', len(dec()) == 0)
    flow('process-to-publish', 'consume-to-api')
    drop('p2t-contract-switch', 0)

    # --- removing the source version clears the decision ---
    ev("window.__debug.removeVersion(window.__debug.chainOrder()[0].dataset.id)")
    check('removing the version clears the decision and the split', len(dec()) == 0 and pg.locator('#vworld .decision-card').count() == 0)

    check('no page errors', not errs); print(errs)
    br.close()
print(sum(res), '/', len(res))
