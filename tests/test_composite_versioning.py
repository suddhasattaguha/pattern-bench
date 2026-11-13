"""Pattern Bench 2.0 — versioning on the composite flow (Python Playwright).
Run: python3 tests/test_composite_versioning.py"""
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
    return [...a.ownerSVGElement.querySelectorAll('.link')].some(l => { const s = l.style.strokeDasharray; l.style.strokeDasharray = 'none'; const ok = l.isPointInStroke(pt); l.style.strokeDasharray = s; return ok; }); })"""

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1500, 'height': 900})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL)
    ev = pg.evaluate
    d = "window.__debug"
    def pick(skey, pane='#world'):
        pg.locator(f'{pane} .flow-layer .node[data-skey="{skey}"]').first.click(force=True)
    tpls = lambda: ev("[...document.querySelectorAll('#world .cblock')].map(b=>[b.dataset.id,b.dataset.tpl])")
    def id_of(t, k=0): return [i for i, x in tpls() if x == t][k]
    visible_versions = lambda: ev("[...document.querySelectorAll('#versionGrid .version-card')].filter(c=>!c.classList.contains('off-flow') && getComputedStyle(c).display!=='none').map(c=>c.dataset.variant || c.title)")
    decisions = lambda: ev(f"{d}.compositeDecisions()")

    # ---- a composite flow: main flow + two fan-outs at the topic + process reuse
    for t in ['api-to-process', 'process-to-publish', 'consume-to-api']:
        ev(f"{d}.append('{t}')")
    pg.click('#modeComposite')
    pick('block-2:out'); ev(f"{d}.compositeAttach('consume-to-process')"); ev(f"{d}.compositeAttach('process-to-file')")
    pick('block-2:out'); ev(f"{d}.compositeAttach('consume-to-api')")
    pick('block-1:out'); ev(f"{d}.compositeAttach('process-to-api')")
    ev(f"{d}.recordHistory()")
    b4, b5, b6, b7 = id_of('consume-to-process'), id_of('process-to-file'), id_of('consume-to-api', 1), id_of('process-to-api')
    n_blocks = len(tpls())
    check('setup: composite flow with 7 blocks', n_blocks == 7 and len(ev(f"{d}.branches()")) == 3)

    # ---- step 3: library gating and selecting a component
    pg.click('#tabVersioned'); pg.wait_for_timeout(100)
    check('versioning: no version card is available until a component is selected', visible_versions() == [])
    check('…the hint says to click a component', pg.is_visible('#endHint') and 'click a component' in pg.inner_text('#endHintText'))
    pick('block-2:out')
    blocks_at = ev(f"{d}.versionTarget().blocks")
    check('selecting the topic selects every block touching it on any row (publisher + 3 consumers)',
          sorted(blocks_at) == sorted(['block-2', 'block-3', b4, b6]))
    vv = visible_versions()
    check('…the library shows only versions that change the topic', len(vv) > 0 and all(
        ev(f"{d}.variantsById['{v}'] && {d}.variantsById['{v}'].nodes.some(n=>n.type==='topic' && n.ver!=='v1')") for v in vv))
    card = pg.inner_text('#world .target-card').lower()
    check('the target card lists the touching blocks with their side and row', 'upstream' in card and 'downstream' in card and 'branch' in card and 'main flow' in card)

    # ---- step 1/2/4: a switch on the shared topic
    ev(f"{d}.dropVersion('p2t-contract-switch', 10, 10)"); pg.wait_for_timeout(150)
    check('the version lands on the publisher', ev(f"{d}.versionOverrides()['block-2']") == 'p2t-contract-switch')
    copy = ev("[...document.querySelectorAll('#vworld .cblock')].map(b=>({id:b.dataset.baseId,l:parseFloat(b.style.left),t:parseFloat(b.style.top),w:parseFloat(b.style.width),h:parseFloat(b.style.height)}))")
    check('step 2: the versioned copy shows the whole composite flow (all 7 blocks)', len(copy) == n_blocks)
    vt = [c for c in copy if c['id'] == 'block-2'][0]
    check('…the versioned block is full height (220 px)', vt['h'] == 220)
    rowc = lambda c: c['t'] + c['h'] / 2
    over = [(a['id'], b['id']) for i, a in enumerate(copy) for b in copy[i+1:]
            if rowc(a) != rowc(b) and a['l'] < b['l'] + b['w'] + 20 and b['l'] < a['l'] + a['w'] + 20 and a['t'] < b['t'] + b['h'] and b['t'] < a['t'] + a['h']]
    check('step 1: no copy tiles overlap', not over)
    base_b4 = ev(f"parseFloat(document.querySelector('#world [data-id=\"{b4}\"]').style.top) - parseFloat({d}.chainOrder()[0].style.top)")
    copy_b4 = [c for c in copy if c['id'] == b4][0]['t'] - [c for c in copy if c['id'] == 'block-1'][0]['t']
    check('step 1: the taller main-flow row pushes the branch row below it further away', copy_b4 > base_b4)
    ds = [x for x in decisions() if x.get('type') == 'topic']
    check('step 4: a switch asks the in-row consumer and both fan-out consumers (3 cards)',
          sorted(x['blockId'] for x in ds) == sorted(['block-3', b4, b6]) and all(x['count'] == 3 for x in ds))
    check('…each card says how many flows are affected', ev("[...document.querySelectorAll('#vworld .decision-card .dc-count')].length") == 3 and
          '3 flows are affected' in pg.inner_text('#vworld .decision-card .dc-count'))
    check('…the affected component in each block is highlighted', ev("document.querySelectorAll('#vworld .flow-layer .node.affected').length") >= 3)
    check('…those blocks are marked pending', all(ev(f"!!document.querySelector('#vworld .cblock.pending[data-base-id=\"{i}\"]')") for i in ['block-3', b4, b6]))
    n_cards = ev("document.querySelectorAll('#vworld .decision-card:not(.target-card)').length")
    pg.locator('#vworld .decision-card [data-action=later]').first.click()
    check('a card can be minimized to a pending pill', ev("document.querySelectorAll('#vworld .decision-pill').length") == 1)
    pg.locator('#vworld .decision-pill').first.click()
    check('…and opened again', ev("document.querySelectorAll('#vworld .decision-pill').length") == 0 and ev("document.querySelectorAll('#vworld .decision-card:not(.target-card)').length") == n_cards)
    check('arrowheads in the copy sit on their lines', ev(f"({ON_LINE})('#vworld')"))
    check('the small window shows the whole base composite flow', ev("document.querySelectorAll('#miniStage .cblock').length") == n_blocks)
    if SHOT:
        pg.click('#zoomOut'); pg.click('#zoomOut'); pg.wait_for_timeout(100); pg.screenshot(path=SHOT)

    # ---- decision (d): a parallel topic version only asks the in-row neighbour
    ev(f"{d}.removeVersion('block-2')")
    pick('block-2:out', '#vworld') if ev("document.querySelector('#vworld .node')") else pick('block-2:out')
    ev(f"{d}.dropVersion('p2t-contract-parallel', 10, 10)"); pg.wait_for_timeout(100)
    ds = [x for x in decisions() if x.get('type') == 'topic']
    check('decision (d): a parallel version leaves the other branches on v1 — only the in-row consumer is asked',
          [x['blockId'] for x in ds] == ['block-3'])
    ev(f"{d}.removeVersion('block-2')")

    # ---- versioning a block on a branch
    pick(f'{b7}:out')
    check('a branch component can be selected', ev(f"{d}.versionTarget().blocks") == [b7])
    ev(f"{d}.dropVersion('p2a-contract-switch', 10, 10)"); pg.wait_for_timeout(100)
    check('a version applies to a branch block', ev(f"{d}.versionOverrides()['{b7}']") == 'p2a-contract-switch')
    t7 = ev(f"(()=>{{const b=document.querySelector('#vworld [data-base-id=\"{b7}\"]'); return parseFloat(b.style.height)}})()")
    check('…drawn full height in the copy', t7 == 220)
    flow = ev(f"{d}.serializeFlow()")
    check('branch versions are saved', flow.get('branchVersions') == [{'ref': 'b2.0', 'variant': 'p2a-contract-switch'}] and ev(f"{d}.validateFlow({d}.serializeFlow())") is None)
    ev(f"{d}.removeVersion('{b7}')")

    # ---- step 4b: contract ripple across branches (shared main-flow process, two paths)
    pick('block-1:in')
    ev(f"{d}.dropVersion('a2p-contract-shared', 10, 10)"); pg.wait_for_timeout(100)
    asks = [a for a in ev(f"{d}.compositeRipples()")['asks']]
    check('4b: the contract change reaches the shared process on both paths (main flow + process reuse)',
          sorted(a['blockId'] for a in asks) == sorted(['block-2', b7]) and all(a['count'] == 2 for a in asks))
    check('…one absorb / pass-on card per path', ev("document.querySelectorAll('#vworld .decision-card.ripple-card').length") == 2)
    ev(f"{d}.setRipple('block-1>block-2', {{ choice:'absorb', code:null }})")
    ev(f"{d}.setRipple('block-1>{b7}', {{ choice:'pass', code:null }})")
    ev(f"{d}.setRipple('block-1>{b7}', {{ code:false }})"); pg.wait_for_timeout(100)
    r = ev(f"{d}.compositeRipples()")
    check('…each path decides on its own: absorbed on the main flow, passed on along the branch',
          all(a['resolved'] for a in r['asks']) and r['absorbed'].get('block-1:out') == ['block-2'])
    check('…v1 Δ on the shared process', ev("document.querySelectorAll('#vworld .flow-layer .dbadge').length") >= 1)
    check('…passed on along the branch to an end application API: ⚠ dependent logic there', ev("document.querySelectorAll('#vworld .flow-layer .ibadge').length") == 1 and ev(f"!!document.querySelector('#vworld .flow-layer .node.impact[data-skey=\"{b7}:out\"]')"))
    flow = ev(f"{d}.serializeFlow()")
    check('ripple answers per path are saved', len(flow.get('compositeRipples', [])) == 2 and ev(f"{d}.validateFlow({d}.serializeFlow())") is None)
    before = json.dumps(flow, sort_keys=True)
    ev(f"{d}.loadFlow({d}.serializeFlow())"); pg.wait_for_timeout(100)
    check('load(save) reproduces versions and ripple answers', before == json.dumps(ev(f"{d}.serializeFlow()"), sort_keys=True))
    ev(f"{d}.undo()")
    check('undo steps back through the ripple answers', not all(a['resolved'] for a in ev(f"{d}.compositeRipples()")['asks']))
    check('no page errors', not errs)
    if errs: print(errs)
    br.close()

print(f"\n{sum(res)}/{len(res)} checks passed")
