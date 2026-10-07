from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.sec import SEC_ARCHIVES_BASE, SecClient, parse_form4_xml
from app.models import Company, InsiderTransaction, SecFiling
from app.scoring.insider import score_insider_transaction


async def ingest_recent_form4(db: Session, company: Company, limit: int = 20) -> dict:
    client = SecClient()
    payload = await client.submissions(company.cik)
    recent = payload.get("filings", {}).get("recent", {})

    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    primary_docs = recent.get("primaryDocument", [])

    processed = 0
    inserted_transactions = 0
    errors: list[str] = []

    for form, accession, filing_date, primary_doc in zip(forms, accessions, filing_dates, primary_docs):
        if form not in {"4", "4/A"}:
            continue
        if processed >= limit:
            break
        processed += 1

        exists = db.scalar(select(SecFiling).where(SecFiling.accession_number == accession))
        if exists:
            continue

        accession_compact = accession.replace("-", "")
        source_url = f"{SEC_ARCHIVES_BASE}/{int(company.cik)}/{accession_compact}/{primary_doc}"

        try:
            xml_text = await client.filing_xml(company.cik, accession, primary_doc)
            parsed = parse_form4_xml(xml_text)

            filing = SecFiling(
                company_id=company.id,
                accession_number=accession,
                form_type=form,
                filing_date=date.fromisoformat(filing_date),
                primary_document=primary_doc,
                source_url=source_url,
            )
            db.add(filing)
            db.flush()

            for tx in parsed["transactions"]:
                tx["score"] = score_insider_transaction(
                    code=tx.get("transaction_code"),
                    value=tx.get("transaction_value"),
                    is_director=tx.get("is_director", False),
                    is_officer=tx.get("is_officer", False),
                    officer_title=tx.get("officer_title"),
                    is_10b5_1=tx.get("is_10b5_1", False),
                )
                db.add(InsiderTransaction(filing_id=filing.id, company_id=company.id, **tx))
                inserted_transactions += 1

            db.commit()
        except Exception as exc:
            db.rollback()
            errors.append(f"{accession}: {exc}")

    return {
        "ticker": company.ticker,
        "filings_checked": processed,
        "transactions_inserted": inserted_transactions,
        "errors": errors,
    }

from app.models import WhaleFiling
from app.scoring.whale import score_whale_filing


async def ingest_recent_whales(db: Session, company: Company, limit: int = 20) -> dict:
    client = SecClient()
    payload = await client.submissions(company.cik)
    recent = payload.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    primary_docs = recent.get("primaryDocument", [])
    inserted = 0
    for form, accession, filing_date, primary_doc in zip(forms, accessions, filing_dates, primary_docs):
        if form not in {"SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A"}:
            continue
        if inserted >= limit:
            break
        if db.scalar(select(WhaleFiling).where(WhaleFiling.accession_number == accession)):
            continue
        compact = accession.replace("-", "")
        source_url = f"{SEC_ARCHIVES_BASE}/{int(company.cik)}/{compact}/{primary_doc}"
        db.add(WhaleFiling(company_id=company.id, accession_number=accession, form_type=form,
                           filing_date=date.fromisoformat(filing_date), source_url=source_url,
                           score=score_whale_filing(form)))
        inserted += 1
    db.commit()
    return {"ticker": company.ticker, "whale_filings_inserted": inserted}
