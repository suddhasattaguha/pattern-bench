"""Pattern Bench 2.0 — fix 17: Export for registry (schema pattern-bench.registry-entry v0.6) (Python Playwright).
Run: python3 tests/test_registry_export.py   (PB_SHOT=dir saves screenshots)"""
import os, json, re
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = 'file:///' + ROOT.replace(os.sep, '/').lstrip('/') + '/pattern-bench.html'
SHOT = os.environ.get('PB_SHOT')
res = []
def check(name, cond):
    res.append(bool(cond)); print(('PASS ' if cond else 'FAIL ') + name)

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 2000, 'height': 1300}, accept_downloads=True)
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    ev = pg.evaluate
    d = "window.__debug"
    def click_node(skey, pane='#world'):
        pg.locator(f'{pane} .flow-layer .node[data-skey="{skey}"]').first.click(force=True); pg.wait_for_timeout(80)
    def label(i, platform, asset, app=False):
        pg.locator('#world .pcont-label.editable').nth(i).click()
        if app:
            pg.fill('.label-editor input[name=name]', platform)
        else:
            pg.fill('.label-editor input[name=platform]', platform); pg.fill('.label-editor input[name=asset]', asset)
        pg.keyboard.press('Enter'); pg.wait_for_timeout(50)
    def export(fill=None):
        pg.click('#registryBtn'); pg.wait_for_timeout(80)
        if fill: fill()
        got = []
        def h(dl): got.append(dl)
        pg.on('download', h)
        pg.click('#regDialog [data-a=export]')
        for _ in range(50):
            if len(got) >= 2: break
            pg.wait_for_timeout(100)
        pg.remove_listener('download', h)
        return {dl.suggested_filename: json.load(open(dl.path())) for dl in got}

    # ---- composite scenario: API-to-Process → Process-to-Publish → Consume-to-API, a caller, labels
    pg.goto(URL); pg.wait_for_timeout(100)
    for t in ['api-to-process', 'process-to-publish', 'consume-to-api']: ev(f"{d}.append('{t}')")
    pg.click('#modeComposite')
    click_node('block-1:in'); pg.click('#world .comp-card .dc-opt'); pg.mouse.click(1900, 1250)
    types = ev("[...document.querySelectorAll('#world .pcont-label .pcont-type')].map(t=>t.textContent)")
    idx = {t: i for i, t in reversed(list(enumerate(types)))}
    label(types.index('IPAAS'), 'SAP BTP', 'Sales Order iFlow')
    label(types.index('MESSAGE BROKER'), 'Azure', 'Order Broker')
    label(types.index('END APPLICATION'), 'S/4HANA', '', app=True)
    check('setup: the toolbar has "Export for registry"', pg.locator('#registryBtn').count() == 1)

    # ---- the dialog
    pg.click('#registryBtn'); pg.wait_for_timeout(80)
    txt = pg.inner_text('#regDialog')
    check('dialog: a new scenario says its id is created now, version 1', 'New scenario' in txt and 'version 1' in txt)
    check('dialog: lists every component with a name field (6 incl. the caller)', pg.locator('#regDialog [data-comp]').count() == 6)
    check('dialog: warns about the container without a label (the caller) and unnamed components',
          'no ref' in txt and 'caller' in txt and 'unnamed component' in txt)
    pg.click('#regDialog [data-a=export]'); pg.wait_for_timeout(50)
    check('dialog: the scenario name is required', 'Give the scenario a name' in pg.inner_text('#regDialog') and not pg.locator('#regOverlay').is_hidden())
    pg.click('#regDialog [data-a=cancel]')
    check('dialog: Cancel closes it and changes nothing', pg.locator('#regOverlay').is_hidden() and ev(f"{d}.scenarioMeta()") is None)

    # ---- add a version, then export
    pg.click('#tabVersioned')
    click_node('block-1:out'); pg.click('#world .target-card .dc-side button[data-side=upstream]')
    ev(f"{d}.dropVersion('a2p-process-parallel', 10, 10)"); pg.wait_for_timeout(120)
    def fill1():
        pg.fill('#regDialog [data-f=name]', 'Sales order to S/4 via broker')
        pg.fill('#regDialog [data-f=author]', 'Suddha')
        pg.fill('#regDialog [data-f=tags]', 'order, EDA')
        pg.fill('#regDialog [data-why^="ver|"]', 'New pricing logic runs next to v1')
        pg.fill('#regDialog [data-comp="block-1:in"]', 'Order API')
        pg.fill('#regDialog [data-comp="block-2:out"]', 'Order events')
        pg.click('#regDialog [data-a=add-rel]')
        pg.locator('#regDialog .rg-rel select').select_option('derivedFrom')
        pg.fill('#regDialog .rg-rel input >> nth=0', 'scn-12ab34'); pg.fill('#regDialog .rg-rel input >> nth=1', '2')
        if SHOT: os.makedirs(SHOT, exist_ok=True); pg.screenshot(path=os.path.join(SHOT, 'reg-dialog.png'))
    files = export(fill1)
    names = sorted(files)
    check('export: two files — <id>.v1.registry.json and <id>.v1.canvas.json',
          len(names) == 2 and re.match(r'^scn-[a-z0-9]{6}\.v1\.canvas\.json$', names[0]) and names[1] == names[0].replace('canvas', 'registry'))
    spec = files[names[1]]; canvas = files[names[0]]
    sid = spec['scenario']['id']
    check('spec: schema pattern-bench.registry-entry v0.6', spec['schema'] == 'pattern-bench.registry-entry' and spec['schemaVersion'] == '0.6')
    check('spec: scenario id / version / name / author / tags / mode / canvas pointer',
          spec['scenario']['version'] == 1 and spec['scenario']['name'] == 'Sales order to S/4 via broker' and spec['scenario']['author'] == 'Suddha'
          and spec['scenario']['tags'] == ['order', 'EDA'] and spec['scenario']['source']['mode'] == 'composite' and spec['scenario']['canvas']['file'] == names[0])
    comps = {c['id']: c for c in spec['base']['components']}
    by_name = {c['name']: c for c in comps.values()}
    check('spec: refs generated from platform / asset — slug(platform)/slug(asset)#type',
          by_name['Order API']['ref'] == 'sap-btp/sales-order-iflow#api' and by_name['Order events']['ref'] == 'azure/order-broker#topic')
    check('spec: a second component of the same type in a container is not numbered unless repeated; process ref', any(c['ref'] == 'sap-btp/sales-order-iflow#process' for c in comps.values()))
    check('spec: the end application gets endapp/<name> refs', any(c['ref'] == 'endapp/s-4hana#api' and c['owner'] == 'endApp' for c in comps.values()))
    check('spec: the unlabelled caller container has no ref (and its component neither)', any(k['kind'] == 'caller' and k['ref'] is None for k in spec['base']['containers'])
          and any(c['type'] == 'app' and c['ref'] is None for c in comps.values()))
    check('spec: unnamed components carry auto labels, marked autoName', by_name['Order API']['autoName'] is False and any(c['autoName'] and c['name'] == 'Queue 1' for c in comps.values()))
    check('spec: links carry fromRef / toRef', any(l['fromRef'] == 'sap-btp/sales-order-iflow#api' and l['toRef'] == 'sap-btp/sales-order-iflow#process' for l in spec['base']['links']))
    check('spec: blocks list their template and components', [b['templateId'] for b in spec['base']['blocks']] == ['api-to-process', 'process-to-publish', 'consume-to-api'])
    v = spec['versions'][0] if spec['versions'] else {}
    check('spec: one versioning entry — label, status open, applies to the process (upstream side)',
          len(spec['versions']) == 1 and v['status'] == 'open' and comps[v['appliesTo']['component']]['type'] == 'process' and v['appliesTo']['side'] == 'upstream')
    check('spec: decision — why / who / option / variant', v['decision']['why'] == 'New pricing logic runs next to v1' and v['decision']['who'] == 'Suddha'
          and v['decision']['option'] == 'parallel' and v['decision']['variant'] == 'a2p-process-parallel')
    check('spec: added API v2 + Process v2, planned, refs of the same components', sorted(a['type'] for a in v['added']) == ['api', 'process']
          and all(a['stage'] == 'planned' and a['version'] == 'v2' for a in v['added']) and any(a['ref'] == 'sap-btp/sales-order-iflow#api' and a['name'] == 'Order API v2' for a in v['added']))
    check('spec: addedLinks with versioned refs and line state', any(l['fromRef'] == 'sap-btp/sales-order-iflow#api@v2' and l['line'] == 'solid' for l in v['addedLinks']))
    check('spec: changed — API and process v1 → v2 (breaking)', sorted(comps[c['component']]['type'] for c in v['changed']) == ['api', 'process'] and all(c['change'] == 'breaking' for c in v['changed']))
    check('spec: impacts — the Process-to-Publish decision (pending) and the caller (stays on v1)',
          any(i['decision'] == 'pending' and i['affectedBlock'] == 'b2' for i in v['impacts']) and any(i['decision'] == 'stayV1' and comps[i['affected']]['type'] == 'app' for i in v['impacts']))
    check('spec: relations', spec['relations'] == [{'type': 'derivedFrom', 'scenarioId': 'scn-12ab34', 'version': 2}])
    check('canvas file: the normal flow file, with the scenario identity and component names',
          canvas['format'] == 'pattern-bench-flow' and canvas['scenario']['id'] == sid and canvas['scenario']['version'] == 1
          and {'key': '@t0:in', 'name': 'Order API'} in canvas['componentNames'] and ev(f"{d}.validateFlow({json.dumps(canvas)})") is None)

    # ---- re-export: same id, version + 1; dialog prefilled
    pg.click('#registryBtn'); pg.wait_for_timeout(80)
    check('re-export: the dialog shows the id and the next version, fields prefilled',
          f'Scenario {sid}' in pg.inner_text('#regDialog') and 'version 2' in pg.inner_text('#regDialog')
          and pg.input_value('#regDialog [data-f=name]') == 'Sales order to S/4 via broker' and pg.input_value('#regDialog [data-comp="block-1:in"]') == 'Order API')
    pg.click('#regDialog [data-a=cancel]')
    files2 = export()
    s2 = [f for n, f in files2.items() if n.endswith('.registry.json')][0]
    check('re-export: same scenario id, version 2, files named .v2', s2['scenario']['id'] == sid and s2['scenario']['version'] == 2 and any('.v2.' in n for n in files2))

    # ---- load the canvas file back: identity and names survive, next export is version 3
    c2 = [f for n, f in files2.items() if n.endswith('.canvas.json')][0]
    ev(f"{d}.loadFlow({json.dumps(c2)})"); pg.wait_for_timeout(120)
    check('load: scenario identity and component names restored', ev(f"{d}.scenarioMeta().id") == sid and ev(f"{d}.scenarioMeta().version") == 2
          and 'Order API' in ev(f"Object.values({d}.compNames())"))
    pg.click('#registryBtn'); pg.wait_for_timeout(80)
    check('load: the next export would be version 3', 'version 3' in pg.inner_text('#regDialog'))
    pg.keyboard.press('Escape')
    check('Escape closes the dialog', pg.locator('#regOverlay').is_hidden())
    # print uses the component name
    txt = ev("(()=>{ const r = window.__debug.printAssessment(true); const t = document.querySelector('.print-host .ps-report').innerText; r(); return t; })()")
    check('print: entries use the component names', 'Order API' in txt)
    # a broken scenario block is rejected
    bad = dict(c2); bad['scenario'] = dict(c2['scenario'], id='nope')
    check('validation: a bad scenario id is rejected', 'registry scenario' in (ev(f"{d}.validateFlow({json.dumps(bad)})") or ''))
    bad = dict(c2); bad['componentNames'] = [{'key': 'block-1:in', 'name': 'x'}]
    check('validation: a bad component key is rejected', 'component name' in (ev(f"{d}.validateFlow({json.dumps(bad)})") or ''))

    # ---- single flow: Δ and a version, no labels
    pg.goto(URL); pg.wait_for_timeout(100)
    for t in ['api-to-process', 'process-to-api']: ev(f"{d}.append('{t}')")
    pg.click('#tabVersioned')
    click_node('block-1:out'); pg.locator('#world .target-card .dc-side button').first.click()
    ev(f"{d}.dropVersion('a2p-contract-shared', 10, 10)"); pg.wait_for_timeout(120)
    click_node('block-2:out', '#vworld'); pg.click('#vworld .target-card [data-action=mark]'); pg.wait_for_timeout(80)
    f3 = export(lambda: pg.fill('#regDialog [data-f=name]', 'Single flow scenario'))
    s3 = [f for n, f in f3.items() if n.endswith('.registry.json')][0]
    check('single flow: exported with mode single, the version and the Δ as entries', s3['scenario']['source']['mode'] == 'single'
          and [x['decision']['option'] for x in s3['versions']] == ['switch', 'nonBreaking'] or [x['decision']['option'] for x in s3['versions']] == ['parallel', 'nonBreaking'])
    check('single flow: the ripple question shows up as an impact', any(i['decision'] in ('pending', 'absorb', 'passOn') for i in s3['versions'][0]['impacts']))
    check('single flow: no refs without labels — still a valid export', all(c['ref'] is None for c in s3['base']['components']))
    check('single flow: the canvas file still validates', ev(f"{d}.validateFlow({json.dumps([f for n, f in f3.items() if n.endswith('.canvas.json')][0])})") is None)

    check('no page errors', not errs)
    if errs: print(errs[:3])
    br.close()
print(f'{sum(res)}/{len(res)} passed')
raise SystemExit(0 if all(res) else 1)
