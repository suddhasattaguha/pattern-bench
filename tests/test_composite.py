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

    # ---- the switch
    check('mode switch is shown above the canvas, Single flow on by default',
          pg.is_visible('#modeSingle') and 'on' in pg.get_attribute('#modeSingle', 'class') and ev(f"{d}.flowMode()") == 'single')
    for t in ['api-to-process', 'process-to-publish', 'consume-to-api']:
        ev(f"{d}.append('{t}')")
    ev(f"{d}.recordHistory()")
    single_snapshot = ev(f"JSON.stringify({d}.serializeFlow())")
    check('single flow serialises without composite fields', 'branches' not in json.loads(single_snapshot))
    check('single flow: connectors are not branch points', pg.locator('#world .node.branchable').count() == 0)

    pg.click('#modeComposite')
    check('switching to Composite flow', ev(f"{d}.flowMode()") == 'composite' and 'composite' in pg.get_attribute('#canvasWrap', 'class'))
    check('composite: topic / process / API nodes are branch points, queues are not',
          pg.locator('#world .node.branchable[data-type="topic"]').count() == 1 and
          pg.locator('#world .node.branchable[data-type="queue"]').count() == 0 and
          pg.locator('#world .node.branchable[data-type="process"]').count() == 1)

    # ---- fan-out at the topic
    pick('block-2:out')
    check('picking the topic marks it and shows the branching hint',
          pg.locator('#world .node.branch-point').count() == 1 and pg.is_visible('#endHint') and 'Topic' in pg.inner_text('#endHintText'))
    check('topic branch point: consumers and publishers fit, others do not',
          ev(f"{d}.isCompatible('consume-to-process')") and ev(f"{d}.isCompatible('api-to-publish')") and
          not ev(f"{d}.isCompatible('process-to-api')") and not ev(f"{d}.isCompatible('file-to-process')"))
    ev(f"{d}.compositeAttach('consume-to-process'); {d}.recordHistory()")
    b = branches()
    check('fan-out branch created below the main flow', len(b) == 1 and b[0]['kind'] == 'out' and b[0]['row'] == 1 and b[0]['key'] == 'block-2:out')
    check('the new branch end is selected: it extends with process patterns only',
          ev(f"{d}.isCompatible('process-to-file')") and not ev(f"{d}.isCompatible('consume-to-api')"))
    ev(f"{d}.compositeAttach('process-to-file'); {d}.recordHistory()")
    check('branch extended to the right', branches()[0]['blocks'] == ['consume-to-process', 'process-to-file'])
    check('topic shows as shared (3 links)', pg.locator('#world .sbadge').count() == 1 and 'shared ×3' in pg.text_content('#world .sbadge text'))
    check('the topic is drawn once (branch does not repeat it)', pg.locator('#world .node[data-type="topic"]').count() == 1)

    # ---- multi-source: a second publisher on the same topic
    pick('block-2:out')
    ev(f"{d}.compositeAttach('api-to-publish'); {d}.recordHistory()")
    b = branches()
    check('multi-source branch created above the main flow', b[1]['kind'] == 'in' and b[1]['row'] == -1)
    check('topic now shared ×4', 'shared ×4' in pg.text_content('#world .sbadge text'))

    # ---- multi-source on the target API (another caller)
    pick('block-3:out')
    check('target API: only callers fit (multi-source), no fan-out',
          ev(f"{d}.isCompatible('process-to-api')") and not ev(f"{d}.isCompatible('api-to-process')"))
    ev(f"{d}.compositeAttach('process-to-api'); {d}.recordHistory()")
    check('its branch extends to the left', ev(f"{d}.isCompatible('file-to-process')") and not ev(f"{d}.isCompatible('process-to-file')"))
    ev(f"{d}.compositeAttach('file-to-process'); {d}.recordHistory()")
    check('caller branch reads file → process → shared API', branches()[2]['blocks'] == ['file-to-process', 'process-to-api'] and branches()[2]['row'] == -2)

    # ---- process reuse: the main flow's process gets a second output
    pick('block-1:out')
    ev(f"{d}.compositeAttach('process-to-file'); {d}.recordHistory()")
    check('process reuse: fan-out from the process', branches()[3]['kind'] == 'out' and branches()[3]['key'] == 'block-1:out' and branches()[3]['row'] == 2)

    # ---- queue ↔ process is 1:1
    ids = ev("[...document.querySelectorAll('#world .cblock')].map(b=>[b.dataset.id,b.dataset.tpl])")
    c2p = [i for i, t in ids if t == 'consume-to-process'][0]
    pick(f'{c2p}:out')
    check('a process already fed by a queue cannot take a second Consume-to-Process',
          not ev(f"{d}.isCompatible('consume-to-process')") and ev(f"{d}.isCompatible('api-to-process')"))
    pg.mouse.click(1300, 860)
    check('clicking empty canvas clears the branch point', ev(f"{d}.branchPoint()") is None)

    # ---- layout: branch tiles sit on their rows, under the shared connector
    tops = ev("[...document.querySelectorAll('#world .cblock')].map(b=>parseFloat(b.style.top))")
    check('rows: main flow, two rows below, two above', sorted(set(tops)) == sorted({tops[0] - 400, tops[0] - 200, tops[0], tops[0] + 200, tops[0] + 400}))
    check('no page errors so far', not errs)
    if SHOT: pg.screenshot(path=SHOT)

    # ---- switching back is blocked while branches exist
    pg.click('#modeSingle')
    check('Single flow is blocked while branches exist', ev(f"{d}.flowMode()") == 'composite' and 'Remove the branches' in pg.inner_text('#toast'))

    # ---- removal rules
    n_before = len(branches())
    middle = [i for i, t in ids if t == 'consume-to-process'][0]
    ev(f"{d}.removeChainBlock(document.querySelector('[data-id=\"{middle}\"]'))")
    check('a branch block that is not the far end is not removed', len(ev("document.querySelectorAll('#world .cblock')")) == len(ids))
    first = ev(f"{d}.chainOrder()[0].dataset.id")
    ev(f"{d}.removeChainBlock({d}.chainOrder()[0])")
    check('the main flow start keeps its process branch (it hangs on the seam)', ev(f"{d}.chainOrder().length") == 2 and len(branches()) == n_before)

    # ---- history and export round-trip
    flow = ev(f"{d}.serializeFlow()")
    check('composite flow serialises its branches', flow.get('mode') == 'composite' and len(flow['branches']) == 4)
    check('the serialised file validates', ev(f"{d}.validateFlow({d}.serializeFlow())") is None)
    before = json.dumps(flow, sort_keys=True)
    ev(f"{d}.loadFlow({d}.serializeFlow())")
    after = json.dumps(ev(f"{d}.serializeFlow()"), sort_keys=True)
    check('load(serialize) reproduces the composite flow', before == after)
    ev(f"{d}.undo()")
    check('undo restores the removed main-flow block with its branches', ev(f"{d}.chainOrder().length") == 3 and len(branches()) == 4)
    for _ in range(12):
        if not branches(): break
        ev(f"{d}.undo()")
    check('undo back past the first branch leaves no branches', len(branches()) == 0)
    pg.click('#modeSingle')
    check('with no branches, switching back to Single flow works', ev(f"{d}.flowMode()") == 'single')
    check('single flow is identical to before composite mode', ev(f"JSON.stringify({d}.serializeFlow())") == single_snapshot)
    check('no page errors', not errs)
    if errs: print(errs)
    br.close()

print(f"\n{sum(res)}/{len(res)} checks passed")
