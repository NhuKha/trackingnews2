from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from xml.etree import ElementTree as ET

import httpx

from app.config import settings


SEC_DATA_BASE = "https://data.sec.gov"
SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"


def _text(node: ET.Element | None, path: str) -> str | None:
    if node is None:
        return None
    found = node.find(path)
    if found is None or found.text is None:
        return None
    value = found.text.strip()
    return value or None


def _decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None


def _bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y"}


def parse_form4_xml(xml_text: str) -> dict[str, Any]:
    root = ET.fromstring(xml_text)

    issuer = root.find("issuer")
    owner = root.find("reportingOwner")
    owner_id = owner.find("reportingOwnerId") if owner is not None else None
    relationship = owner.find("reportingOwnerRelationship") if owner is not None else None

    issuer_cik = _text(issuer, "issuerCik")
    ticker = _text(issuer, "issuerTradingSymbol")
    issuer_name = _text(issuer, "issuerName")
    insider_name = _text(owner_id, "rptOwnerName") or "Unknown"
    insider_cik = _text(owner_id, "rptOwnerCik")

    is_director = _bool(_text(relationship, "isDirector"))
    is_officer = _bool(_text(relationship, "isOfficer"))
    is_ten_percent_owner = _bool(_text(relationship, "isTenPercentOwner"))
    officer_title = _text(relationship, "officerTitle")

    footnotes = " ".join((n.text or "") for n in root.findall(".//footnote"))
    is_10b5_1 = "10b5-1" in footnotes.lower()

    transactions: list[dict[str, Any]] = []
    for tx in root.findall(".//nonDerivativeTransaction"):
        tx_date_raw = _text(tx, "transactionDate/value")
        shares = _decimal(_text(tx, "transactionAmounts/transactionShares/value"))
        price = _decimal(_text(tx, "transactionAmounts/transactionPricePerShare/value"))
        value = shares * price if shares is not None and price is not None else None

        transactions.append({
            "insider_name": insider_name,
            "insider_cik": insider_cik,
            "is_director": is_director,
            "is_officer": is_officer,
            "is_ten_percent_owner": is_ten_percent_owner,
            "officer_title": officer_title,
            "transaction_date": date.fromisoformat(tx_date_raw) if tx_date_raw else None,
            "security_title": _text(tx, "securityTitle/value"),
            "transaction_code": _text(tx, "transactionCoding/transactionCode"),
            "shares": shares,
            "price": price,
            "transaction_value": value,
            "acquired_or_disposed": _text(tx, "transactionAmounts/transactionAcquiredDisposedCode/value"),
            "ownership_type": _text(tx, "ownershipNature/directOrIndirectOwnership/value"),
            "shares_owned_after": _decimal(_text(tx, "postTransactionAmounts/sharesOwnedFollowingTransaction/value")),
            "is_10b5_1": is_10b5_1,
        })

    return {
        "issuer_cik": issuer_cik,
        "ticker": ticker,
        "issuer_name": issuer_name,
        "insider_name": insider_name,
        "transactions": transactions,
    }


class SecClient:
    def __init__(self) -> None:
        self.headers = {
            "User-Agent": settings.sec_user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov",
        }

    async def submissions(self, cik: str) -> dict[str, Any]:
        cik10 = str(cik).zfill(10)
        url = f"{SEC_DATA_BASE}/submissions/CIK{cik10}.json"
        async with httpx.AsyncClient(timeout=settings.sec_timeout_seconds) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def filing_xml(self, cik: str, accession_number: str, primary_document: str) -> str:
        cik_no_zeros = str(int(cik))
        accession_compact = accession_number.replace("-", "")
        url = f"{SEC_ARCHIVES_BASE}/{cik_no_zeros}/{accession_compact}/{primary_document}"
        headers = {"User-Agent": settings.sec_user_agent, "Accept-Encoding": "gzip, deflate"}
        async with httpx.AsyncClient(timeout=settings.sec_timeout_seconds, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.text
