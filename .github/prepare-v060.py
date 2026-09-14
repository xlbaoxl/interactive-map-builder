from pathlib import Path
import base64, hashlib, json, os, subprocess, urllib.request

VERSION = '0.6.0'
DATE = '2026-09-15'
BASE = '39130597f6cfa74cac2be68d95dcc483ad96a3fd'

def git(*args):
    return subprocess.check_output(['git', *args]).decode().strip()

def replace(path, old, new):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    assert text.count(old) == 1, (path, old)
    p.write_text(text.replace(old, new), encoding='utf-8')

assert git('rev-parse', 'HEAD') == BASE
replace('pyproject.toml', 'version = "0.5.1"', 'version = "0.6.0"')
replace('scripts/mapcore/version.py', '__version__ = "0.5.1"', '__version__ = "0.6.0"')
replace('CHANGELOG.md', '## [Unreleased] / 未发布\n', '## [Unreleased] / 未发布\n\n## [0.6.0] - ' + DATE + '\n')
replace('CHANGELOG.md', '\n## [0.5.1]', '''
### Release and upgrade / 发布与升级

- 正式发布 v0.6.0；MapSpec 保持 1.1，已有地图需重新构建才能获得分享入口。
  Release v0.6.0 while retaining MapSpec 1.1. Rebuild existing maps to add the Share view control.
- 全新安装读取 Excel 时使用 `python -m pip install ".[excel]"`；已安装的 Excel 读取器继续有效。
  Fresh source/Skill installations that read Excel use `python -m pip install ".[excel]"`.
  Existing Excel readers remain usable after upgrading.
- 发布前验证发行包校验和、清单和干净环境安装，发布后重新下载官方附件进行相同校验。
  Verify checksums, manifests, and clean installation before publishing; download the official
  assets again after publishing and repeat integrity and installation checks.

## [0.5.1]''')
replace('README.md', '## Quick start\n', '''## Current release: v0.6.0

This release combines leaner command startup, intent-resolved first builds, and **Share view**
HTML/JSON handoff. MapSpec stays at 1.1. Rebuild existing maps to add the sharing control;
filters and hidden layers do not remove embedded data from shared HTML.
For a new installation that reads Excel, install `.[excel]`; existing Excel readers remain usable.
See [release notes](https://github.com/xlbaoxl/interactive-map-builder/releases/tag/v0.6.0).

## Quick start
''')
replace('README.zh-CN.md', '## 快速开始\n', '''## 当前版本：v0.6.0

本版整合命令启动优化、明确意图直接构建和“分享当前视图”HTML／JSON 交付。
MapSpec 保持 1.1；已有地图需重新构建才能获得分享入口。筛选和隐藏图层不会删除分享 HTML
中的内嵌数据。全新安装需要读取 Excel 时安装 `.[excel]`，已安装的 Excel 读取器继续有效。
详见[正式发布说明](https://github.com/xlbaoxl/interactive-map-builder/releases/tag/v0.6.0)。

## 快速开始
''')
replace('tests/test_distribution.py', 'from build_skill_package import build_skill_package', 'from build_skill_package import build_skill_package, project_version')
replace('tests/test_distribution.py', '    assert package_version() == __version__', '    assert project_version() == __version__\n    assert package_version() == __version__')
replace('tests/test_distribution.py', '        "interactive-map-builder/scripts/mapcore/version.py",', '''        "interactive-map-builder/scripts/mapcore/version.py",
        "interactive-map-builder/scripts/mapcore/arguments.py",
        "interactive-map-builder/scripts/mapcore/resources/templates/view-state.js",
        "interactive-map-builder/scripts/mapcore/resources/templates/view-state.css",
        "interactive-map-builder/references/view-state.md",''')

workflow = Path('.github/workflows/release.yml')
text = workflow.read_text(encoding='utf-8')
text = text.replace('permissions:\n  contents: write\n', 'permissions:\n  contents: write\n\nconcurrency:\n  group: release\n  cancel-in-progress: false\n', 1)
text = text.replace('github.event.workflow_run.conclusion == \'success\' &&', "github.event.workflow_run.event == 'push' &&\n       github.event.workflow_run.conclusion == 'success' &&", 1)
text = text.replace('          print(data["project"]["version"])', '''          import ast
          version = data["project"]["version"]
          module = ast.parse(Path("scripts/mapcore/version.py").read_text(encoding="utf-8"))
          engine = next(ast.literal_eval(node.value) for node in module.body
                        if isinstance(node, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets))
          assert version == engine, "Package and engine versions differ"
          print(version)''', 1)
# Generate user-facing release notes and a dependency-free integrity checker.
marker = '      - name: Build release assets\n'
assert text.count(marker) == 1
text = text.replace(marker, '''      - name: Prepare release notes and asset integrity checker
        env:
          VERSION: ${{ steps.version.outputs.version }}
        run: |
          python - <<'PYNOTES'
          import os, re
          from pathlib import Path
          text = Path("CHANGELOG.md").read_text(encoding="utf-8")
          version = re.escape(os.environ["VERSION"])
          section = re.search(r"^## \\[" + version + r"\\][^\\n]*\\n(.*?)(?=^## |\\Z)", text, re.M | re.S)
          assert section and section.group(1).strip(), "Versioned release notes are missing"
          Path(os.environ["RUNNER_TEMP"], "release-notes.md").write_text(section.group(1).strip() + "\\n", encoding="utf-8")
          PYNOTES
          cat > "$RUNNER_TEMP/verify-release.py" <<'PYVERIFY'
          import ast, hashlib, json, sys, tarfile, zipfile
          from pathlib import Path
          root, version = Path(sys.argv[1]), sys.argv[2]
          skill_name = f"interactive-map-builder-skill-v{version}.zip"
          wheel_name = f"interactive_map_builder-{version}-py3-none-any.whl"
          source_name = f"interactive_map_builder-{version}.tar.gz"
          expected = {skill_name, wheel_name, source_name}
          lines = (root / "SHA256SUMS.txt").read_text().splitlines()
          sums = {}
          for line in lines:
              digest, name = line.split(maxsplit=1)
              name = name.lstrip("*")
              assert name in expected and name not in sums, "Unexpected checksum entry"
              assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
              sums[name] = digest
          assert set(sums) == expected, "Missing checksum entry"
          with zipfile.ZipFile(root / skill_name) as skill, zipfile.ZipFile(root / wheel_name) as wheel:
              prefix = "interactive-map-builder/"
              manifest = json.loads(skill.read(prefix + "PACKAGE_MANIFEST.json"))
              assert manifest["name"] == "interactive-map-builder" and manifest["version"] == version
              paths = [entry["path"] for entry in manifest["files"]]
              assert len(paths) == len(set(paths))
              names = skill.namelist()
              assert len(names) == len(set(names))
              assert set(names) == {prefix + p for p in paths} | {prefix + "PACKAGE_MANIFEST.json"}
              for entry in manifest["files"]:
                  data = skill.read(prefix + entry["path"])
                  assert len(data) == entry["bytes"]
                  assert hashlib.sha256(data).hexdigest() == entry["sha256"], entry["path"]
                  if entry["path"].startswith("scripts/"):
                      assert data == wheel.read(entry["path"][8:]), entry["path"]
              code = ast.parse(skill.read(prefix + "scripts/mapcore/version.py"))
              engine = next(ast.literal_eval(n.value) for n in code.body if isinstance(n, ast.Assign)
                            and any(isinstance(t, ast.Name) and t.id == "__version__" for t in n.targets))
              assert engine == version
              if tuple(map(int, version.split("."))) >= (0, 6, 0):
                  assert {"scripts/mapcore/arguments.py", "scripts/mapcore/resources/templates/view-state.js",
                          "scripts/mapcore/resources/templates/view-state.css", "references/view-state.md"} <= set(paths)
              with tarfile.open(root / source_name) as source:
                  metadata = source.extractfile(f"interactive_map_builder-{version}/pyproject.toml")
                  assert metadata and metadata.read() == skill.read(prefix + "pyproject.toml")
          print(json.dumps({"status": "pass", "version": version, "sha256": sums, "manifest_files": len(paths)}, indent=2))
          PYVERIFY

''' + marker, 1)
marker = '      - name: Create GitHub Release\n'
assert text.count(marker) == 1
text = text.replace(marker, '''      - name: Verify candidate assets and clean wheel installation
        if: steps.existing.outputs.state != 'complete'
        env:
          VERSION: ${{ steps.version.outputs.version }}
        run: |
          set -euo pipefail
          python "$RUNNER_TEMP/verify-release.py" dist "$VERSION"
          python -m venv "$RUNNER_TEMP/imb-candidate"
          "$RUNNER_TEMP/imb-candidate/bin/python" -m pip install dist/*.whl
          cd "$RUNNER_TEMP"
          test "$("$RUNNER_TEMP/imb-candidate/bin/interactive-map-builder" --version)" = "$VERSION"
          "$RUNNER_TEMP/imb-candidate/bin/interactive-map-builder" doctor

''' + marker, 1)
text = text.replace('            --generate-notes \\\n', '            --notes-file "$RUNNER_TEMP/release-notes.md" \\\n', 1)
text += '''
      - name: Download and verify the published assets
        env:
          VERSION: ${{ steps.version.outputs.version }}
          TAG: ${{ steps.version.outputs.tag }}
        run: |
          set -euo pipefail
          PUBLISHED="$RUNNER_TEMP/imb-published"
          mkdir -p "$PUBLISHED"
          gh release download "$TAG" --dir "$PUBLISHED" \\
            --pattern '*.whl' --pattern '*.tar.gz' \\
            --pattern "interactive-map-builder-skill-v${VERSION}.zip" --pattern 'SHA256SUMS.txt'
          python "$RUNNER_TEMP/verify-release.py" "$PUBLISHED" "$VERSION" | tee "$PUBLISHED/verification.json"
          python -m venv "$RUNNER_TEMP/imb-published-install"
          "$RUNNER_TEMP/imb-published-install/bin/python" -m pip install "$PUBLISHED"/*.whl
          cd "$RUNNER_TEMP"
          test "$("$RUNNER_TEMP/imb-published-install/bin/interactive-map-builder" --version)" = "$VERSION"
          "$RUNNER_TEMP/imb-published-install/bin/interactive-map-builder" doctor | tee "$PUBLISHED/doctor.json"

      - name: Retain verified published assets for audit
        uses: actions/upload-artifact@v4
        with:
          name: verified-release-${{ steps.version.outputs.tag }}
          path: ${{ runner.temp }}/imb-published/
          if-no-files-found: error
          retention-days: 7
'''
workflow.write_text(text, encoding='utf-8')
paths = ['pyproject.toml', 'scripts/mapcore/version.py', 'CHANGELOG.md', 'README.md', 'README.zh-CN.md', 'tests/test_distribution.py', '.github/workflows/release.yml']
subprocess.run(['git', 'add', '--', *paths], check=True)
subprocess.run(['git', 'diff', '--cached', '--check'], check=True)
assert set(git('diff', '--cached', '--name-only').splitlines()) == set(paths)
entries = []
for path in paths:
    data = Path(path).read_bytes()
    request = urllib.request.Request(
        'https://api.github.com/repos/' + os.environ['GITHUB_REPOSITORY'] + '/git/blobs',
        data=json.dumps({'content': base64.b64encode(data).decode(), 'encoding': 'base64'}).encode(),
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json'},
        method='POST')
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.load(response)
    assert result['sha'] == git('hash-object', path)
    entries.append({'path': path, 'mode': git('ls-files', '--stage', '--', path).split()[0], 'type': 'blob', 'sha': result['sha']})
output = Path(os.environ['RUNNER_TEMP']) / 'imb-release-prepared'
output.mkdir()
tree = git('write-tree')
(output / 'candidate.json').write_text(json.dumps({'base': BASE, 'tree': tree, 'entries': entries}, indent=2))
subprocess.run(['git', 'archive', '--format=tar', '-o', str(output / 'source.tar'), tree], check=True)
print('RELEASE_CANDIDATE=' + json.dumps({'tree': tree, 'entries': entries}))
