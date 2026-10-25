import pytest
from damga.quote_check import quote_contains_value, verify_quote


def test_quote_verbatim_exact():
    doc_text = "INVOICE #1024\nPig iron (basic grade) .......... 800.000 t\nTotal amount: $240,000"
    quote = "Pig iron (basic grade) .......... 800.000 t"
    ok, status = verify_quote(quote, 800.0, doc_text)
    assert ok is True
    assert status == "pass"


def test_quote_normalized_whitespace():
    # Multiple spaces and newline variations
    doc_text = "Delivery   receipt:\nScrap    shredded   grade:   1,234.5  t"
    quote = "Scrap shredded grade: 1,234.5 t"
    ok, status = verify_quote(quote, 1234.5, doc_text)
    assert ok is True
    assert status == "pass"


def test_quote_eu_thousands_separator():
    doc_text = "Doğalgaz tüketim: 11.002.300,50 m3 ölçülmüştür."
    quote = "Doğalgaz tüketim: 11.002.300,50 m3"
    ok, status = verify_quote(quote, 11002300.5, doc_text)
    assert ok is True
    assert status == "pass"


def test_quote_us_thousands_separator():
    doc_text = "Natural gas consumption: 11,002,300 m3 recorded."
    quote = "Natural gas consumption: 11,002,300 m3"
    ok, status = verify_quote(quote, 11002300.0, doc_text)
    assert ok is True
    assert status == "pass"


def test_quote_not_in_doc_text():
    doc_text = "Invoice for 500 tonnes of lime"
    quote = "Invoice for 800 tonnes of scrap"
    ok, status = verify_quote(quote, 800.0, doc_text)
    assert ok is False
    assert status == "fail"


def test_quote_number_mismatch():
    doc_text = "Scrap delivery: 500 tonnes received"
    quote = "Scrap delivery: 500 tonnes"
    # Extracted value says 800.0 but quote text has 500
    ok, status = verify_quote(quote, 800.0, doc_text)
    assert ok is False
    assert status == "fail"
