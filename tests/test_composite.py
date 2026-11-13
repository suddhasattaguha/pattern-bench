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
    check('process reuse: fan-out from the process', branches()[3]['kind'] == 'out' and branches()[3]['key'] == 'block-1:out' and branches()[3]['row'] > 0)

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

    # ---- links: straight segments with bends, and every arrowhead sits on its line
    check('branch links are drawn as straight segments with bends (no free curves)',
          ev("[...document.querySelectorAll('#world .flow-layer path.link')].every(p => !/C/.test(p.getAttribute('d')))"))
    ON_LINE = """(sel) => [...document.querySelectorAll(sel + ' .flow-layer .link-arrow')].every(a => {
        const m = /^M([-\\d.]+) ([-\\d.]+)/.exec(a.getAttribute('d')); const pt = new DOMPoint(+m[1], +m[2]);
        return [...a.ownerSVGElement.querySelectorAll('.link')].some(l => l.isPointInStroke(pt)); })"""
    check('every arrowhead tip lies on a link (composite)', ev(f"({ON_LINE})('#world')"))

    # ---- rows are packed so drop lines don't run through another branch's tiles
    clear = ev("""(()=>{
      const tiles=[...document.querySelectorAll('#world .cblock')].map(b=>({x1:parseFloat(b.style.left),x2:parseFloat(b.style.left)+parseFloat(b.style.width)+20,y1:parseFloat(b.style.top),y2:parseFloat(b.style.top)+120,id:b.dataset.id}));
      const segs=[];
      document.querySelectorAll('#world .flow-layer path.link').forEach(p=>{ const nums=[...p.getAttribute('d').matchAll(/[ML]([-\\d.]+) ([-\\d.]+)/g)].map(m=>[+m[1],+m[2]]); for(let i=1;i<nums.length;i++) if(Math.abs(nums[i][0]-nums[i-1][0])<0.5 && Math.abs(nums[i][1]-nums[i-1][1])>150) segs.push([nums[i][0],Math.min(nums[i][1],nums[i-1][1]),Math.max(nums[i][1],nums[i-1][1])]); });
      // a long vertical segment may cross its own start row (main flow) but no other row's tiles
      const top0=parseFloat(document.querySelector('#world .cblock').style.top);
      return segs.every(([x,y1,y2])=>tiles.every(t=>t.y1===top0 || !(t.x1<x && x<t.x2 && t.y1<y2-60 && t.y2>y1+60)));
    })()""")
    check('no drop line runs through a branch row it does not belong to', clear)

    # ---- multi-source links arrive level with the connector (like callers), not from above
    level_in = ev("""(()=>{
      const out=[]; document.querySelectorAll('#world .flow-layer path.link').forEach(p=>{
        const n=[...p.getAttribute('d').matchAll(/[MLQ]([-\\d.]+) ([-\\d.]+)/g)].map(m=>[+m[1],+m[2]]);
        const a=n[n.length-2], z=n[n.length-1]; if(n.length>3) out.push(Math.abs(a[1]-z[1])<0.5 || Math.abs(a[0]-z[0])<0.5 && z[1]>a[1]===false);
      }); return out; })()""")
    check('bent links end with a level segment into the receiving symbol', all(level_in))

    # ---- calling applications on any upstream API / file
    callable_ = ev(f"{d}.callable()")
    check('the exposed API at the start of the main flow can take a calling application', 'block-1:in' in callable_)
    apub = [i for i, t in ev("[...document.querySelectorAll('#world .cblock')].map(b=>[b.dataset.id,b.dataset.tpl])") if t == 'api-to-publish'][0]
    check("a branch starting with an API can take one too", f'{apub}:in' in callable_)
    check('a shared target API (fed by processes) cannot', 'block-3:out' not in callable_)
    pick('block-1:in')
    check('picking that API shows the card with "Add calling application"', pg.is_visible('#world .comp-card') and 'Add calling application' in pg.inner_text('#world .comp-card'))
    pg.click('#world .comp-card .dc-opt')
    pick('block-1:in'); pg.click('#world .comp-card .dc-opt')
    pick(f'{apub}:in'); pg.click('#world .comp-card .dc-opt')
    cl = ev(f"{d}.callersList()")
    check('three calling applications: two on the main API, one on the branch API',
          len(cl) == 3 and sum(c['key'] == 'block-1:in' for c in cl) == 2 and sum(c['key'] == f'{apub}:in' for c in cl) == 1)
    ys = ev("[...document.querySelectorAll('#world .flow-layer .node[data-type=app]')].map(n=>n.transform.baseVal.consolidate().matrix.f)")
    check('two callers of the same API are stacked, not on top of each other', len(set(round(y) for y in ys)) == 3)
    check('the main API is now shared ×3', any('×3' in t for t in ev("[...document.querySelectorAll('#world .sbadge text')].map(t=>t.textContent)")))
    check('arrowheads still on their lines', ev(f"({ON_LINE})('#world')"))
    if SHOT: pg.screenshot(path=SHOT)
    first_app = ev("document.querySelector('#world .flow-layer .node[data-type=app]').dataset.skey")
    pg.locator(f'#world .flow-layer .node[data-skey="{first_app}"]').click(force=True)
    check('clicking a calling application offers to remove it', 'Remove this calling application' in pg.inner_text('#world .comp-card'))
    pg.click('#world .comp-card .dc-opt')
    check('…and removes it', len(ev(f"{d}.callersList()")) == 2)
    rt = ev(f"{d}.serializeFlow()")
    check('added calling applications are saved', len(rt.get('callers', [])) == 2 and ev(f"{d}.validateFlow({d}.serializeFlow())") is None)
    ev(f"{d}.loadFlow({d}.serializeFlow())")
    check('…and come back on load', len(ev(f"{d}.callersList()")) == 2)
    ev(f"{d}.undo()")
    check('undo brings the removed caller back', len(ev(f"{d}.callersList()")) == 3)
    ev(f"{d}.removeCaller(...[{d}.callersList()[0].id])"); ev(f"{d}.removeCaller({d}.callersList()[0].id)"); ev(f"{d}.removeCaller({d}.callersList()[0].id)")
    check('callers removed again', len(ev(f"{d}.callersList()")) == 0)

    # ---- switching back is blocked while branches exist
    pg.click('#modeSingle')
    check('Single flow is blocked while branches exist', ev(f"{d}.flowMode()") == 'composite' and 'Remove the branches' in pg.inner_text('#toast'))

    # ---- removal rules
    n_before = len(branches())
    ids = ev("[...document.querySelectorAll('#world .cblock')].map(b=>[b.dataset.id,b.dataset.tpl])")
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
    ev(f"{d}.dropVersion('a2p-contract-parallel', 10, 10)"); pg.wait_for_timeout(150)
    pg.click('#tabVersioned'); pg.wait_for_timeout(150)
    check('single flow + versioned copy: every arrowhead tip lies on its (curved) link',
          ev(f"({ON_LINE})('#world')") and ev(f"({ON_LINE})('#vworld')") and ev("document.querySelectorAll('#vworld .link-arrow').length") > 3)
    check('no page errors', not errs)
    if errs: print(errs)

    # ---- balance: branches of one connector on the main flow alternate below / above
    pg.goto(URL)
    for t in ['file-to-process', 'process-to-api']: ev(f"{d}.append('{t}')")
    ev(f"{d}.setFlowMode('composite')")
    rows_ = []
    for _ in range(4):
        pick('block-1:out'); ev(f"{d}.compositeAttach('process-to-api')"); rows_.append(branches()[-1]['row'])
    check('four fan-outs from one process alternate below / above (1, -1, 2, -2)', rows_ == [1, -1, 2, -2])
    pick('block-1:in'); pg.click('#world .comp-card .dc-opt')
    pick('block-1:in'); ev(f"{d}.compositeAttach('process-to-file')")
    app_x = ev("document.querySelector('#world .flow-layer .node[data-type=app]').transform.baseVal.consolidate().matrix.e")
    file_x = ev("document.querySelector('#world .flow-layer .node[data-skey=\"block-1:in\"]').transform.baseVal.consolidate().matrix.e")
    check('a file with a multi-source writer pushes its calling application further left', file_x - app_x > 150)
    check('no page errors (balance)', not errs)
    br.close()

print(f"\n{sum(res)}/{len(res)} checks passed")
