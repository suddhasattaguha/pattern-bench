"""Pattern Bench 2.0 — round 7 (Test Defect Notes v2, round 7, 15 Nov) (Python Playwright).
Run: python3 tests/test_round7.py   (PB_SHOT=dir saves screenshots)"""
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
    pg = br.new_page(viewport={'width': 2000, 'height': 1300})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    ev = pg.evaluate
    d = "window.__debug"
    def shot(name):
        if SHOT: os.makedirs(SHOT, exist_ok=True); pg.screenshot(path=os.path.join(SHOT, name + '.png'))
    def node(skey, pane='#world', role=None):
        sel = f'{pane} .flow-layer .node[data-skey="{skey}"]' + (f'.role-{role}' if role else '')
        return pg.locator(sel).first
    def click_node(skey, pane='#world', role=None):
        node(skey, pane, role).click(force=True); pg.wait_for_timeout(80)
    def fresh(main):
        pg.goto(URL); pg.wait_for_timeout(100)
        for t in main: ev(f"{d}.append('{t}')")
        pg.click('#modeComposite'); pg.wait_for_timeout(50)
    def add_caller(skey):
        click_node(skey); pg.click('#world .comp-card .dc-opt'); pg.mouse.click(1900, 1250)
    def toast(): return pg.text_content('#toast') or ''
    def tog(t):
        ev(f"document.querySelector('#vworld .link-hit[data-tog=\"{t}\"]').dispatchEvent(new MouseEvent('click', {{bubbles:true}}))"); pg.wait_for_timeout(100)
    def tiles(pane='#vworld'):
        return ev(f"[...document.querySelectorAll('{pane} > .cblock')].filter(b=>b.style.display!=='none').map(b=>[parseFloat(b.style.left), parseFloat(b.style.top), parseFloat(b.style.left)+parseFloat(b.style.width)+20, parseFloat(b.style.top)+parseFloat(b.style.height)])")
    def caller_boxes(pane='#vworld'):
        return ev(f"[...document.querySelectorAll('{pane} .container-layer rect.pcont')].map(r=>r.getBBox()).filter(b=>b.width===150&&b.height===120).map(b=>[b.x, b.y, b.x+b.width, b.y+b.height])")
    inter = lambda a, b: a[0] < b[2] - 2 and b[0] < a[2] - 2 and a[1] < b[3] - 2 and b[1] < a[3] - 2

    # ================= A: callers on a versioned API (notes 1, 2, 3, 4, 9) =================
    fresh(['api-to-process', 'process-to-publish', 'consume-to-api'])
    add_caller('block-1:in'); add_caller('block-1:in')
    pg.click('#tabVersioned')
    click_node('block-1:out')
    check('setup: the process has two connectors', len(ev(f"{d}.versionTarget().conns")) == 2)
    pg.click('#world .target-card .dc-side button[data-side=upstream]')
    ev(f"{d}.dropVersion('a2p-process-parallel', 10, 10)"); pg.wait_for_timeout(150)
    check('setup: API-to-Process gets New Process v2 · own API v2', ev(f"{d}.versionOverrides()['block-1']") == 'a2p-process-parallel')
    # note 9 / 11: every v2 component is drawn solid
    dash = ev("[...document.querySelectorAll('#vworld .node.role-side .n-shape, #vworld .node.role-primary .n-shape')].map(s=>getComputedStyle(s).strokeDasharray)")
    check('note 9 / 11: every v2 component is drawn solid (no dashed outline)', dash and all(x in ('none', '') for x in dash))
    check('…and so is its v2 badge', all(x in ('none', '') for x in ev("[...document.querySelectorAll('#vworld .vbadge.role-side rect')].map(r=>getComputedStyle(r).strokeDasharray)")))
    check('…the legend shows the side-effect as a solid outline', ev("!document.querySelector('.version-legend').innerHTML.includes('stroke-dasharray=\"3 2\"')"))
    # note 1: a caller moved to API v2 is flagged
    cids = [c['id'] for c in ev(f"{d}.callersList()")]
    tog(f'caller|{cids[0]}|v2'); tog(f'caller|{cids[0]}|v1')
    check('setup: the first caller is on v2', ev(f"{d}.serializeFlow().callerVer") == [{'caller': 0, 'ver': 'v2'}])
    check('note 1: the caller on API v2 gets "⚠ calls new version" (probable change in the calling application)',
          ev("document.querySelectorAll('#vworld .ibadge.adopt').length") == 1 and 'calls new version' in pg.text_content('#vworld .ibadge.adopt'))
    pg.locator('#vworld .ibadge.adopt').click(); pg.wait_for_timeout(80)
    check('…it can be acknowledged like the other ⚠ markers', pg.locator('#vworld .warn-card [data-action=ack]').count() == 1)
    pg.click('#vworld .warn-card [data-action=ack]'); pg.wait_for_timeout(80)
    check('…acknowledged (grey ✓) and saved', ev("document.querySelector('#vworld .ibadge.adopt').classList.contains('acked')")
          and any(a['id'].startswith('impact|@c') for a in ev(f"{d}.serializeFlow()").get('acks', [])))
    shot('r7-callers-v2')
    # note 2: a v2 component can't be versioned
    click_node('block-1:in', '#vworld', 'side')
    check('note 2: clicking API v2 opens no versioning card', ev(f"{d}.versionTarget()") is None and pg.locator('#vworld .target-card').count() == 0)
    check('…and says why', 'can’t be versioned again' in toast())
    click_node('block-1:out', '#vworld', 'primary')
    check('note 2: same for Process v2', ev(f"{d}.versionTarget()") is None)
    # note 3: a component already versioned on a connector — that connector is locked
    click_node('block-1:out', '#vworld', 'unchanged')
    vt = ev(f"{d}.versionTarget()")
    check('note 3: the process v1 — the versioned block\'s connector is locked, only the other one is offered',
          vt and [c['own'] for c in vt['conns'] if c.get('locked')] == ['block-1'] and vt['conn'] == 'block-2')
    ev(f"{d}.dropVersion('p2t-contract-parallel', 10, 10)"); pg.wait_for_timeout(150)
    click_node('block-1:out', '#vworld', 'unchanged')
    check('note 3: once every connector is versioned, no further versioning on that node', ev(f"{d}.versionTarget()") is None
          and 'remove that version' in toast())
    r = ev("(()=>{const b=document.querySelector('#vworld .cblock[data-base-id=\"block-1\"]').getBoundingClientRect(); return [b.x+b.width/2, b.y+b.height/2]})()")
    ev(f"{d}.dropVersion('a2p-contract-parallel', {r[0]}, {r[1]})"); pg.wait_for_timeout(100)
    check('note 3: dropping another version onto a versioned block is refused (remove it with × first)',
          ev(f"{d}.versionOverrides()['block-1']") == 'a2p-process-parallel' and 'already has a version' in toast())
    ev(f"{d}.removeVersion('block-1')"); pg.wait_for_timeout(100)
    click_node('block-1:out', '#vworld')
    vt = ev(f"{d}.versionTarget()")
    check('…after × it can be versioned again', vt and not any(c.get('locked') and c['own'] == 'block-1' for c in vt['conns']))
    pg.mouse.click(1900, 1250)
    # note 4: single-component platforms are framed wide enough
    W = lambda pane: ev(f"[...document.querySelectorAll('{pane} .container-layer .pcont')].map(r=>r.getBBox()).filter(b=>!(b.width===150&&b.height===120)).map(b=>b.width)")
    check('note 4: every platform frame is at least 160 px wide (room for its name)', W('#vworld') and min(W('#vworld')) >= 159)
    check('…also in the base flow', W('#world') and min(W('#world')) >= 159)

    # ================= B: Consume-to-API next steps (notes 5, 6) =================
    fresh(['process-to-publish', 'consume-to-api'])
    pg.click('#modeComposite') if False else None
    click_node('block-1:out'); pg.click('#world .comp-card .dc-opt') if pg.locator('#world .comp-card .dc-opt').count() and False else None
    pg.mouse.click(1900, 1250)
    pg.click('#tabVersioned')
    names = ev("[...document.querySelectorAll('#versionGrid .version-card')].map(c=>c.dataset.variant)")
    check('note 5: the library has "two topics – two queues – two APIs" and "two topics – two APIs, queue switches"',
          'c2a-topic-api-parallel' in names and 'c2a-topic-api-switch' in names)
    ev(f"{d}.dropVersion('c2a-topic-api-parallel', 10, 10)"); pg.wait_for_timeout(80)
    check('note 5: they build on a target-API version — refused on a plain Consume-to-API', not ev(f"{d}.versionOverrides()").get('block-2'))
    click_node('block-2:out')
    check('setup: the target API has one connector (picked)', ev(f"{d}.versionTarget().conn") == 'block-2')
    check('note 5: a plain Consume-to-API isn\'t offered the next steps', 'c2a-topic-api-parallel' not in ev(f"{d}.targetOptions()"))
    ev(f"{d}.dropVersion('c2a-api-parallel', 10, 10)"); pg.wait_for_timeout(150)
    click_node('block-1:out', '#vworld')
    pg.click('#vworld .target-card .dc-side button[data-side=downstream]'); pg.wait_for_timeout(80)
    vt = ev(f"{d}.versionTarget()")
    check('note 6: versioning the topic on that consumer — its connector is picked as one unit', vt['conn'] == 'block-2')
    check('note 6: …and the only option is two topics – two queues – two APIs', ev(f"{d}.targetOptions()") == ['c2a-topic-api-parallel'])
    pg.click('#vworld .target-card [data-action=other]') if pg.locator('#vworld .target-card [data-action=other]').count() else None
    owns = ev("[...document.querySelectorAll('#vworld .flow-layer .link-hit.pickable')].map(h=>h.dataset.own)")
    check('note 6: both of the block\'s lines at the topic are highlighted as one connector (same owner)', owns.count('block-2') == 2)
    ev("document.querySelectorAll('#vworld .flow-layer .link-hit.pickable[data-own=\"block-2\"]')[1].dispatchEvent(new MouseEvent('click', {bubbles:true}))"); pg.wait_for_timeout(80)
    check('…clicking either one gives the same options', ev(f"{d}.targetOptions()") == ['c2a-topic-api-parallel'])
    ev(f"{d}.dropVersion('c2a-topic-api-parallel', 10, 10)"); pg.wait_for_timeout(150)
    check('note 6: applied as the next step of the API version', ev(f"{d}.versionOverrides()['block-2']") == 'c2a-topic-api-parallel')
    cnt = lambda t: ev(f"document.querySelectorAll('#vworld .flow-layer .node[data-type={t}][data-blocks*=\"block-2\"]').length")
    check('…two topics, two queues, two APIs', cnt('topic') == 2 and cnt('queue') == 2 and cnt('api') == 2)
    shot('r7-c2a-next')
    ev(f"{d}.removeVersion('block-2')")
    click_node('block-2:out'); ev(f"{d}.dropVersion('c2a-api-switch', 10, 10)"); pg.wait_for_timeout(120)
    click_node('block-1:out', '#vworld'); pg.click('#vworld .target-card .dc-side button[data-side=downstream]'); pg.wait_for_timeout(80)
    check('note 5: after "push switches" the next step is two topics – two APIs with the queue switching', ev(f"{d}.targetOptions()") == ['c2a-topic-api-switch'])
    ev(f"{d}.dropVersion('c2a-topic-api-switch', 10, 10)"); pg.wait_for_timeout(150)
    lk = ev("[...document.querySelectorAll('#vworld .flow-layer path.link[data-own=\"block-2\"]')].map(l=>(l.classList.contains('retired')?'d':'s'))")
    check('…one queue: Topic v2 → queue → API v2 solid, the v1 links dotted', sorted(lk) == ['d', 'd', 's', 's'] and cnt('queue') == 1)
    f = ev(f"{d}.serializeFlow()")
    check('…saves and loads', ev(f"{d}.validateFlow({json.dumps(f)})") is None)
    ev(f"{d}.loadFlow({json.dumps(f)})"); pg.wait_for_timeout(100)
    check('…restored', list(ev(f"{d}.versionOverrides()").values()) == ['c2a-topic-api-switch'])

    # ================= C: API-to-API versioning + caller on the middle API (notes 7, 8) =================
    fresh(['api-to-process', 'process-to-api', 'api-to-api'])
    add_caller('block-2:out')
    pg.click('#tabVersioned')
    click_node('block-3:out'); ev(f"{d}.dropVersion('a2a-own-backend', 10, 10)"); pg.wait_for_timeout(150)
    l3 = ev("[...document.querySelectorAll('#vworld .flow-layer path.link[data-own=\"block-3\"], #vworld .flow-layer line.link[data-own=\"block-3\"]')].map(l=>[l.dataset.k1,l.dataset.k2])")
    check('note 7: API-to-API v2 draws front API → backend API (no loops back to the front API)',
          len(l3) == 2 and all(a == 'block-2:out' and b == 'block-3:out' for a, b in l3))
    check('note 7: the process reaches front API v1 and v2 with one line each (no doubled lines)',
          ev("document.querySelectorAll('#vworld .flow-layer path.link[data-own=\"block-2\"], #vworld .flow-layer line.link[data-own=\"block-2\"]').length") == 2)
    arrows = ev("document.querySelectorAll('#vworld .flow-layer path.link-arrow').length")
    links_n = ev("document.querySelectorAll('#vworld .flow-layer path.link, #vworld .flow-layer line.link').length")
    check('note 7: every connector has its arrowhead', arrows == links_n)
    check('note 8: the caller box clears every tile (the taller versioned row makes room)', not any(inter(c, t) for c in caller_boxes() for t in tiles()))
    shot('r7-a2a')
    # image 6: a version on the upstream process, caller on the middle API
    fresh(['api-to-process', 'process-to-api', 'api-to-api'])
    add_caller('block-1:in'); add_caller('block-2:out')
    pg.click('#tabVersioned')
    click_node('block-1:out'); pg.click('#world .target-card .dc-side button[data-side=upstream]')
    ev(f"{d}.dropVersion('a2p-process-parallel', 10, 10)"); pg.wait_for_timeout(150)
    click_node('block-3:out'); ev(f"{d}.dropVersion('a2a-own-backend', 10, 10)"); pg.wait_for_timeout(150)
    check('note 8: with a version on the upstream process the callers still clear every tile', not any(inter(c, t) for c in caller_boxes() for t in tiles()))
    check('…and in the base flow', not any(inter(c, t) for c in caller_boxes('#world') for t in tiles('#world')))
    shot('r7-upstream-version')

    # ================= D: a change on the caller (note 10) =================
    fresh(['api-to-process', 'process-to-publish'])
    add_caller('block-1:in')
    pg.click('#tabVersioned')
    cid = ev(f"{d}.callersList()")[0]['id']
    click_node('xc|' + cid)
    check('note 10: clicking a calling application in versioning opens "Change in the calling application"',
          pg.locator('#world .cchange-card').count() == 1 and pg.locator('#world .cchange-card [data-change]').count() == 2)
    pg.click('#world .cchange-card [data-change=minor]'); pg.wait_for_timeout(100)
    check('note 10: non-breaking → Δ on the caller, no decision', ev("document.querySelectorAll('#vworld .cbadge:not(.breaking)').length") == 1
          and not ev(f"{d}.compositeDecisions()"))
    click_node('xc|' + cid, '#vworld')
    pg.click('#vworld .cchange-card [data-change=breaking]'); pg.wait_for_timeout(100)
    ds = ev(f"{d}.compositeDecisions()")
    check('note 10: breaking → the API it calls is flagged for a version decision', len(ds) == 1 and ds[0]['blockId'] == 'block-1' and ds[0].get('callerId') == cid
          and 'a2p-contract-parallel' in ds[0]['options'])
    check('…shown on the caller and as a pill', ev("document.querySelectorAll('#vworld .cbadge.breaking').length") == 1
          and pg.locator('#vworld .decision-pill').filter(has_text='Caller change').count() == 1)
    pg.locator('#vworld .decision-pill').filter(has_text='Caller change').click(); pg.wait_for_timeout(80)
    check('…its card offers the API versions or "Stay on v1"', 'breaking change in the caller' in pg.inner_text('#vworld .assess-card').lower()
          and pg.locator('#vworld .assess-card [data-vid]').count() >= 1 and pg.locator('#vworld .assess-card [data-assess=v1]').count() == 1)
    f = ev(f"{d}.serializeFlow()")
    check('note 10: the caller change is saved', f.get('callerChange') == [{'caller': 0, 'change': 'breaking'}] and ev(f"{d}.validateFlow({json.dumps(f)})") is None)
    ev(f"{d}.loadFlow({json.dumps(f)})"); pg.wait_for_timeout(100)
    check('…and restored', ev("document.querySelectorAll('#vworld .cbadge.breaking').length") == 1)
    txt = ev("(()=>{ const r = window.__debug.printAssessment(true); const t = document.querySelector('.print-host .ps-report').innerText; r(); return t; })()")
    check('…and listed in the print', 'breaking change in the calling application' in txt)
    pg.locator('#vworld .assess-card [data-vid]').first.click() if pg.locator('#vworld .assess-card [data-vid]').count() else (
        pg.locator('#vworld .decision-pill').filter(has_text='Caller change').click(), pg.locator('#vworld .assess-card [data-vid]').first.click())
    pg.wait_for_timeout(120)
    check('…applying an API version resolves it', any(v.startswith('a2p-') for v in ev(f"{d}.versionOverrides()").values()) and not any(x.get('callerId') for x in ev(f"{d}.compositeDecisions()")))
    shot('r7-caller-change')

    check('no page errors', not errs)
    if errs: print(errs[:3])
    br.close()
print(f'{sum(res)}/{len(res)} passed')
raise SystemExit(0 if all(res) else 1)
