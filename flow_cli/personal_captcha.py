"""
Local browser reCAPTCHA token acquisition for personal mode.
"""

from typing import Optional

try:
    from playwright.async_api import async_playwright

    HAS_PLAYWRIGHT = True
except Exception:
    HAS_PLAYWRIGHT = False


RECAPTCHA_SITE_KEY = "6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV"


async def get_personal_recaptcha_token(
    project_id: str,
    action: str,
    st_token: Optional[str],
    headless: bool = False,
    timeout_seconds: int = 90,
    settle_seconds: float = 2.0,
) -> str:
    """Run reCAPTCHA in a local browser and return the token."""
    if not HAS_PLAYWRIGHT:
        raise Exception(
            "Playwright is not installed. Run: pip install playwright && python -m playwright install chromium"
        )

    url = f"https://labs.google/fx/tools/flow/project/{project_id}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-default-browser-check",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(viewport={"width": 1440, "height": 900})

        try:
            page = await context.new_page()

            if st_token:
                await context.add_cookies(
                    [
                        {
                            "name": "__Secure-next-auth.session-token",
                            "value": st_token,
                            "domain": "labs.google",
                            "path": "/",
                            "httpOnly": True,
                            "secure": True,
                            "sameSite": "Lax",
                        }
                    ]
                )

            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_seconds * 1000)
            await page.wait_for_timeout(int(max(0.0, settle_seconds) * 1000))

            await page.wait_for_function(
                "typeof grecaptcha !== 'undefined' && typeof grecaptcha.enterprise !== 'undefined' && typeof grecaptcha.enterprise.execute === 'function'",
                timeout=20000,
            )

            token = await page.evaluate(
                """
                async ({siteKey, actionName}) => {
                    return await new Promise((resolve, reject) => {
                        try {
                            grecaptcha.enterprise.ready(async () => {
                                try {
                                    const t = await grecaptcha.enterprise.execute(siteKey, {action: actionName});
                                    resolve(t || "");
                                } catch (err) {
                                    reject(err?.message || String(err));
                                }
                            });
                        } catch (err) {
                            reject(err?.message || String(err));
                        }
                    });
                }
                """,
                {"siteKey": RECAPTCHA_SITE_KEY, "actionName": action},
            )

            if not token:
                raise Exception("Browser execution succeeded but returned an empty token")
            return token
        finally:
            await context.close()
            await browser.close()
