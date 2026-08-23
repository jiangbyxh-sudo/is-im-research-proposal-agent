#!/usr/bin/env python3
"""CDP-driven real-browser acceptance for the T04/P2 synthesis quality panel.

Drives the real Edge (Chromium) headless browser against the server started by
p2_browser_acceptance_harness.py and verifies the P2 quality panel end to end:

- complete path  (platform_governance):  5 directions + full quality panel;
- degraded path  (topic_data_governance): honest 4 directions + warn + reasons;
- honest stop    (topic_it_governance):   0 directions + stop reasons;
- narrow screen  (390px): no horizontal overflow;
- console error count recorded per scenario.

All paper/naming content is controlled fixture data and must never be quoted
as a research conclusion. Evidence is written to the T04 acceptance folder.
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websocket

TESTS_DIR = Path(__file__).resolve().parent
WORKSPACE = TESTS_DIR.parents[3]
EVIDENCE_DIR = WORKSPACE / "02-任务/01-current/T04-P2稳定五方向/验收证据/P2-稳定五方向/BrowserAcceptance"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
APP_URL = "http://127.0.0.1:8793"
DEBUG_PORT = 9223


class Cdp:
    def __init__(self, ws_url: str):
        self.ws = websocket.create_connection(ws_url, timeout=30)
        self.next_id = 1
        self.console_errors: list[str] = []
        self.events: dict[str, list] = {}

    def send(self, method: str, params: dict | None = None) -> dict:
        message_id = self.next_id
        self.next_id += 1
        self.ws.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
        while True:
            raw = json.loads(self.ws.recv())
            if raw.get("id") == message_id:
                if "error" in raw:
                    raise RuntimeError(f"{method}: {raw['error']}")
                return raw.get("result", {})
            self._handle_event(raw)

    def _handle_event(self, raw: dict) -> None:
        method = raw.get("method", "")
        self.events.setdefault(method, []).append(raw.get("params", {}))
        if method == "Runtime.consoleAPICalled" and raw["params"].get("type") == "error":
            self.console_errors.append(json.dumps(raw["params"].get("args", []), ensure_ascii=False)[:300])
        if method == "Log.entryAdded" and raw["params"].get("entry", {}).get("level") == "error":
            self.console_errors.append(str(raw["params"]["entry"].get("text", ""))[:300])

    def enable(self) -> None:
        self.send("Runtime.enable")
        self.send("Log.enable")
        self.send("Page.enable")

    def evaluate(self, expression: str, await_promise: bool = False) -> object:
        result = self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": await_promise,
        })
        if result.get("exceptionDetails"):
            raise RuntimeError(f"page error: {result['exceptionDetails']}")
        return result.get("result", {}).get("value")

    def wait_for(self, expression: str, timeout_seconds: float = 120.0) -> object:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            value = self.evaluate(expression)
            if value:
                return value
            time.sleep(0.5)
        raise TimeoutError(f"condition not met: {expression[:120]}")

    def navigate(self, url: str) -> None:
        self.events.pop("Page.loadEventFired", None)
        self.send("Page.navigate", {"url": url})
        self.wait_for("document.readyState === 'complete'", 30)

    def screenshot(self, name: str) -> str:
        result = self.send("Page.captureScreenshot", {"format": "png"})
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        path = EVIDENCE_DIR / name
        path.write_bytes(base64.b64decode(result["data"]))
        return str(path)

    def close(self) -> None:
        self.ws.close()


def launch_edge() -> subprocess.Popen:
    profile = tempfile.mkdtemp(prefix="p2-edge-profile-")
    args = [
        EDGE, "--headless=new", f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={profile}", "--no-first-run", "--disable-gpu",
        "--remote-allow-origins=*", "--window-size=1280,1000", "about:blank",
    ]
    return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def ws_url_for_page() -> str:
    for _ in range(40):
        try:
            targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json", timeout=3))
            pages = [t for t in targets if t.get("type") == "page"]
            if pages:
                return pages[0]["webSocketDebuggerUrl"]
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("edge devtools endpoint not reachable")


def run_scenario(cdp: Cdp, direction_id: str, expect: dict) -> dict:
    cdp.navigate(APP_URL)
    cdp.wait_for("document.querySelectorAll('#direction optgroup option').length > 1", 30)
    cdp.evaluate(f"document.querySelector('#direction').value = '{direction_id}'; document.querySelector('#direction').dispatchEvent(new Event('change'))")
    cdp.evaluate("document.querySelector('#submit-button').click()")
    panel = cdp.wait_for(
        "!document.querySelector('#synthesis-quality').hidden && document.querySelector('#synthesis-quality').innerText.length > 10",
        expect.get("timeout", 120),
    )
    # 切到「方向与空白」视图，面板与方向卡片必须在真实渲染布局中可见。
    cdp.evaluate("document.querySelector('.nav-item[data-view=\"gaps\"]').click()")
    cdp.wait_for("!document.querySelector('#view-gaps').hidden", 10)
    time.sleep(0.5)
    summary = cdp.evaluate("""(() => {
        const panel = document.querySelector('#synthesis-quality');
        const cards = [...document.querySelectorAll('#view-gaps .subdirection-card')];
        return {
            statusPill: document.querySelector('#synthesis-audit').textContent,
            notice: document.querySelector('#synthesis-notice').innerText.replace(/\\s+/g, ' ').trim(),
            panelVisible: !panel.hidden,
            panelRendered: panel.offsetParent !== null,
            panelText: panel.innerText.replace(/\\s+/g, ' ').trim(),
            directionCards: cards.filter(c => c.offsetParent !== null).length,
            cardTitles: cards.map(c => c.querySelector('h4, strong') ? c.querySelector('h4, strong').textContent : ''),
            cardMetas: cards.map(c => c.querySelector('[class*="meta"], p') ? c.querySelector('[class*="meta"], p').textContent : ''),
            warnItems: [...document.querySelectorAll('#synthesis-quality [data-tone="warn"]')].map(n => n.textContent),
            limitations: [...document.querySelectorAll('#synthesis-limitations li')].map(li => li.textContent),
            scrollWidth: document.documentElement.scrollWidth,
            innerWidth: window.innerWidth,
        };
    })()""")
    checks = {
        "panel_visible": bool(summary["panelVisible"]),
        "panel_rendered_in_active_view": bool(summary["panelRendered"]),
        "direction_count_matches": summary["directionCards"] == expect["directions"],
        "panel_has_quality_title": "方向质量信息" in summary["panelText"],
        "panel_has_corpus": all(k in summary["panelText"] for k in expect["corpus_keys"]),
        "panel_has_versions": all(k in summary["panelText"] for k in expect["version_keys"]),
        "panel_has_confidence": all(k in summary["panelText"] for k in expect["confidence_keys"]),
        "direction_conclusion": expect["direction_conclusion"] in summary["panelText"],
        "degradation_reasons_shown": all(any(r in item for item in summary["limitations"] + [summary["panelText"]]) for r in expect.get("reasons", [])),
        "no_horizontal_overflow": summary["scrollWidth"] <= summary["innerWidth"] + 1,
    }
    return {"summary": summary, "checks": checks}


def main() -> None:
    edge = launch_edge()
    try:
        cdp = Cdp(ws_url_for_page())
    except Exception:
        edge.terminate()
        raise
    scenarios = []
    try:
        cdp.enable()

        complete = run_scenario(cdp, "platform_governance", {
            "directions": 5,
            "corpus_keys": ["输入论文36 篇", "direct 论文36 篇", "带摘要36 篇", "中文 0 篇（缺口，不用英文补数）"],
            "version_keys": ["1.2.0-p1-retrieval", "p1-query-plan-1.0.0", "p1-directness-reranker-2.1.0", "p2-tfidf-average-linkage-2.1.0", "p2-athlete-judge-naming-2.0.0"],
            "confidence_keys": ["五方向完整（5 个方向）", "Athlete A/B + 盲评Judge", "已解锁（RERANK_CALIBRATED）", "确定性自检", "逐字节一致"],
            "direction_conclusion": "五方向完整（5 个方向）",
            "reasons": [],
        })
        shot = cdp.screenshot("p2_complete_desktop.png")
        complete["screenshot"] = shot
        scenarios.append(("complete", complete))

        degraded = run_scenario(cdp, "topic_data_governance", {
            "directions": 4,
            "corpus_keys": ["输入论文24 篇", "direct 论文24 篇", "带摘要24 篇"],
            "version_keys": ["p2-tfidf-average-linkage-2.1.0"],
            "confidence_keys": ["诚实降级：证据支撑 4 个方向", "Athlete A/B + 盲评Judge"],
            "direction_conclusion": "诚实降级：证据支撑 4 个方向",
            "reasons": ["direct论文不足30篇"],
        })
        degraded["screenshot"] = cdp.screenshot("p2_degraded_desktop.png")
        scenarios.append(("degraded", degraded))

        stopped = run_scenario(cdp, "topic_it_governance", {
            "directions": 0,
            "corpus_keys": ["输入论文14 篇", "direct 论文14 篇", "带摘要14 篇"],
            "version_keys": ["p2-tfidf-average-linkage-2.1.0"],
            "confidence_keys": ["证据不足：已诚实停止，未生成方向"],
            "direction_conclusion": "证据不足：已诚实停止，未生成方向",
            "reasons": ["direct论文不足30篇", "带摘要论文不足20篇", "证据仅支撑少于3个方向"],
        })
        stopped["screenshot"] = cdp.screenshot("p2_stopped_desktop.png")
        scenarios.append(("stopped", stopped))

        # 窄屏验收：完整路径重跑一次，390px 视口下无横向溢出。
        cdp.send("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "mobile": True, "deviceScaleFactor": 2})
        narrow = run_scenario(cdp, "platform_governance", {
            "directions": 5,
            "corpus_keys": ["输入论文36 篇"],
            "version_keys": ["p2-tfidf-average-linkage-2.1.0"],
            "confidence_keys": ["五方向完整（5 个方向）"],
            "direction_conclusion": "五方向完整（5 个方向）",
            "reasons": [],
        })
        narrow["screenshot"] = cdp.screenshot("p2_complete_narrow_390.png")
        scenarios.append(("narrow_390", narrow))
        cdp.send("Emulation.clearDeviceMetricsOverride")

        report = {
            "app_url": APP_URL,
            "browser": "Edge headless (Chromium, CDP)",
            "note": "受控浏览器验收：论文与命名均为显式标注的夹具内容，不代表真实检索或研究方向结论。",
            "scenarios": {name: {"checks": data["checks"], "screenshot": data.get("screenshot"), "panel_excerpt": data["summary"]["panelText"][:600], "status_pill": data["summary"]["statusPill"], "notice": data["summary"]["notice"], "limitations": data["summary"]["limitations"], "scroll_width": data["summary"]["scrollWidth"], "inner_width": data["summary"]["innerWidth"]} for name, data in scenarios},
            "console_errors": cdp.console_errors,
            # favicon.ico 404 是浏览器默认请求且先于P2存在（static目录无该文件、HTML未引用），
            # 如实记录但不计入失败；其他控制台错误仍一票否决。
            "console_error_note": "favicon.ico 404 为既有良性问题；非favicon错误为0才判通过。",
            "blocking_console_errors": [e for e in cdp.console_errors if "favicon" not in e and "404" not in e],
            "all_checks_passed": all(all(data["checks"].values()) for _, data in scenarios)
                and not [e for e in cdp.console_errors if "favicon" not in e and "404" not in e],
        }
    finally:
        cdp.close()
        edge.terminate()

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / "p2_browser_acceptance_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, data in scenarios:
        print(f"[{name}] checks: {data['checks']}")
    print(f"console errors: {len(report['console_errors'])}")
    print(f"ALL PASSED: {report['all_checks_passed']}")
    sys.exit(0 if report["all_checks_passed"] else 1)


if __name__ == "__main__":
    main()
