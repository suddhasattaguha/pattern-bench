"""Pattern Bench 2.0 — round 6 (fix list 1–15) (Python Playwright).
Run: python3 tests/test_round6.py   (PB_SHOT=dir saves screenshots)"""
import os, json, re
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = 'file:///' + ROOT.replace(os.sep, '/').lstrip('/') + '/pattern-bench.html'
SHOT = os.environ.get('PB_SHOT')
res = []
def check(name, cond):
    res.append(bool(cond)); print(('PASS ' if cond else 'FAIL ') + name)

# segments of every connector path in a pane (straight 'L' parts only, bends are rounded)
SEGS = """(pane) => [...document.querySelectorAll(pane + ' .flow-layer path.link')].map(p => {
    const nums = p.getAttribute('d').match(/[ML][-\\d.]+ [-\\d.]+/g) || [];
    return nums.map(t => t.slice(1).split(' ').map(Number));
  })"""

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 2000, 'height': 1300})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL)
    ev = pg.evaluate
    d = "window.__debug"
    def pick(skey, pane='#world'):
        pg.locator(f'{pane} .flow-layer .node[data-skey="{skey}"]').first.click(force=True)
    def shot(name):
        if SHOT: os.makedirs(SHOT, exist_ok=True); pg.screenshot(path=os.path.join(SHOT, name + '.png'))
    visible_versions = lambda: ev("[...document.querySelectorAll('#versionGrid .version-card')].filter(c=>!c.classList.contains('off-flow') && getComputedStyle(c).display!=='none').map(c=>c.dataset.variant)")
    clear = lambda: (pg.click('#clearCanvas'), pg.click('#confirmOk'))

    # ================= single flow stays v1.9 (round-6 fields are composite-only) =================
    for t in ['api-to-process', 'process-to-api', 'api-to-process']:
        ev(f"{d}.append('{t}')")
    f = ev(f"{d}.serializeFlow()")
    check('single flow: no round-6 fields in the file', not any(k in f for k in ['lineFlips', 'callerVer', 'laneChoice', 'acks', 'mode']))
    check('single flow: no connector data / hit paths in the DOM', ev("document.querySelectorAll('#world [data-own], #world .link-hit').length") == 0)
    # fix 14: new process icon (both modes)
    check('fix 14: process icon = hexagon with start dot, diamond and two steps',
          ev("(()=>{const n=document.querySelector('#world .node[data-type=process]'); return n.querySelectorAll('rect.n-dot').length===2 && n.querySelectorAll('circle.n-dot').length===1 && !n.querySelector('circle.n-line')})()"))
    check('…also on the library cards', ev("document.querySelectorAll('#quadrantGrid .node[data-type=process] rect.n-dot').length") > 0)
    # fix 11: middle API wording (single flow)
    pg.click('#tabVersioned')
    ev(f"{d}.dropVersion('p2a-contract-switch', 10, 10)") if False else None
    pick('block-2:out'); pg.locator('#world .target-card .dc-side button').first.click()
    ev(f"{d}.dropVersion('p2a-contract-switch', 10, 10)"); pg.wait_for_timeout(100)
    cap = ev("document.querySelector('#vworld .versioned .vcaption').textContent")
    check('fix 11: an API between two blocks reads "API v2", not "Target API v2"', cap == 'API v2 · same Process')
    check('…its title names provider / consumer', 'downstream iPaaS provides it' in ev("document.querySelector('#vworld .versioned').title"))
    # fix 8: selected tile in front, bigger remove ×
    pg.locator('#vworld .cblock.versioned').first.click(position={'x': 40, 'y': 60})
    z = ev("getComputedStyle(document.querySelector('#vworld .cblock.versioned.selected')).zIndex")
    others = ev("Math.max(...[...document.querySelectorAll('#vworld .cblock:not(.selected)')].map(b=>+getComputedStyle(b).zIndex||0))")
    check('fix 8: the selected tile is drawn in front of every other tile', int(z) > others)
    xr = ev("(()=>{const r=document.querySelector('#vworld .cblock.selected .delete-x').getBoundingClientRect(); return [r.width, r.height]})()")
    check('fix 8: the remove × is ~24 px', xr[0] >= 22 and xr[1] >= 22)
    pg.locator('#vworld .cblock.selected .delete-x').click()
    check('…and removes the version', ev(f"Object.keys({d}.versionOverrides()).length") == 0)

    # fix 13 (single flow): acknowledge a ⚠ dependent-logic marker
    pg.click('#tabBaseFlow'); clear()
    for t in ['process-to-publish', 'consume-to-process', 'process-to-api']:
        ev(f"{d}.append('{t}')")
    pg.click('#tabVersioned')
    ev(f"{d}.dropVersion('c2p-contract-dual', 10, 10)"); pg.wait_for_timeout(100)
    pg.click('#vworld .ripple-card [data-ripple=pass]'); pg.click('#vworld .ripple-card [data-code=no]'); pg.wait_for_timeout(100)
    check('setup: a ⚠ dependent logic marker', ev("document.querySelectorAll('#vworld .ibadge').length") == 1)
    pg.locator('#vworld .ibadge').click(); pg.wait_for_timeout(100)
    check('fix 13: clicking the ⚠ opens a card with Acknowledge and a note', pg.locator('#vworld .warn-card [data-action=ack]').count() == 1)
    pg.fill('#vworld .warn-card input.warn-note', 'noted with owner'); pg.click('#vworld .warn-card [data-action=ack]'); pg.wait_for_timeout(100)
    check('…the ⚠ turns grey with ✓', ev("document.querySelector('#vworld .ibadge').classList.contains('acked')") and '✓' in pg.text_content('#vworld .ibadge'))
    f = ev(f"{d}.serializeFlow()")
    check('…saved with the flow (by position)', f.get('acks') == [{'id': 'impact|@t2:out', 'note': 'noted with owner'}] and ev(f"{d}.validateFlow({d}.serializeFlow())") is None)
    ev(f"{d}.loadFlow({json.dumps(f)})"); pg.wait_for_timeout(100)
    check('…and restored on load', ev("document.querySelector('#vworld .ibadge').classList.contains('acked')"))
    # fix 9 / 12 (single flow): print report
    ev("(()=>{ window.__restore = window.__debug.printAssessment(true); return 1; })()")
    txt = pg.inner_text('.print-host .ps-report')
    check('fix 9 (single flow too): the print lists entries per component with numbered markers on the diagram',
          ev("document.querySelectorAll('.print-host .ps-entries li').length") >= 2 and
          ev("document.querySelectorAll('.print-host .ps-marker').length") == ev("document.querySelectorAll('.print-host .ps-entries li').length"))
    check('fix 12: breaking vs non-breaking wording', 'new version (breaking)' in txt)
    check('fix 13: an acknowledged ⚠ shows its note in the print', 'acknowledged: noted with owner' in txt)
    check('fix 9: the corner list of names is gone', 'Assets' not in txt)
    ev("window.__restore()")
    pg.click('#printBtn'); pg.wait_for_timeout(100)
    check('fix 9: unnamed affected components → "name them now / print with auto labels"', pg.locator('.print-host [data-pp=auto]').count() == 1 and 'no name' in pg.inner_text('.print-host .pp-ask'))
    pg.click('.print-host [data-pp=name]'); pg.wait_for_timeout(100)
    check('…"Name them now" highlights the containers to name', ev("document.querySelectorAll('#world .pcont.need-name').length") >= 1)
    pg.locator('#world .pcont-label.need-name').first.click()
    first_need = pg.locator('.label-editor input').first
    first_need.fill('SAP BTP'); pg.locator('.label-editor input').nth(1).fill('order-flow'); pg.keyboard.press('Enter')
    pg.click('#tabVersioned')
    ev("(()=>{ window.__restore = window.__debug.printAssessment(true); return 1; })()")
    txt = pg.inner_text('.print-host .ps-report')
    check('…a named component is titled by its name and platform; the others by auto labels', 'order-flow (SAP BTP)' in txt and '(unnamed)' in txt)
    ev("window.__restore()")

    # ================= composite flow =================
    pg.goto(URL); pg.wait_for_timeout(100)        # fresh page: block ids start at block-1
    for t in ['api-to-process', 'process-to-publish', 'consume-to-api']:
        ev(f"{d}.append('{t}')")
    pg.click('#modeComposite')
    pick('block-2:out'); ev(f"{d}.compositeAttach('consume-to-process')")
    pick('block-2:out'); ev(f"{d}.compositeAttach('consume-to-api')")
    pick('block-1:in'); pg.click('#world .comp-card .dc-opt')
    pick('block-1:in'); pg.click('#world .comp-card .dc-opt')
    pick('block-1:in'); ev(f"{d}.compositeAttach('process-to-api')")
    pick('block-1:in'); pg.click('#world .comp-card .dc-opt')
    pg.mouse.click(1900, 1250)
    b4, b5, b6 = 'block-4', 'block-5', 'block-6'
    # fix 4: caller boxes
    boxes = ev("[...document.querySelectorAll('#world .pcont.own-external')].filter(r=>r.tagName==='rect').map(r=>[+r.getAttribute('width'), +r.getAttribute('height')])")
    callers_n = len(ev(f"{d}.callersList()"))
    check('fix 4: three readable caller boxes (~150 × 120)', callers_n == 3 and sum(1 for w, h in boxes if w == 150 and h >= 110) >= 3)
    cy = ev("[...document.querySelectorAll('#world .flow-layer .node[data-type=app]')].map(n=>n.transform.baseVal.consolidate().matrix.f).sort((a,b)=>a-b)")
    check('fix 4: stacked ~130 px apart', all(b - a >= 125 for a, b in zip(cy, cy[1:])))
    rects = ev("[...document.querySelectorAll('#world .cblock')].filter(b=>b.style.display!=='none').map(b=>[parseFloat(b.style.left),parseFloat(b.style.top),parseFloat(b.style.width)+20,parseFloat(b.style.height)])")
    cboxes = ev("[...document.querySelectorAll('#world .pcont.own-external')].filter(r=>r.tagName==='rect' && +r.getAttribute('width')===150).map(r=>[+r.getAttribute('x'),+r.getAttribute('y'),150,+r.getAttribute('height')])")
    inter = lambda a, b: a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]
    check('fix 4: rows make room — no caller box overlaps a tile', not any(inter(c, t) for c in cboxes for t in rects))
    # fix 1: separate paths at the API (3 callers + 1 multi-source flow) and at the topic (fan-out)
    segs = ev(f"({SEGS})('#world')")
    ends = [tuple(map(round, s[-1])) for s in segs]
    check('fix 1: connectors arriving at one component all end at different points (meet only at the arrowhead)', len(ends) == len(set(ends)))
    vert = [(round(a[0]), round(min(a[1], b[1])), round(max(a[1], b[1]))) for s in segs for a, b in zip(s, s[1:]) if abs(a[0] - b[0]) < 0.5 and abs(a[1] - b[1]) > 1]
    shared = [(u, v) for i, u in enumerate(vert) for v in vert[i+1:] if u[0] == v[0] and u[1] < v[2] and v[1] < u[2]]
    check('fix 1: no two connectors share a vertical segment (junction / drop lines)', not shared)
    horiz = [(round(a[1]), round(min(a[0], b[0])), round(max(a[0], b[0]))) for s in segs for a, b in zip(s, s[1:]) if abs(a[1] - b[1]) < 0.5 and abs(a[0] - b[0]) > 1]
    hshared = [(u, v) for i, u in enumerate(horiz) for v in horiz[i+1:] if u[0] == v[0] and u[1] + 2 < v[2] and v[1] + 2 < u[2]]
    check('fix 1: …nor a horizontal one', not hshared)
    shot('r6-base')

    # fix 2 / 3: component + connector
    pg.click('#tabVersioned'); pick('block-2:out'); pg.wait_for_timeout(100)
    check('fix 2: library empty until a connector is picked', visible_versions() == [])
    check('fix 2: the topic\'s 4 connectors are highlighted and clickable', ev("document.querySelectorAll('#world .link-hit.pickable').length") >= 4)
    card = pg.locator('#world .target-card')
    check('fix 3: guide card = assessment, no block list', 'shared by 4 flows' in card.inner_text() and '1 publish into it (upstream)' in card.inner_text()
          and card.locator('.dc-side button').count() == 2)
    st = ev("(()=>{const c=document.querySelector('#world .target-card'); const s=getComputedStyle(c); return [+s.zIndex, s.backgroundColor, c.offsetWidth]})()")
    check('fix 3: opaque, on top of the flow layer, ≤ 280 px', st[0] > 60 and 'rgba' not in st[1] and st[2] <= 280)
    cr = ev("(()=>{const c=document.querySelector('#world .target-card'); return [parseFloat(c.style.left), parseFloat(c.style.top), c.offsetWidth, c.offsetHeight]})()")
    area = lambda a, b: max(0, min(a[0]+a[2], b[0]+b[2]) - max(a[0], b[0])) * max(0, min(a[1]+a[3], b[1]+b[3]) - max(a[1], b[1]))
    check('fix 3: placed in the freest side next to the component (covers little or no tile)', sum(area(cr, t) for t in rects) < 0.2 * cr[2] * cr[3])
    pg.click('#world .target-card .dc-side button[data-side=upstream]'); pg.wait_for_timeout(100)
    check('fix 3: "Upstream" with one connector picks it — the library shows its versions', ev(f"{d}.versionTarget().only") == 'block-2' and len(visible_versions()) > 0
          and 'Versioning on: Process-to-Publish' in pg.inner_text('#world .target-card'))
    pg.click('#world .target-card [data-action=other]')
    ev("document.querySelector('#world .link-hit.pickable[data-own=\"block-5\"]').dispatchEvent(new MouseEvent('click', {bubbles:true}))"); pg.wait_for_timeout(100)
    check('fix 2: clicking a branch connector picks that flow', ev(f"{d}.versionTarget().only") == b5 and 'branch · downstream' in pg.inner_text('#world .target-card'))
    pg.click('#world .target-card [data-action=clear]')
    pick(f'{b6}:out') if False else None
    # fix 7 + fix 10 + fix 15: a parallel topic version on the publisher
    pick('block-2:out'); pg.click('#world .target-card .dc-side button[data-side=upstream]')
    ev(f"{d}.dropVersion('p2t-contract-parallel', 10, 10)"); pg.wait_for_timeout(200)
    check('fix 7: v2 connectors are coloured violet', ev("document.querySelectorAll('#vworld .flow-layer .link.v2').length") >= 2)
    check('fix 7: the legend shows v1 / v2 / not valid in composite flow', ev("[...document.querySelectorAll('.version-legend .comp-only')].filter(e=>getComputedStyle(e).display!=='none').length") == 3)
    ds = ev(f"{d}.compositeDecisions()")
    assess = sorted(x['blockId'] for x in ds if x.get('kind') == 'assess')
    check('fix 10: the fan-out branches stay on v1 and are flagged as impacted (assess)', assess == sorted([b4, b5]))
    check('fix 15: parallel questions first appear as pills (no open card)', ev("document.querySelectorAll('#vworld .decision-card:not(.target-card):not(.warn-card)').length") == 0
          and ev("[...document.querySelectorAll('#vworld .decision-pill')].filter(p=>p.textContent.includes('Impacted')).length") == 2)
    check('fix 10: the impacted component in those blocks is highlighted', ev("document.querySelectorAll('#vworld .flow-layer .node.affected').length") >= 3)
    pg.locator('#vworld .decision-pill').filter(has_text='Impacted').first.click()
    check('fix 10: the assess card offers stay on v1 / move to v2 / keep both', pg.locator('#vworld .assess-card [data-assess]').count() == 3)
    who = ev("document.querySelector('#vworld .assess-card').dataset.key.split('|')[0]")
    pg.click('#vworld .assess-card [data-assess=v2]'); pg.wait_for_timeout(100)
    check('…"move to v2" connects that branch to the v2 lane (violet) and records the answer',
          ev(f"{d}.serializeFlow().laneChoice") == [{'ref': 'b0.0' if who == b4 else 'b1.0', 'choice': 'v2'}] and '→ Moved to Topic v2' in pg.inner_text('#vworld'))
    pg.locator('#vworld .decision-pill').filter(has_text='Impacted').first.click()
    pg.click('#vworld .assess-card [data-assess=both]'); pg.wait_for_timeout(100)
    check('fix 10: "keep both" → amber lines, ⚠ badge and the warning note open', ev("document.querySelectorAll('#vworld .flow-layer .link.warn').length") == 2
          and ev("document.querySelectorAll('#vworld .wbadge').length") == 1 and 'same consumer receives two versions' in pg.inner_text('#vworld .warn-card'))
    segs = ev(f"({SEGS})('#vworld')")
    vert = [(round(a[0]), round(min(a[1], b[1])), round(max(a[1], b[1]))) for s in segs for a, b in zip(s, s[1:]) if abs(a[0] - b[0]) < 0.5 and abs(a[1] - b[1]) > 1]
    shared = [(u, v) for i, u in enumerate(vert) for v in vert[i+1:] if u[0] == v[0] and u[1] < v[2] and v[1] < u[2]]
    check('fix 1: in the versioned copy too, v1 and v2 lanes never share a drop line', not shared)
    shot('r6-parallel')
    flow = ev(f"{d}.serializeFlow()")
    check('round-6 state saves and validates', ev(f"{d}.validateFlow({d}.serializeFlow())") is None and len(flow['laneChoice']) == 2)
    ev(f"{d}.loadFlow({json.dumps(flow)})"); pg.wait_for_timeout(150)
    check('…and loads back (assessments, warning)', ev("document.querySelectorAll('#vworld .flow-layer .link.warn').length") == 2 and len(ev(f"{d}.serializeFlow().laneChoice")) == 2)
    pg.locator('#vworld .wbadge').click(); pg.wait_for_timeout(50)
    if not pg.locator('#vworld .warn-card').count(): pg.locator('#vworld .wbadge').click()
    pg.click('#vworld .warn-card [data-action=ack]'); pg.wait_for_timeout(100)
    check('fix 13: a "not a valid pattern" warning can be acknowledged', ev("document.querySelector('#vworld .wbadge').classList.contains('acked')"))

    B1, B2 = ev(f"{d}.chainOrder().map(b=>b.dataset.id)")[:2]
    # fix 5: switch on the publisher → swap dotted / solid
    ev(f"{d}.removeVersion('{B2}')")
    pick(B2 + ':out'); pg.click('#world .target-card .dc-side button[data-side=upstream]')
    ev(f"{d}.dropVersion('p2t-contract-switch', 10, 10)"); pg.wait_for_timeout(150)
    check('fix 15: a switch opens its cards straight away', ev("document.querySelectorAll('#vworld .decision-card:not(.target-card):not(.warn-card)').length") >= 1)
    pg.locator('#vworld [data-action=later]').first.click() if pg.locator('#vworld [data-action=later]').count() else None
    togs = ev(f"[...document.querySelectorAll('#vworld .link-hit[data-tog^=\"fan|{B2}\"]')].map(h=>h.dataset.tog)")
    check('fix 5: the publisher\'s two topic lines are clickable', len(togs) == 2)
    dotted = ev(f"(()=>{{const l=[...document.querySelectorAll('#vworld .link[data-tog^=\"fan|{B2}\"]')].find(x=>x.classList.contains('retired')); return l && l.dataset.tog}})()")
    ev(f"document.querySelector('#vworld .link-hit[data-tog=\"{dotted}\"]').dispatchEvent(new MouseEvent('click', {{bubbles:true}}))"); pg.wait_for_timeout(150)
    check('fix 5: dotted → solid: both live = amber, ⚠ and the publisher warning', ev("document.querySelectorAll('#vworld .link.warn').length") == 2
          and 'one process publishes two versions' in pg.inner_text('#vworld .warn-card'))
    check('…saved as a line swap', ev(f"{d}.serializeFlow().lineFlips") == [{'ref': 't1', 'links': [int(dotted.split('|')[2])]}])
    ev(f"document.querySelector('#vworld .link-hit[data-tog=\"{dotted}\"]').dispatchEvent(new MouseEvent('click', {{bubbles:true}}))"); pg.wait_for_timeout(150)
    check('…clicking a solid line while the other is solid makes it dotted again (back to the switch)', ev("document.querySelectorAll('#vworld .link.warn').length") == 0
          and ev(f"{d}.serializeFlow().lineFlips") in (None, []))
    other = [t for t in togs if t != dotted][0]
    ev(f"document.querySelector('#vworld .link-hit[data-tog=\"{other}\"]').dispatchEvent(new MouseEvent('click', {{bubbles:true}}))"); pg.wait_for_timeout(150)
    check('…clicking the only solid line swaps the two (one always stays live)', ev(f"document.querySelector('#vworld .link[data-tog=\"{other}\"]').classList.contains('retired')")
          and not ev(f"document.querySelector('#vworld .link[data-tog=\"{dotted}\"]').classList.contains('retired')"))
    ev(f"{d}.removeVersion('{B2}')")

    # fix 6: callers on a versioned API — per-caller v1 / v2
    pick(B1 + ':in'); pg.wait_for_timeout(50)
    check('fix 2: callers\' connectors count (API: 3 callers + 2 flows)', len(ev(f"{d}.versionTarget().conns")) == 5)
    caller_hit = ev("[...document.querySelectorAll('#world .link-hit.pickable')].find(h=>h.dataset.own.startsWith('xc|')).dataset.own")
    ev(f"document.querySelector('#world .link-hit.pickable[data-own=\"{caller_hit}\"]').dispatchEvent(new MouseEvent('click', {{bubbles:true}}))"); pg.wait_for_timeout(50)
    check('fix 2d: a caller\'s connector picks the API\'s block, the card says only this caller moves', ev(f"{d}.versionTarget().only") == B1
          and 'only this caller moves to v2' in pg.inner_text('#world .target-card'))
    ev(f"{d}.dropVersion('a2p-contract-parallel', 10, 10)"); pg.wait_for_timeout(150)
    cid = caller_hit.split('|')[1]
    cv = ev(f"{d}.serializeFlow().callerVer")
    check('fix 2d / 6: that caller alone is on v2, the others stay on v1', len(cv) == 1 and cv[0]['ver'] == 'v2')
    check('fix 6: every caller has a v1 and a v2 connector (one solid, one dotted)', ev("document.querySelectorAll('#vworld .link-hit[data-tog^=\"caller|\"]').length") == 6)
    check('fix 6: the caller on v2 has no ⚠ dependent logic; the others keep it', ev("document.querySelectorAll('#vworld .ibadge').length") == 2)
    others_c = ev("[...new Set([...document.querySelectorAll('#vworld .link-hit[data-tog^=\"caller|\"]')].map(h=>h.dataset.tog.split('|')[1]))]")
    for c in others_c:
        if c != cid:
            ev(f"document.querySelector('#vworld .link-hit[data-tog=\"caller|{c}|v2\"]').dispatchEvent(new MouseEvent('click', {{bubbles:true}}))"); pg.wait_for_timeout(80)
    check('fix 6: clicking a caller\'s dotted v2 line → both live → amber + caller warning', ev("document.querySelectorAll('#vworld .link.warn').length") >= 2
          and 'one process calls two versions' in pg.inner_text('#vworld'))
    for c in others_c:
        if c != cid:
            ev(f"document.querySelector('#vworld .link-hit[data-tog=\"caller|{c}|v1\"]').dispatchEvent(new MouseEvent('click', {{bubbles:true}}))"); pg.wait_for_timeout(80)
    check('fix 6: …then v1 → dotted: all callers on v2, "no caller left on v1"', ev("document.querySelectorAll('#vworld .link.warn').length") == 0
          and ev("document.querySelectorAll('#vworld .nbadge').length") == 1 and 'no caller left on v1' in pg.text_content('#vworld .flow-layer'))
    shot('r6-callers')
    # fix 9 (composite): print
    pg.click('#printBtn'); pg.wait_for_timeout(100)
    if pg.locator('.print-host [data-pp=auto]').count(): pg.click('.print-host [data-pp=auto]')
    rep = pg.inner_text('.print-host .ps-report')
    check('fix 9 (composite): entries name the components and the branch / main flow, and list the callers\' versions',
          'Callers:' in rep and '→ v2' in rep and 'main flow' in rep and '(unnamed)' in rep)
    check('fix 9: markers match the entries', ev("document.querySelectorAll('.print-host .ps-marker').length") == ev("document.querySelectorAll('.print-host .ps-entries li').length"))
    if SHOT: pg.screenshot(path=os.path.join(SHOT, 'r6-print.png'))
    pg.click('.print-host [data-pp=close]')
    # regression (Nov 15): a new version a block brings must always be drawn — also when that block sits on a
    # branch and the shared component has no such version on the main flow (e.g. a consumer on Topic v2)
    pg.goto(URL); pg.wait_for_timeout(100)
    for t in ['api-to-process', 'process-to-publish', 'consume-to-api']:
        ev(f"{d}.append('{t}')")
    pg.click('#modeComposite')
    pick('block-2:out'); ev(f"{d}.compositeAttach('consume-to-process')")
    pick('block-2:out'); ev(f"{d}.compositeAttach('consume-to-api')")
    pick('block-2:out'); ev(f"{d}.compositeAttach('api-to-publish')")
    pick('block-1:out'); ev(f"{d}.compositeAttach('process-to-file')")
    pick('block-1:in'); ev(f"{d}.compositeAttach('process-to-api')")
    pg.click('#tabVersioned')
    missing = []
    for bid, tpl in ev("[...document.querySelectorAll('#world .cblock')].map(b=>[b.dataset.id,b.dataset.tpl])"):
        for v in ev(f"Object.values({d}.variantsById).filter(v=>v.base==='{tpl}').map(v=>v.id)"):
            ev(f"(()=>{{const o={d}.versionOverrides(); Object.keys(o).forEach(k=>delete o[k]); o['{bid}']='{v}'; {d}.renderCopy(); }})()")
            need = set(ev(f"{d}.variantsById['{v}'].nodes.filter(n=>n.ver==='v2').map(n=>n.type)"))
            have = set(ev("[...document.querySelectorAll('#vworld .flow-layer .node')].filter(n=>{const b=n.nextElementSibling; return b && b.classList.contains('vbadge') && b.textContent==='v2'}).map(n=>n.dataset.type)"))
            if need - have: missing.append((tpl, v, sorted(need - have)))
    check('every new version (v2) a block brings is drawn, on the main flow and on every branch', not missing)
    ev(f"(()=>{{const o={d}.versionOverrides(); Object.keys(o).forEach(k=>delete o[k]); o['block-5']='c2a-topic-switch'; {d}.renderCopy(); }})()")
    tp = ev("[...document.querySelectorAll('#vworld .flow-layer .node[data-type=topic]')].map(n=>{const m=n.transform.baseVal.consolidate().matrix; const b=n.nextElementSibling; return [m.e, m.f, b && b.classList.contains('vbadge') ? b.textContent : '']})")
    v1x = [t for t in tp if t[2] != 'v2' and abs(t[1] - 240) < 1]
    v2t = [t for t in tp if t[2] == 'v2']
    check('…a branch\'s new Topic v2 sits right next to the shared v1 topic on the main flow (not on the branch row)',
          len(v2t) == 1 and v1x and abs(v2t[0][0] - v1x[0][0]) < 1 and abs(v2t[0][1] - 240) <= 80)
    if missing: print(missing)
    check('no page errors', not errs)
    if errs: print(errs)
    br.close()
print(f'\n{sum(res)}/{len(res)} checks passed')
