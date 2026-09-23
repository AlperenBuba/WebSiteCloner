# WebSiteCloner

A Selenium-based console application that archives the current state of a given URL locally, including HTML, CSS, JavaScript, forms, and input field information.

---

## 📖 Table of Contents

- [Features](#-features)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Usage](#-usage)
- [Output Structure](#-output-structure)
- [How It Works](#-how-it-works)
- [Limitations](#-limitations)
- [Legal Notice](#-legal-notice)
- [License](#-license)
- [Contributing](#-contributing)
- [Contact](#-contact)

---

## ✨ Features

- 🎯 **No site-specific selectors** — works on any site, no maintenance required.
- 🌐 **JavaScript-aware** — uses a real Chrome browser via Selenium; captures the final DOM of SPAs built with React, Vue, Angular, etc.
- 📄 **HTML** — the current DOM of the page (`page.html`).
- 🎨 **CSS** — inline `<style>` blocks, same-domain CSS rules, and external CSS files are saved separately.
- 📜 **JavaScript** — downloads all external `.js` files referenced by the page.
- 📝 **Input & form analysis** — extracts all input fields and forms as JSON.
- 🔗 **Link inventory** — records all links on the page with their target URLs and visible text.
- 📊 **Summary report** — generates `summary.json` for each download.
- 🎭 **Bot detection mitigation** — hides `navigator.webdriver`, uses a realistic User-Agent.
- 🖥️ **Two modes** — headless (background) and visible browser (for debugging).
- 🌈 **Colorized console output** — readable logs via `colorama`.
- 🖱️ **Simple menu interface** — no need to memorize commands.

---

## 📋 Requirements

- **Python** 3.9 or higher
- **Google Chrome** (latest version)
- **ChromeDriver** — Selenium 4.6+ downloads it automatically, no manual setup needed
- Operating system: **Windows, macOS, Linux** (tested on all three)

### Python packages

```
selenium
requests
beautifulsoup4
colorama
```

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/username/WebSiteCloner.git
cd WebSiteCloner
```

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

or individually:

```bash
pip install selenium requests beautifulsoup4 colorama
```

---

## 🎮 Usage

```bash
python3 WebSiteCloner.py
```

You will be greeted with the following menu:

```
╔══════════════════════════════════════╗
║       Website Downloader v1.0        ║
╚══════════════════════════════════════╝
  1) Download site (headless)
  2) Download site (visible browser)
  3) Exit
Choice:
```

- **Option 1:** The browser runs in the background; no window opens. Use this for normal operation.
- **Option 2:** The browser opens visibly. Use this if the site loads slowly, you're getting errors, or you want to see what's happening.
- **Option 3:** Exit the program.

It will then prompt you for a **URL**:

```
URL: https://example.com
```

The download starts and logs are printed step by step to the console:

```
=== Downloading: https://example.com ===

[i] Output folder: /Users/alperen/WebSiteCloner/dump_example.com
[+] HTML saved: 45231 characters
[+] Inline CSS: 1204 characters
[+] Same-domain CSS: 8312 characters
[+] CSS: example.com_style.css (2048 characters)
[+] JS: example.com_app.js (15234 characters)
[+] 3 input fields saved
    1. name='q' type='text' placeholder='Search...'
    2. name='email' type='email' placeholder='Email'
    3. name='password' type='password' placeholder='Password'
[+] 42 links saved

=== Done ===
HTML    : 45231 characters
CSS     : 1 file + inline 1204 chars
JS      : 1 file
Input   : 3
Form    : 1
Link    : 42
Folder  : /Users/alperen/WebSiteCloner/dump_example.com
```

---

## 📁 Output Structure

Each download is saved in a separate folder named after the target domain:

```
dump_example.com/
├── page.html          # Final DOM of the page
├── inputs.json        # Details of all <input> fields
├── forms.json         # All <form> elements and their inputs
├── links.json         # All links on the page (href + text)
├── summary.json       # Download summary (URL, title, file counts, etc.)
├── css/
│   ├── inline.css                 # <style> blocks
│   ├── same_domain.css            # CSS rules readable from same domain
│   └── example.com_style.css      # External CSS files
└── js/
    └── example.com_app.js         # External JS files
```

### `summary.json` example

```json
{
  "url": "https://example.com/",
  "title": "Example Domain",
  "html_length": 45231,
  "inline_css_length": 1204,
  "same_domain_css_length": 8312,
  "css_files": ["https://example.com/style.css"],
  "script_files": ["https://example.com/app.js"],
  "input_count": 3,
  "form_count": 1,
  "link_count": 42,
  "downloaded_at": "2026-09-23 14:32:11"
}
```

---

## ⚙️ How It Works

1. **Browser is launched** — Selenium opens Chrome. The `navigator.webdriver` fingerprint is hidden via CDP, and a realistic User-Agent is set.
2. **URL is loaded** — `driver.get(url)` is called.
3. **Waits until the page is ready** — waits until `document.readyState === 'complete'`, then waits an additional 3 seconds for JS to finish.
4. **Final DOM is captured** — the HTML as seen by the browser is retrieved via `driver.page_source`.
5. **CSS/JS is extracted** — inline `<style>`, `document.styleSheets`, and `<link rel="stylesheet">` / `<script src>` tags are scanned. External files are downloaded with `requests`.
6. **Form/input/link analysis** — the page structure is dumped to JSON using BeautifulSoup and Selenium.
7. **Summary is written** — `summary.json` is generated.
8. **Browser is closed** — `driver.quit()` is called in the `finally` block.

---

## ⚠️ Limitations

This tool **does not perfectly clone every site**. It may return incomplete or incorrect results in the following cases:

- **Login walls:** Pages that require authentication (Instagram, Facebook, banking sites, etc.) only return the skeleton of the login screen.
- **Anti-bot protections:** On sites with Cloudflare, CAPTCHA, or behavioral analysis, the page may come back empty or you may be blocked.
- **CORS:** CSS rules loaded from a different domain cannot be read via JS (`same_domain.css` may be empty). Those files are downloaded separately via `requests`, but may sometimes be inaccessible.
- **Infinite scroll:** Only the first screen is loaded; content brought in by "load more" is not captured.
- **Signed media URLs:** Image/video CDNs may use signed and time-limited URLs; even if downloaded, they may expire shortly.
- **Single page:** It does **not** automatically follow subpages of the given URL. Links are recorded in `links.json` but not downloaded.
- **Dynamic styles:** CSS loaded via `fetch` after page load may sometimes be missed.

---

## ⚖️ Legal Notice

This tool is designed for **personal archiving, design inspection, UI/UX learning, and educational purposes**.

**Do NOT:**

- Clone the fetched HTML/CSS/JS and **publish it as another website**
- Collect usernames/passwords or perform **phishing**
- Redistribute copyrighted content **without permission**
- Process personal data **outside the scope of GDPR / KVKK**

Such actions are **crimes** under the **Turkish Penal Code** (TCK 158, 243–245), **Law No. 5846 on Intellectual and Artistic Works (FSEK)**, and **KVKK**. Responsibility for use rests entirely with the user.

Before scraping, check the target site's **`robots.txt`** file and **Terms of Service**. Sending excessive requests can overload the server and result in an IP ban.

---

## 📜 License

This project is released under a **custom "Source-Available" license**. See the `LICENSE.md` file for details.

In short:
- ✅ You may read, inspect, and learn from the source code.
- ❌ You may not copy, use, modify, or distribute it.

---

## 🤝 Contributing

Before contributing, please open an **issue** describing what you'd like to change. Pull requests will be reviewed.

---

## 📬 Contact

- **Developer:** Alperen [Last Name]
- **Email:** example@example.com
- **GitHub:** [@username](https://github.com/username)

---

**Version:** 1.0.0
**Last updated:** September 2026