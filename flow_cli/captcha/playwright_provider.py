"""
Playwright-based reCAPTCHA token provider.

Launches a headless (or headed) Chromium instance, navigates to the
Flow project page, waits for ``grecaptcha.enterprise`` to load, and
executes the reCAPTCHA challenge to obtain a token.
"""

from __future__ import annotations

from flow_cli.captcha.base import CaptchaProvider
from flow_cli.constants import RECAPTCHA_SITE_KEY
from flow_cli.exceptions import FlowCaptchaError
from flow_cli.logging import get_logger

logger = get_logger(__name__)

try:
    from playwright.async_api import async_playwright

    HAS_PLAYWRIGHT = True
except Exception:
    HAS_PLAYWRIGHT = False
    async_playwright = None  # type: ignore[assignment]


class PlaywrightCaptchaProvider(CaptchaProvider):
    """Acquire reCAPTCHA tokens via a local Playwright browser.

    Parameters
    ----------
    st_token:
        Session token to inject as a cookie.
    headless:
        Run the browser without a visible window.
    timeout_seconds:
        Page-load and script timeout.
    settle_seconds:
        Seconds to wait after page load before executing reCAPTCHA.
    """

    def __init__(
        self,
        st_token: str | None = None,
        *,
        headless: bool = False,
        timeout_seconds: int = 90,
        settle_seconds: float = 2.0,
    ) -> None:
        if not HAS_PLAYWRIGHT:
            raise FlowCaptchaError(
                "Playwright is not installed.  "
                "Run: pip install playwright && python -m playwright install chromium"
            )
        self.st_token = st_token
        self.headless = headless
        self.timeout_seconds = timeout_seconds
        self.settle_seconds = settle_seconds

    async def get_token(
        self,
        project_id: str,
        action: str = "IMAGE_GENERATION",
    ) -> str | None:
        """Launch Playwright, load the project page, and execute reCAPTCHA."""
        url = f"https://labs.google/fx/tools/flow/project/{project_id}"

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=self.headless,
                channel="chrome",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-default-browser-check",
                    "--disable-dev-shm-usage",
                ],
            )
            context = await browser.new_context(
                viewport={"width": 1440, "height": 900}
            )
            try:
                page = await context.new_page()

                if self.st_token:
                    await context.add_cookies([{
                        "name": "__Secure-next-auth.session-token",
                        "value": self.st_token,
                        "domain": "labs.google",
                        "path": "/",
                        "httpOnly": True,
                        "secure": True,
                        "sameSite": "Lax",
                    }])

                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.timeout_seconds * 1000,
                )
                await page.wait_for_timeout(
                    int(max(0.0, self.settle_seconds) * 1000)
                )

                # Wait for reCAPTCHA enterprise to be available
                await page.wait_for_function(
                    "typeof grecaptcha !== 'undefined' "
                    "&& typeof grecaptcha.enterprise !== 'undefined' "
                    "&& typeof grecaptcha.enterprise.execute === 'function'",
                    timeout=20000,
                )

                # Execute reCAPTCHA
                token = await page.evaluate(
                    """
                    async ({siteKey, actionName}) => {
                        return await new Promise((resolve, reject) => {
                            try {
                                grecaptcha.enterprise.ready(async () => {
                                    try {
                                        const t = await grecaptcha.enterprise.execute(
                                            siteKey, {action: actionName}
                                        );
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
                    raise FlowCaptchaError(
                        "reCAPTCHA executed but returned an empty token"
                    )

                logger.debug("reCAPTCHA token acquired (%d chars)", len(token))
                return token

            finally:
                await context.close()
                await browser.close()
