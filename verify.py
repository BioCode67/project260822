#!/usr/bin/env python3
"""verify.py — 되감기 데모 모드 회귀 검증

기대값 (CLAUDE.md 2절 "검증된 동작"):
  reps   = 8
  depth  = 6 / 8
  shots  = 4
  errors = none

사용: python3 verify.py [index.html 경로]
"""
import glob, os, sys
from playwright.sync_api import sync_playwright

def chromium_path():
    """번들 chromium 경로. 환경에 미리 설치된 빌드를 찾아 쓴다(없으면 기본값)."""
    for pat in ("/opt/pw-browsers/chromium-*/chrome-linux/chrome",
                os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome")):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None

TARGET = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "index.html")
# 종목별 시연 시나리오 기대값 (모두 결정적이다)
CASES = [
    ("스쿼트", "squat",  {"reps": "8", "depth": "6 / 8", "shots": 4}),
    ("푸시업", "pushup", {"reps": "8", "depth": "4 / 8", "shots": 2}),
]

with sync_playwright() as p:
    exe = chromium_path()
    b = p.chromium.launch(args=["--no-sandbox"], **({"executable_path": exe} if exe else {}))
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs, net = [], []          # errs = JS 런타임 오류 / net = 리소스 로드 실패(폰트 CDN 등)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: net.append(m.text) if m.type == "error" else None)
    pg.goto("file://" + TARGET)
    pg.wait_for_timeout(1500)

    ok = True
    for label, key, expect in CASES:
        pg.click('.exsel .ex[data-ex="%s"]' % key)
        pg.wait_for_timeout(250)
        pg.click("#demoBtn")
        # 세트 종료(8회)까지 대기. 문서상 약 20초.
        try:
            pg.wait_for_function("() => document.getElementById('repN').textContent === '8'", timeout=45000)
        except Exception:
            pass
        pg.wait_for_timeout(800)

        got = {"reps":  pg.inner_text("#repN"),
               "depth": pg.inner_text("#depthRate"),
               "shots": pg.eval_on_selector_all(".shot", "e=>e.length")}
        print("[%s]" % label)
        print("  reps  ", got["reps"],  " (기대 %s)" % expect["reps"])
        print("  depth ", got["depth"], " (기대 %s)" % expect["depth"])
        print("  shots ", got["shots"], " (기대 %s)" % expect["shots"])
        print("  chal  ", pg.inner_text("#chalScore"), " (참고값, 합/불 판정 대상 아님)")
        for k, v in expect.items():
            if got[k] != v:
                print("  ✗ %s: 기대 %r → 실제 %r" % (k, v, got[k]))
                ok = False

    print("errors", errs or "none")
    if net:
        print("       (참고) 차단된 외부 리소스 %d건 — 폰트 CDN. 계측/시연 동작과 무관." % len(net))
    ok = ok and not errs
    print("\nRESULT:", "PASS" if ok else "FAIL")
    b.close()
    sys.exit(0 if ok else 1)
