from __future__ import annotations

import json
import logging
import re

import httpx
from bs4 import BeautifulSoup
from openai import OpenAI

try:
    import dns.resolver

    _DNS_AVAILABLE = True
except ImportError:  # dnspython not installed -- degrade gracefully
    _DNS_AVAILABLE = False

from app.config import settings
from app.dedup.engine import combine_verification, normalize_phone
from app.db.models import Prospect

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
WHATSAPP_LINK_RE = re.compile(r"(?:wa\.me/|api\.whatsapp\.com/send\?phone=)(\d+)")

SOCIAL_DOMAINS = {
    "facebook.com": "facebook",
    "instagram.com": "instagram",
    "linkedin.com": "linkedin",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "youtube.com": "youtube",
}

GENERIC_EMAIL_PREFIXES = {"info", "contact", "sales", "support", "hello", "admin", "office"}
COMPANY_SIZE_BUCKETS = {"1-10", "11-50", "51-200", "201+"}

# Emails that technically match the regex but never belong to the business
# itself -- website-builder placeholders, template examples, and
# third-party widget/analytics addresses that show up in raw page markup.
JUNK_EMAIL_DOMAINS = {
    "example.com", "example.org", "test.com", "domain.com", "yourdomain.com",
    "email.com", "yoursite.com", "sentry.io", "sentry-next.io",
    "wixpress.com", "squarespace.com", "godaddy.com", "wordpress.com",
    "weebly.com", "shopify.com", "google-analytics.com", "googletagmanager.com",
    "hotjar.com", "intercom.io", "zendesk.com", "freshdesk.com", "schema.org",
    "w3.org", "sentry.wixpress.com",
}


def _is_junk_email(email: str) -> bool:
    domain = email.split("@")[-1].lower()
    return domain in JUNK_EMAIL_DOMAINS


def _has_mx_record(domain: str) -> bool:
    """Cheap sanity check that a domain can even receive mail -- no message
    is sent, just an MX DNS lookup. Doesn't confirm the specific mailbox
    exists, but catches typo'd/dead domains before we call an email
    "verified"."""
    if not _DNS_AVAILABLE:
        return False
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5)
        return len(answers) > 0
    except Exception:  # noqa: BLE001 -- NXDOMAIN, timeout, no MX, etc. all mean "can't confirm"
        return False


class EnrichmentService:
    """
    Visits a prospect's website (and common sub-pages) to fill in gaps the
    scraper couldn't get directly from Google Maps / directories: email,
    WhatsApp number, social profiles, a short description, and a rough
    company-size estimate.
    """

    SUBPAGES = ["", "/contact", "/contact-us", "/about", "/about-us"]

    def __init__(self, timeout: float = 15.0):
        self.client = httpx.Client(
            headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True
        )
        if settings.openrouter_api_key:
            self.llm = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.openrouter_api_key,
            )
        else:
            self.llm = None

    def close(self) -> None:
        self.client.close()

    def enrich(self, prospect: Prospect) -> Prospect:
        if not prospect.website:
            return prospect

        base_url = prospect.website
        if not base_url.startswith("http"):
            base_url = f"https://{base_url}"

        found_emails: set[str] = set()
        found_whatsapp: set[str] = set()
        found_social: dict[str, str] = {}
        description_candidate: str | None = None

        for path in self.SUBPAGES:
            html = self._fetch(f"{base_url.rstrip('/')}{path}")
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text(" ", strip=True)

            # Prefer explicit mailto: links (highest confidence -- the site
            # itself is telling us this is its contact address). Only fall
            # back to regex-scanning the *visible text* (never raw HTML) so
            # we don't pick up addresses buried in <script>/<style>/meta
            # tags from analytics or third-party widgets. Either way,
            # filter out website-builder/placeholder/tracking domains.
            mailto_emails = {
                a["href"].split("mailto:", 1)[-1].split("?")[0].strip()
                for a in soup.find_all("a", href=True)
                if a["href"].lower().startswith("mailto:")
            }
            mailto_emails = {e for e in mailto_emails if e and not _is_junk_email(e)}
            if mailto_emails:
                found_emails.update(mailto_emails)
            else:
                found_emails.update(e for e in EMAIL_RE.findall(text) if not _is_junk_email(e))

            for match in WHATSAPP_LINK_RE.finditer(html):
                normalized = normalize_phone(f"+{match.group(1)}")
                if normalized:
                    found_whatsapp.add(normalized)

            for a in soup.find_all("a", href=True):
                href = a["href"]
                for domain, label in SOCIAL_DOMAINS.items():
                    if domain in href and label not in found_social:
                        found_social[label] = href

            if not description_candidate:
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc and meta_desc.get("content"):
                    description_candidate = meta_desc["content"].strip()
                elif text:
                    description_candidate = text[:400]

        if found_emails and not prospect.email:
            prospect.email = self._best_email(found_emails)
            domain = prospect.email.split("@")[-1]
            if _has_mx_record(domain):
                prospect.verification_status = combine_verification(
                    prospect.verification_status, email_ok=True
                )
        if found_whatsapp and not prospect.whatsapp:
            prospect.whatsapp = next(iter(found_whatsapp))
            prospect.whatsapp_source = "confirmed"
        if found_social:
            prospect.social_profiles = json.dumps(found_social)
        # Use OpenRouter for better enrichment if configured
        if getattr(self, "llm", None) and description_candidate:
            prompt = (
                "Analyze this text from a company website and provide ONLY a JSON response "
                "(no markdown blocks, no intro, no outro) with exactly three keys: "
                "'description' (a concise 1-2 sentence business description), "
                "'company_size' (one of: '1-10', '11-50', '51-200', '201+'), and "
                "'contact_name' (the owner, founder, director, or main broker's full name if mentioned, otherwise null).\n"
                f"Website text: {description_candidate}"
            )
            try:
                response = self.llm.chat.completions.create(
                    model="nvidia/nemotron-3-ultra-550b-a55b:free",
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.choices[0].message.content.strip()
                if content.startswith("```json"):
                    content = content[7:-3]
                elif content.startswith("```"):
                    content = content[3:-3]
                res_data = json.loads(content)
                if res_data.get("description"):
                    prospect.business_description = res_data["description"]
                # Guard against the model returning something outside the
                # fixed bucket set (freeform text would silently break
                # score/filtering downstream, which expects one of these).
                if res_data.get("company_size") in COMPANY_SIZE_BUCKETS:
                    prospect.company_size_estimate = res_data["company_size"]
                if res_data.get("contact_name") and not prospect.contact_name:
                    prospect.contact_name = res_data["contact_name"]
            except Exception as e:
                logger.error(f"LLM enrichment failed: {e}")

        if description_candidate and not prospect.business_description:
            prospect.business_description = description_candidate

        prospect.company_size_estimate = prospect.company_size_estimate or self._estimate_size(
            found_social
        )

        return prospect

    def _fetch(self, url: str) -> str | None:
        try:
            resp = self.client.get(url)
            if resp.status_code >= 400:
                return None
            return resp.text
        except httpx.HTTPError as exc:
            logger.debug("Enrichment fetch failed for %s: %s", url, exc)
            return None

    @staticmethod
    def _best_email(emails: set[str]) -> str:
        # Prefer a role-based address (info@, contact@) over a personal one,
        # since it's more likely to be actively monitored.
        for email in emails:
            prefix = email.split("@")[0].lower()
            if prefix in GENERIC_EMAIL_PREFIXES:
                return email
        return next(iter(emails))

    @staticmethod
    def _estimate_size(social: dict[str, str]) -> str:
        # Very rough heuristic placeholder; swap in a real firmographic
        # data source (e.g. LinkedIn company size, Clearbit) later.
        return "1-10" if len(social) <= 1 else "11-50"
