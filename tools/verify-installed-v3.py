"""Offline V3 installation smoke check. Does not start NX or mutate evidence."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    if len(sys.argv) != 2:
        raise SystemExit('expected staged app path')
    app = Path(sys.argv[1]).resolve(strict=True)
    sys.path.insert(0, str(app / 'src'))
    import nx_sketch_mcp
    from nx_sketch_mcp.config import config_from_object
    from nx_sketch_mcp.server import McpServer
    from nx_sketch_mcp.v3.project_root import project_root
    from nx_sketch_mcp.v3.reference_recognition import analyze_reference
    from nx_sketch_mcp.v3.service import review_disk_source, export_reviewed_disk_source
    from nx_sketch_mcp.v3.ug11 import compiler
    if not Path(nx_sketch_mcp.__file__).resolve().is_relative_to(app) or not Path(compiler.__file__).resolve().is_relative_to(app):
        raise RuntimeError('V3 code was not imported from staged app')
    root = project_root()
    original = root / 'tests/\u5916\u7403\u53c9.prt'
    snapshot = json.loads((root / 'workspace/v3/p1/P1-20261108-01/native/p1-reference-snapshot.json').read_text(encoding='utf8'))
    analysis = analyze_reference(snapshot, tolerances={'linear': .001, 'angular': .0001}, source_label='installed offline smoke')
    if analysis.get('execution_approved') is not False:
        raise RuntimeError('reference analysis boundary invalid')
    preview = review_disk_source(str(original))
    if (preview.get('status') != 'reviewed_disk_source_only' or preview.get('execution_approved') is not False
            or not preview.get('design_guidance', {}).get('preferences') or preview.get('group_count', 0) < 1):
        raise RuntimeError('reviewed plan preview unavailable')
    group = review_disk_source(str(original), group_index=0)
    McpServer._validate_prepare_v3_composition({'operation_id': 'install-check', 'ownership_id': 'offline',
        'binding_epoch': 1, 'revision_id': 'offline', 'steps': group['steps']})
    server = McpServer(config_from_object({}))
    try:
        init = server.handle_message({'jsonrpc':'2.0','id':1,'method':'initialize','params':{
            'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'v3-install-check','version':'1'}}})
        server.handle_message({'jsonrpc':'2.0','method':'notifications/initialized','params':{}})
        listing = server.handle_message({'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}})
        tools = {item['name'] for item in listing['result']['tools']}
        required = {'nx_analyze_v3_reference','nx_v3_review_disk_source','nx_v3_export_reviewed_ug11',
                    'nx_prepare_v3_composition','nx_v3_start_parametric_file_analysis','nx_v3_get_parametric_file_analysis'}
        if not required <= tools:
            raise RuntimeError('V3 MCP tools missing')
        version = init['result']['serverInfo']['version']
    finally:
        server.close()
    with tempfile.TemporaryDirectory(prefix='nx-v3-install-smoke-') as directory:
        config = Path(directory) / 'config.json'
        config.write_text('{}', encoding='utf8')
        requests = [
            {'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25',
                'capabilities':{},'clientInfo':{'name':'v3-installed-stdio-check','version':'1'}}},
            {'jsonrpc':'2.0','method':'notifications/initialized','params':{}},
            {'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'nx_v3_review_disk_source',
                'arguments':{'source_path':str(original)}}},
        ]
        wire = '\n'.join(json.dumps(request, ensure_ascii=True) for request in requests) + '\n'
        child = subprocess.run([sys.executable, '-I', '-B', str(app / 'tools/mcp_stdio.py'), '--config', str(config)],
                               cwd=directory, input=wire, capture_output=True, text=True, encoding='utf8',
                               errors='replace', timeout=60)
        if child.returncode:
            raise RuntimeError('installed stdio entry failed: ' + child.stderr[:500])
        responses = [json.loads(line) for line in child.stdout.splitlines() if line.strip()]
        response = next((item for item in responses if item.get('id') == 2), None)
        content = response.get('result', {}) if isinstance(response, dict) else {}
        actual = content.get('structuredContent', {})
        if content.get('isError') is not False or actual.get('group_count') != preview['group_count']:
            raise RuntimeError('installed stdio V3 planning tool failed')
        output = Path(directory) / 'bundle'
        result = export_reviewed_disk_source(str(original), str(output))
        if result.get('status') != 'generated_only' or result.get('execution_approved') is not False:
            raise RuntimeError('UG11 export did not remain generation-only')
        manifest = json.loads((output / 'manifest.json').read_text(encoding='utf8'))
        logic = json.loads((output / 'logic-ir.json').read_text(encoding='utf8'))
        if manifest.get('design_guidance') != logic.get('design_guidance'):
            raise RuntimeError('bundle guidance mismatch')
        runtime = subprocess.run([sys.executable, '-I', '-B', str(output / 'bundle_runtime.py'),
                                  '--overrides', str(output / 'parameters.json'), '--check-input', str(output)],
                                 cwd=directory, capture_output=True, text=True, encoding='utf8', errors='replace', timeout=180)
        if runtime.returncode:
            raise RuntimeError('portable UG11 runtime check failed: ' + runtime.stderr[:500])
    print(json.dumps({'version':version,'tool_count':len(tools),'reviewed_groups':preview['group_count'],
                      'source_root':str(root),'offline_v3_plan_and_portable_export':'PASS', 'installed_stdio_v3_tool':'PASS',
                      'native_execution':'NOT_RUN'}, ensure_ascii=True))


if __name__ == '__main__':
    main()
