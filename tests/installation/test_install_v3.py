"""Sandboxed offline checks of the V3 installer; never modifies a real installation."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / 'tools/install-local.ps1'


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='nx-v3-install-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.install = self.base / 'install'
        self.build = self.base / 'build'
        self.install.mkdir(); self.build.mkdir()
        self.coordination = self.base / 'test-journal-coordination'
        self.coordination.mkdir()
        (self.install / 'installation.json').write_text(json.dumps({'source_root': str(ROOT), 'version': 'old', 'unrelated': 'preserve'}), encoding='utf8')
        self.config_bytes = json.dumps({'pipe_name':'fixture','token_file':str(self.install/'token.txt'),
                                        'helper_path':str(self.install/'app/workspace/build/current/M2/M2JsonlHelper.exe')}).encode('utf8')
        (self.install / 'mcp-config.json').write_bytes(self.config_bytes)
        (self.install / 'token.txt').write_bytes(b'private-token-not-read-or-changed')
        (self.install / 'README.md').write_bytes(b'personal-readme-preserved')
        (self.install / 'app/src/nx_sketch_mcp').mkdir(parents=True)
        (self.install / 'app/src/nx_sketch_mcp/server.py').write_bytes(b'old server sentinel')
        (self.install / 'app/private').mkdir()
        (self.install / 'app/private/extra.txt').write_bytes(b'private-app-sentinel')
        for name in ('M2Bridge.dll','M2Entry.dll','M2JsonlHelper.exe','M2Startup.dll'):
            shutil.copyfile(ROOT / 'workspace/build/current/M2' / name, self.build / name)
        shutil.copyfile(ROOT / 'workspace/build/current/M2/ReferenceGeometryNative.dll', self.build / 'ReferenceGeometryNative.dll')

    def invoke(self, version='0.22.0', clean=False):
        # Execute the production script text with only its source and shared
        # journal-gate roots redirected to this fixture. No real global files
        # or session gate are opened by an installer test.
        wrapper = r"""
$ErrorActionPreference='Stop'
$text=[IO.File]::ReadAllText($env:NX_TEST_INSTALLER)
$originalProject = "`$projectRoot = (Resolve-Path -LiteralPath (Join-Path `$PSScriptRoot '..')).Path.TrimEnd('\','/')"
$originalGate = "`$coordinationRoot = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex/nx-sketch-mcp/journal-coordination'"
if (-not $text.Contains($originalProject) -or -not $text.Contains($originalGate)) { throw 'Test injection anchors changed.' }
$text=$text.Replace($originalProject, '`$projectRoot = $env:NX_TEST_PROJECT')
$text=$text.Replace($originalGate, '`$coordinationRoot = $env:NX_TEST_GATE')
$options=@{}; if ($env:NX_TEST_CLEAN -eq '1') { $options['CleanReplace']=$true }
& ([scriptblock]::Create($text)) -InstallRoot $env:NX_TEST_INSTALL -BuildRoot $env:NX_TEST_BUILD -Version $env:NX_TEST_VERSION @options
"""
        # Single-quoted PowerShell replacement text must contain the variable,
        # not an escaped backtick.
        wrapper = wrapper.replace("'`$projectRoot", "'$projectRoot").replace("'`$coordinationRoot", "'$coordinationRoot")
        env = os.environ.copy()
        env.update(NX_TEST_INSTALLER=str(INSTALLER), NX_TEST_PROJECT=str(ROOT), NX_TEST_GATE=str(self.coordination),
                   NX_TEST_INSTALL=str(self.install), NX_TEST_BUILD=str(self.build), NX_TEST_VERSION=version,
                   NX_TEST_CLEAN='1' if clean else '0')
        return subprocess.run(['pwsh','-NoProfile','-NonInteractive','-Command',wrapper], env=env,
                              cwd=ROOT, capture_output=True, text=True, encoding='utf8', errors='replace', timeout=180)

    def test_staged_v3_install_preserves_private_files_and_runs_from_unrelated_cwd(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('offline V3 plan and portable export passed', result.stdout)
        for path, expected in [('mcp-config.json',self.config_bytes),
                               ('token.txt',b'private-token-not-read-or-changed'),
                               ('app/private/extra.txt',b'private-app-sentinel')]:
            self.assertEqual((self.install / path).read_bytes(), expected)
        self.assertEqual((self.install / 'README.md').read_bytes(), (ROOT / 'docs/installed-README.md').read_bytes())
        self.assertEqual((self.install / 'app/README.md').read_bytes(), (ROOT / 'docs/installed-app-README.md').read_bytes())
        metadata = json.loads((self.install / 'installation.json').read_text(encoding='utf8'))
        self.assertEqual(metadata['source_root'], str(ROOT))
        self.assertEqual(metadata['unrelated'], 'preserve')
        app = self.install / 'app'
        for name in ('M2Bridge.dll','M2Entry.dll','M2JsonlHelper.exe','M2Startup.dll','ReferenceGeometryNative.dll'):
            self.assertEqual((app / 'workspace/build/current/M2' / name).read_bytes(), (self.build / name).read_bytes())
        self.assertEqual((app / 'nx-profile/startup/M2Startup.dll').read_bytes(), (self.build / 'M2Startup.dll').read_bytes())
        self.assertTrue((app / 'src/nx_sketch_mcp/v3/ug11/journal_template.cs').is_file())
        self.assertTrue((app / 'tools/mcp_stdio.py').is_file())
        installed_guide = (app / 'docs/v3/reference-rebuild.md').read_text(encoding='utf8')
        self.assertIn((ROOT / 'docs/v3/reference-rebuild.md').resolve().as_uri(), installed_guide)
        self.assertNotIn('../../workspace/v3', installed_guide)
        self.assertNotIn('../../tests/', installed_guide)
        check = subprocess.run([os.sys.executable,'-I','-B',str(ROOT/'tools/verify-installed-v3.py'),str(app)],
                               cwd=self.base, capture_output=True, text=True, encoding='utf8', errors='replace', timeout=180)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertEqual(json.loads(check.stdout)['native_execution'], 'NOT_RUN')
        self.assertEqual(json.loads(check.stdout)['installed_stdio_v3_tool'], 'PASS')
        self.assertTrue((app / 'tools/verify-m2-local-network.ps1').is_file())
        metadata_path = self.install / 'installation.json'
        original_metadata = metadata_path.read_bytes()
        metadata['source_root'] = str(self.base)
        metadata_path.write_text(json.dumps(metadata), encoding='utf8')
        rejected = subprocess.run([os.sys.executable,'-I','-B',str(ROOT/'tools/verify-installed-v3.py'),str(app)],
                                  cwd=self.base, capture_output=True, text=True, encoding='utf8', errors='replace', timeout=60)
        self.assertNotEqual(rejected.returncode, 0)
        metadata_path.write_bytes(original_metadata)
        installed_p3 = app / 'src/nx_sketch_mcp/v3/p3_integration.py'
        original_code = installed_p3.read_bytes()
        installed_p3.write_bytes(original_code + b'\n# changed after install\n')
        code_mismatch = subprocess.run([os.sys.executable,'-I','-B',str(ROOT/'tools/verify-installed-v3.py'),str(app)],
                                       cwd=self.base, capture_output=True, text=True, encoding='utf8', errors='replace', timeout=60)
        self.assertNotEqual(code_mismatch.returncode, 0)
        self.assertIn('installed P3 source differs', code_mismatch.stderr)
        installed_p3.write_bytes(original_code)
        self.assertFalse(list(self.install.glob('.v3-install-stage-*')))

    def test_clean_replace_removes_only_old_app_and_keeps_private_root(self):
        (self.install / 'sessions/private').mkdir(parents=True)
        (self.install / 'sessions/private/bridge.token').write_bytes(b'private-session-token')
        (self.install / 'journal-coordination').mkdir()
        (self.install / 'journal-coordination/state.txt').write_bytes(b'private-coordination')
        result = self.invoke(clean=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Clean replaced version', result.stdout)
        self.assertFalse((self.install / 'app/private/extra.txt').exists())
        self.assertEqual((self.install / 'mcp-config.json').read_bytes(), self.config_bytes)
        self.assertEqual((self.install / 'token.txt').read_bytes(), b'private-token-not-read-or-changed')
        self.assertEqual((self.install / 'sessions/private/bridge.token').read_bytes(), b'private-session-token')
        self.assertEqual((self.install / 'journal-coordination/state.txt').read_bytes(), b'private-coordination')
        self.assertEqual((self.install / 'README.md').read_bytes(), (ROOT / 'docs/installed-README.md').read_bytes())
        self.assertTrue((self.install / 'app/nx-profile/startup/M2Startup.dll').is_file())
        self.assertTrue((self.install / 'app/src/nx_sketch_mcp/v3/service.py').is_file())
        self.assertFalse(list(self.install.glob('.v3-install-stage-*')))

    def test_clean_replace_refuses_token_inside_app(self):
        private = json.loads(self.config_bytes)
        private['token_file'] = str(self.install / 'app/private/credential.token')
        updated = json.dumps(private).encode('utf8')
        (self.install / 'mcp-config.json').write_bytes(updated)
        (self.install / 'app/private/credential.token').write_bytes(b'private-token-inside-app')
        result = self.invoke(clean=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('token must be under the installation root and outside app', result.stderr)
        self.assertEqual((self.install / 'app/private/credential.token').read_bytes(), b'private-token-inside-app')
        self.assertEqual((self.install / 'mcp-config.json').read_bytes(), updated)
        self.assertEqual((self.install / 'app/src/nx_sketch_mcp/server.py').read_bytes(), b'old server sentinel')

    def test_clean_replace_refuses_app_as_regular_file(self):
        app = self.install / 'app'
        app.rename(self.install / 'old-app-fixture')
        app.write_bytes(b'not-an-app-directory')
        result = self.invoke(clean=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('app target must be a directory', result.stderr)
        self.assertEqual(app.read_bytes(), b'not-an-app-directory')
        self.assertEqual((self.install / 'old-app-fixture/private/extra.txt').read_bytes(), b'private-app-sentinel')

    def test_clean_replace_rejects_reparse_tree_without_deleting_target(self):
        if os.name != 'nt': self.skipTest('Windows junction test')
        outside = self.base / 'outside'
        outside.mkdir(); (outside / 'keep.txt').write_bytes(b'outside-kept')
        link = self.install / 'app/linked-dir'
        created = subprocess.run(['pwsh','-NoProfile','-NonInteractive','-Command',
                                  'New-Item -ItemType Junction -Path $env:NX_LINK -Target $env:NX_TARGET | Out-Null'],
                                 env={**os.environ,'NX_LINK':str(link),'NX_TARGET':str(outside)},
                                 capture_output=True, text=True)
        if created.returncode: self.skipTest('Cannot create test junction: ' + created.stderr)
        try:
            result = self.invoke(clean=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Reparse point in old app', result.stderr)
            self.assertEqual((outside / 'keep.txt').read_bytes(), b'outside-kept')
            self.assertEqual((self.install / 'app/src/nx_sketch_mcp/server.py').read_bytes(), b'old server sentinel')
            self.assertEqual((self.install / 'README.md').read_bytes(), b'personal-readme-preserved')
        finally:
            link.rmdir()  # Removes the junction itself; never traverses its target.
        self.assertEqual((outside / 'keep.txt').read_bytes(), b'outside-kept')

    def test_missing_native_dll_rejected_before_replacing_anything(self):
        (self.build / 'ReferenceGeometryNative.dll').unlink()
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ReferenceGeometryNative.dll', result.stderr)
        self.assertEqual((self.install / 'app/src/nx_sketch_mcp/server.py').read_bytes(), b'old server sentinel')
        self.assertEqual((self.install / 'mcp-config.json').read_bytes(), self.config_bytes)

    def test_requested_version_mismatch_rejected_before_install(self):
        result = self.invoke(version='0.0.0')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Requested version differs', result.stderr)
        self.assertEqual((self.install / 'app/src/nx_sketch_mcp/server.py').read_bytes(), b'old server sentinel')
        self.assertEqual((self.install / 'README.md').read_bytes(), b'personal-readme-preserved')
        self.assertFalse(list(self.install.glob('.v3-install-stage-*')))

    def test_unresolved_journal_marker_prevents_replacement(self):
        (self.coordination / 'active.json').write_text('{}', encoding='utf8')
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('active or unresolved', result.stderr)
        self.assertEqual((self.install / 'app/src/nx_sketch_mcp/server.py').read_bytes(), b'old server sentinel')
        self.assertEqual((self.install / 'README.md').read_bytes(), b'personal-readme-preserved')
        self.assertTrue((self.coordination / 'active.json').exists())
        self.assertFalse(list(self.install.glob('.v3-install-stage-*')))

    def test_held_journal_gate_prevents_replacement(self):
        if os.name != 'nt': self.skipTest('Windows file sharing test')
        gate = self.coordination / 'gate.lock'
        gate.write_bytes(b'')
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.CreateFileW(str(gate), 0xC0000000, 0, None, 3, 0x80, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
        try: result = self.invoke()
        finally: kernel.CloseHandle(handle)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('journal coordination gate is held', result.stderr)
        self.assertEqual((self.install / 'app/src/nx_sketch_mcp/server.py').read_bytes(), b'old server sentinel')
        self.assertFalse(list(self.install.glob('.v3-install-stage-*')))

    def test_copy_failure_restores_previously_managed_files(self):
        if os.name != 'nt': self.skipTest('Windows file sharing test')
        target = self.install / 'app/src/nx_sketch_mcp/server.py'
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.CreateFileW(str(target), 0x80000000, 1, None, 3, 0x80, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
        try: result = self.invoke()
        finally: kernel.CloseHandle(handle)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_bytes(), b'old server sentinel')
        self.assertEqual((self.install / 'app/private/extra.txt').read_bytes(), b'private-app-sentinel')
        self.assertEqual((self.install / 'token.txt').read_bytes(), b'private-token-not-read-or-changed')
        self.assertFalse((self.install / 'app/src/nx_sketch_mcp/__init__.py').exists())
        self.assertFalse(list(self.install.glob('.v3-install-stage-*')))


if __name__ == '__main__': unittest.main()
