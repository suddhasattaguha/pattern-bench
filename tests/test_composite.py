"""Pattern Bench 2.0 trial — flow mode switch and composite flow (Python Playwright).
Run: python3 tests/test_composite.py"""
import os, json
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = 'file:///' + ROOT.replace(os.sep, '/').lstrip('/') + '/pattern-bench.html'
SHOT = os.environ.get('PB_SHOT')
res = []
def check(name, cond):
    res.append(bool(cond)); print(('PASS ' if cond else 'FAIL ') + name)

ON_LINE = """(sel) => [...document.querySelectorAll(sel + ' .flow-layer .link-arrow')].every(a => {
    const m = /^M([-\\d.]+) ([-\\d.]+)/.exec(a.getAttribute('d')); const pt = new DOMPoint(+m[1], +m[2]);
    return [...a.ownerSVGElement.querySelectorAll('.link')].some(l => l.isPointInStroke(pt)); })"""

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1500, 'height': 900})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL)
    ev = pg.evaluate
    d = "window.__debug"
    def pick(skey):
        pg.locator(f'#world .flow-layer .node[data-skey="{skey}"]').first.click(force=True)
    branches = lambda: ev(f"{d}.branches()")
    tpls = lambda: ev("[...document.querySelectorAll('#world .cblock')].map(b=>[b.dataset.id,b.dataset.tpl])")
    def ids_of(t): return [i for i, x in tpls() if x == t]
    available = lambda: ev(f"Object.keys({d}.templatesById).filter(id => {d}.isCompatible(id))")

    # ---- fix 3: the switch
    check('Single flow on by default', ev(f"{d}.flowMode()") == 'single' and 'on' in pg.get_attribute('#modeSingle', 'class'))
    check('fix 3: Composite flow is not selectable on an empty canvas', pg.is_disabled('#modeComposite'))
    for t in ['api-to-process', 'process-to-publish', 'consume-to-api']:
        ev(f"{d}.append('{t}')")
    ev(f"{d}.recordHistory()")
    single_snapshot = ev(f"JSON.stringify({d}.serializeFlow())")
    check('single flow serialises without composite fields', 'branches' not in json.loads(single_snapshot))
    check('…selectable once the flow has a block', not pg.is_disabled('#modeComposite'))
    pg.click('#modeComposite')
    check('switching to Composite flow', ev(f"{d}.flowMode()") == 'composite')

    # ---- fix 2: nothing free to drop
    check('fix 2: with no connector picked, no library pattern is available', available() == [])
    check('…and the hint says to click a connector', pg.is_visible('#endHint') and 'click a Topic' in pg.inner_text('#endHintText'))
    check('queues are not clickable', pg.locator('#world .node.branchable[data-type="queue"]').count() == 0)

    # ---- fix 4: strict alternation on one connector (topic in the middle of the main flow)
    pick('block-2:out')
    check('topic picked: consumers and publishers fit, nothing else',
          sorted(available()) == sorted(['consume-to-process', 'consume-to-api', 'process-to-publish', 'api-to-publish']))
    ev(f"{d}.compositeAttach('consume-to-process')")
    check('1st branch on the topic goes below', branches()[0]['row'] > 0)
    # fix 1 (in line): the new branch's far end is picked; a process pattern extends it in line
    check('after adding, the new far-end connector is picked (process patterns fit)',
          'process-to-file' in available() and 'consume-to-api' not in available())
    ev(f"{d}.compositeAttach('process-to-file')")
    check('…and extends that branch in line (same row)', branches()[0]['blocks'] == ['consume-to-process', 'process-to-file'] and len(branches()) == 1)
    pick('block-2:out'); ev(f"{d}.compositeAttach('api-to-publish')")
    pick('block-2:out'); ev(f"{d}.compositeAttach('consume-to-api')")
    pick('block-2:out'); ev(f"{d}.compositeAttach('consume-to-process')")
    rows = [b['row'] for b in branches()]
    check('fix 4: branches of the topic alternate below / above / below / above', [r > 0 for r in rows] == [True, False, True, False])

    # ---- fix 1: blocks joined at a process stay one asset on one row
    pick('block-2:out'); ev(f"{d}.compositeAttach('process-to-publish')")
    p2p = branches()[-1]
    check('5th branch on the topic goes below again', p2p['row'] > 0 and p2p['kind'] == 'in')
    check('its open process start is picked: API-to-Process fits', 'api-to-process' in available())
    ev(f"{d}.compositeAttach('api-to-process')")
    b5 = branches()[-1]
    check('fix 1: API-to-Process joins that process in line, on the same row', b5['blocks'] == ['api-to-process', 'process-to-publish'] and len(branches()) == 5)
    # process reuse: a second block joins the main flow's process from another row
    pick('block-1:out')
    ev(f"{d}.compositeAttach('api-to-process')")
    check('process reuse goes on its own row', branches()[-1]['key'] == 'block-1:out' and branches()[-1]['kind'] == 'in')
    check("fix 1: the process's iPaaS container expands to take in the joined block (one outline)",
          ev("document.querySelectorAll('#world .container-layer path.pcont.own-ipaas').length") == 2)

    # ---- fix 5: calling applications on any API / file, alongside other flows
    callable_ = ev(f"{d}.callable()")
    check('fix 5: exposed API, target API and branch APIs all take calling applications',
          'block-1:in' in callable_ and 'block-3:out' in callable_ and all(f'{i}:in' in callable_ for i in ids_of('api-to-publish')))
    pick('block-1:in'); pg.click('#world .comp-card .dc-opt')      # a calling application on the exposed API
    pick('block-1:in')
    ev(f"{d}.compositeAttach('process-to-api')")     # another flow also calls it: multi-source branch
    check('with a caller on it, the exposed API is no open end: Process-to-API becomes a multi-source branch',
          branches()[-1]['key'] == 'block-1:in' and branches()[-1]['blocks'] == ['process-to-api'])
    pick('block-1:in')
    check('…and "Add calling application" is still offered', pg.is_visible('#world .comp-card') and 'Add calling application' in pg.inner_text('#world .comp-card'))
    pg.click('#world .comp-card .dc-opt')
    pick('block-3:out'); pg.click('#world .comp-card .dc-opt')
    cl = ev(f"{d}.callersList()")
    check('three calling applications added', len(cl) == 3)
    app_y = ev("[...document.querySelectorAll('#world .flow-layer .node[data-type=app]')].map(n=>n.transform.baseVal.consolidate().matrix.f)")
    api_y = ev("document.querySelector('#world .flow-layer .node[data-skey=\"block-3:out\"]').transform.baseVal.consolidate().matrix.f")
    check('a caller of the target API sits above / below it, clear of the tile on its left', any(abs(y - api_y) >= 130 for y in app_y))

    # ---- fix 6 / 7 and drawing
    check('fix 6: no "shared ×N" badges', ev("document.querySelectorAll('#world .sbadge').length") == 0)
    all_tops = sorted(set(ev("[...document.querySelectorAll('#world .cblock')].map(b=>parseFloat(b.style.top))")))
    t0 = ev(f"parseFloat({d}.chainOrder()[0].style.top)")
    check('fix 7: rows are 300 px apart', all((t - t0) % 300 == 0 for t in all_tops) and len(all_tops) >= 4)
    check('branch links are straight segments with bends', ev("[...document.querySelectorAll('#world .flow-layer path.link')].every(p => !/C/.test(p.getAttribute('d')))"))
    check('every arrowhead tip lies on its line', ev(f"({ON_LINE})('#world')"))
    if SHOT:
        pg.mouse.click(1450, 880); pg.click('#zoomOut'); pg.click('#zoomOut'); pg.click('#zoomOut')
        pg.screenshot(path=SHOT)
    check('no page errors so far', not errs)

    # ---- switching, saving, undo
    pg.click('#modeSingle')
    check('Single flow blocked while branches exist', ev(f"{d}.flowMode()") == 'composite')
    flow = ev(f"{d}.serializeFlow()")
    check('composite flow saves branches and callers', flow.get('mode') == 'composite' and len(flow['branches']) == 7 and len(flow['callers']) == 3)
    check('the saved file validates', ev(f"{d}.validateFlow({d}.serializeFlow())") is None)
    before = json.dumps(flow, sort_keys=True)
    ev(f"{d}.loadFlow({d}.serializeFlow())")
    check('load(save) reproduces the composite flow', before == json.dumps(ev(f"{d}.serializeFlow()"), sort_keys=True))
    ev(f"{d}.undo()")
    check('undo removes the last calling application', len(ev(f"{d}.callersList()")) == 2)

    # ---- removal rules
    far = [i for i, t in tpls() if t == 'process-to-file'][0]
    mid = [i for i, t in tpls() if t == 'consume-to-process'][0]
    n = len(tpls())
    ev(f"{d}.removeChainBlock(document.querySelector('[data-id=\"{mid}\"]'))")
    check('a branch block that is not at the far end is kept', len(tpls()) == n)
    ev(f"{d}.removeChainBlock(document.querySelector('[data-id=\"{far}\"]'))")
    check('the far-end block of a branch is removed', len(tpls()) == n - 1)

    # ---- fix 3: clearing the canvas returns to Single flow
    pg.click('#clearCanvas'); pg.click('#confirmOk')
    check('fix 3: clearing the canvas returns to Single flow', ev(f"{d}.flowMode()") == 'single' and pg.is_disabled('#modeComposite'))

    # ---- single flow is untouched
    ev(f"{d}.loadFlow({json.dumps(json.loads(single_snapshot))})")
    check('single flow round-trips exactly as before', ev(f"JSON.stringify({d}.serializeFlow())") == single_snapshot)
    ev(f"{d}.dropVersion('a2p-contract-parallel', 10, 10)"); pg.wait_for_timeout(150)
    pg.click('#tabVersioned'); pg.wait_for_timeout(150)
    check('single flow + versioned copy: every arrowhead tip lies on its (curved) link',
          ev(f"({ON_LINE})('#world')") and ev(f"({ON_LINE})('#vworld')") and ev("document.querySelectorAll('#vworld .link-arrow').length") > 3)
    check('no page errors', not errs)
    if errs: print(errs)
    br.close()

print(f"\n{sum(res)}/{len(res)} checks passed")
