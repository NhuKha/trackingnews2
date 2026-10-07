from decimal import Decimal

from app.ingestion.sec import parse_form4_xml
from app.scoring.insider import score_insider_transaction
from app.scoring.signal import combine_signal_scores, signal_level


FORM4 = """<?xml version="1.0"?>
<ownershipDocument>
  <issuer>
    <issuerCik>0000123456</issuerCik>
    <issuerName>Example Corp</issuerName>
    <issuerTradingSymbol>EXM</issuerTradingSymbol>
  </issuer>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0000999999</rptOwnerCik>
      <rptOwnerName>Jane Doe</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isDirector>0</isDirector>
      <isOfficer>1</isOfficer>
      <isTenPercentOwner>0</isTenPercentOwner>
      <officerTitle>Chief Executive Officer</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <securityTitle><value>Common Stock</value></securityTitle>
      <transactionDate><value>2026-10-01</value></transactionDate>
      <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>10000</value></transactionShares>
        <transactionPricePerShare><value>125.50</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
      <postTransactionAmounts><sharesOwnedFollowingTransaction><value>50000</value></sharesOwnedFollowingTransaction></postTransactionAmounts>
      <ownershipNature><directOrIndirectOwnership><value>D</value></directOrIndirectOwnership></ownershipNature>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""


def test_parse_form4():
    parsed = parse_form4_xml(FORM4)
    assert parsed["ticker"] == "EXM"
    tx = parsed["transactions"][0]
    assert tx["transaction_code"] == "P"
    assert tx["transaction_value"] == Decimal("1255000.00")
    assert tx["officer_title"] == "Chief Executive Officer"


def test_insider_score_large_ceo_purchase():
    score = score_insider_transaction(
        code="P", value=Decimal("1255000"), is_director=False, is_officer=True,
        officer_title="Chief Executive Officer", is_10b5_1=False,
    )
    assert score >= 70


def test_signal_scoring():
    score = combine_signal_scores(x_score=90, market_score=80, insider_score=85, news_score=90,
                                  whale_score=40, sentiment_score=70, verification_score=95)
    assert 0 <= score <= 100
    assert signal_level(91) == "EXTREME"
