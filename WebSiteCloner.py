import os
import sys
import json
import time
import requests
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
from colorama import init, Fore, Style

init(autoreset=True)

# ---------------------------------------------------------------------------
# Yardımcı: renkli print
# ---------------------------------------------------------------------------
def info(msg):    print(Fore.LIGHTCYAN_EX + "[i] " + msg)
def ok(msg):      print(Fore.LIGHTGREEN_EX + "[+] " + msg)
def warn(msg):    print(Fore.LIGHTYELLOW_EX + "[!] " + msg)
def err(msg):     print(Fore.LIGHTRED_EX + "[-] " + msg)
def blue(msg):    print(Fore.LIGHTBLUE_EX + msg)


# ---------------------------------------------------------------------------
# Yardımcı: güvenli dosya adı
# ---------------------------------------------------------------------------
def safe_filename(url: str, default: str = "file") -> str:
    parsed = urlparse(url)
    name = (parsed.netloc + parsed.path).strip("/").replace("/", "_")
    if not name:
        name = default
    return name[:180]  # çok uzun isimleri kırp


# ---------------------------------------------------------------------------
# Tarayıcı
# ---------------------------------------------------------------------------
def make_driver(headless: bool = True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)
    # navigator.webdriver izini gizle
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


# ---------------------------------------------------------------------------
# Ana indirme fonksiyonu
# ---------------------------------------------------------------------------
def indir(url: str, headless: bool = True):
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url

    domain = urlparse(url).netloc.replace(":", "_") or "site"
    out_dir = f"dump_{domain}"
    css_dir = os.path.join(out_dir, "css")
    js_dir  = os.path.join(out_dir, "js")
    img_dir = os.path.join(out_dir, "img")
    for d in (out_dir, css_dir, js_dir, img_dir):
        os.makedirs(d, exist_ok=True)

    blue(f"\n=== İndiriliyor: {url} ===\n")
    info(f"Çıktı klasörü: {os.path.abspath(out_dir)}")

    driver = make_driver(headless=headless)
    try:
        driver.get(url)

        # 1) Sayfanın tam yüklenmesini bekle
        try:
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            warn("readyState 'complete' olmadı, yine de devam ediliyor")

        # 2) JS'in son işlerini bitirmesi için kısa bekleme
        time.sleep(3)

        # 3) Nihai HTML
        html = driver.page_source
        with open(os.path.join(out_dir, "page.html"), "w", encoding="utf-8") as f:
            f.write(html)
        ok(f"HTML kaydedildi: {len(html)} karakter")

        # 4) Inline <style>
        inline_css = driver.execute_script("""
            return Array.from(document.querySelectorAll('style'))
                .map(s => s.textContent)
                .join('\\n\\n/* --- yeni style --- */\\n\\n');
        """)
        with open(os.path.join(css_dir, "inline.css"), "w", encoding="utf-8") as f:
            f.write(inline_css)
        ok(f"Inline CSS: {len(inline_css)} karakter")

        # 5) Aynı domain'den erişilebilir CSS kuralları
        same_domain_css = driver.execute_script("""
            return Array.from(document.styleSheets).map(s => {
                try {
                    return Array.from(s.cssRules).map(r => r.cssText).join('\\n');
                } catch (e) { return ''; }
            }).filter(Boolean).join('\\n\\n/* --- yeni stylesheet --- */\\n\\n');
        """)
        with open(os.path.join(css_dir, "same_domain.css"), "w", encoding="utf-8") as f:
            f.write(same_domain_css)
        ok(f"Same-domain CSS: {len(same_domain_css)} karakter")

        soup = BeautifulSoup(html, "html.parser")
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": url,
        }

        # 6) Harici CSS
        css_links = []
        for link in soup.find_all("link", rel="stylesheet"):
            href = link.get("href")
            if not href:
                continue
            css_url = urljoin(url, href)
            css_links.append(css_url)
            try:
                r = requests.get(css_url, headers=headers, timeout=15)
                r.raise_for_status()
                fname = safe_filename(css_url, "style.css")
                if not fname.endswith(".css"):
                    fname += ".css"
                with open(os.path.join(css_dir, fname), "w", encoding="utf-8") as f:
                    f.write(r.text)
                ok(f"CSS: {fname} ({len(r.text)} karakter)")
            except Exception as e:
                warn(f"CSS alınamadı: {css_url} → {e}")

        # 7) Script dosyaları
        script_srcs = []
        for s in soup.find_all("script", src=True):
            src = s.get("src")
            if not src:
                continue
            js_url = urljoin(url, src)
            script_srcs.append(js_url)
            try:
                r = requests.get(js_url, headers=headers, timeout=15)
                r.raise_for_status()
                fname = safe_filename(js_url, "script.js")
                if not fname.endswith(".js"):
                    fname += ".js"
                with open(os.path.join(js_dir, fname), "w", encoding="utf-8") as f:
                    f.write(r.text)
                ok(f"JS: {fname} ({len(r.text)} karakter)")
            except Exception as e:
                warn(f"JS alınamadı: {js_url} → {e}")

        # 8) Input alanları (siteye özel selector yok, genel tarama)
        inputs = []
        for el in driver.find_elements(By.TAG_NAME, "input"):
            inputs.append({
                "name": el.get_attribute("name"),
                "id": el.get_attribute("id"),
                "type": el.get_attribute("type"),
                "placeholder": el.get_attribute("placeholder"),
                "aria-label": el.get_attribute("aria-label"),
                "autocomplete": el.get_attribute("autocomplete"),
                "value": el.get_attribute("value"),
                "maxlength": el.get_attribute("maxlength"),
                "required": el.get_attribute("required") is not None,
                "disabled": el.get_attribute("disabled") is not None,
                "class": el.get_attribute("class"),
            })
        with open(os.path.join(out_dir, "inputs.json"), "w", encoding="utf-8") as f:
            json.dump(inputs, f, indent=2, ensure_ascii=False)
        ok(f"{len(inputs)} input alanı kaydedildi")
        for i, inp in enumerate(inputs, 1):
            print(f"    {i}. name={inp['name']!r} type={inp['type']!r} "
                  f"placeholder={inp['placeholder']!r}")

        # 9) Formlar
        forms = []
        for f in soup.find_all("form"):
            forms.append({
                "action": f.get("action"),
                "method": f.get("method"),
                "inputs": [i.get("name") for i in f.find_all("input")],
            })
        with open(os.path.join(out_dir, "forms.json"), "w", encoding="utf-8") as f:
            json.dump(forms, f, indent=2, ensure_ascii=False)

        # 10) Linkler
        links = []
        for a in soup.find_all("a", href=True):
            links.append({
                "href": urljoin(url, a["href"]),
                "text": a.get_text(strip=True)[:80],
            })
        with open(os.path.join(out_dir, "links.json"), "w", encoding="utf-8") as f:
            json.dump(links, f, indent=2, ensure_ascii=False)
        ok(f"{len(links)} link kaydedildi")

        # 11) Özet
        summary = {
            "url": driver.current_url,
            "title": driver.title,
            "html_length": len(html),
            "inline_css_length": len(inline_css),
            "same_domain_css_length": len(same_domain_css),
            "css_files": css_links,
            "script_files": script_srcs,
            "input_count": len(inputs),
            "form_count": len(forms),
            "link_count": len(links),
            "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        blue(f"\n=== Tamamlandı ===")
        print(f"HTML    : {summary['html_length']} karakter")
        print(f"CSS     : {len(css_links)} dosya + inline {summary['inline_css_length']} krkt")
        print(f"JS      : {len(script_srcs)} dosya")
        print(f"Input   : {len(inputs)}")
        print(f"Form    : {len(forms)}")
        print(f"Link    : {len(links)}")
        print(f"Klasör  : {os.path.abspath(out_dir)}")

    finally:
        driver.quit()


# ---------------------------------------------------------------------------
# Menü
# ---------------------------------------------------------------------------
def menu():
    while True:
        blue("\n╔══════════════════════════════════════╗")
        blue("║       WebSite İndirici v1.0          ║")
        blue("╚══════════════════════════════════════╝")
        print("  1) Site indir (headless)")
        print("  2) Site indir (tarayıcı görünür)")
        print("  3) Çıkış")
        secim = input("Seçim: ").strip()

        if secim == "1":
            url = input("URL: ").strip()
            if not url:
                warn("URL boş")
                continue
            try:
                indir(url, headless=True)
            except Exception as e:
                err(f"Hata: {e}")

        elif secim == "2":
            url = input("URL: ").strip()
            if not url:
                warn("URL boş")
                continue
            try:
                indir(url, headless=False)
            except Exception as e:
                err(f"Hata: {e}")

        elif secim == "3":
            blue("Görüşürüz.")
            break
        else:
            warn("Geçersiz seçim")


if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        blue("\nÇıkılıyor...")
        sys.exit(0)