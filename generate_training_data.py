"""
generate_training_data.py — Builds spaCy training data from silver annotations.

Reads the extraction jsonl, runs `extract_code_entities()` (regex + dictionary)
and `en_core_web_lg` NER on each block, merges the resulting spans, exports
DocBin files for spaCy v3 training.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

import spacy
from spacy.tokens import DocBin
from spacy.util import filter_spans

from ner_pipeline import (
    STOPWORDS,
    TECH_RECLASSIFY,
    TOOL_RECLASSIFY,
    _is_noise,
    extract_code_entities,
)

INPUT_JSONL = "data/graphs/restored-src-extracted.jsonl"
OUT_DIR = Path("data/training")
TRAIN_OUT = OUT_DIR / "train.spacy"
DEV_OUT = OUT_DIR / "dev.spacy"

MIN_CHARS = 50
SPLIT_RATIO = 0.8
SEED = 42
BATCH_SIZE = 64

LABELS = {"LIB", "CLASS", "FUNC", "TECH", "PER", "ORG", "LOC"}

SPACY_LABEL_MAP = {
    "PERSON": "PER",
    "PER": "PER",
    "ORG": "ORG",
    "ORGANIZATION": "ORG",
    "GPE": "LOC",
    "LOC": "LOC",
    "FAC": "LOC",
    "PRODUCT": "TECH",
    "LANGUAGE": "TECH",
}


def locate(text: str, needle: str) -> list[tuple[int, int]]:
    """Find all word-bounded, case-insensitive positions of `needle` in `text`."""
    if not needle or len(needle) < 2:
        return []
    pattern = r"\b" + re.escape(needle) + r"\b"
    return [(m.start(), m.end()) for m in re.finditer(pattern, text, re.IGNORECASE)]


def collect_code_spans(text: str, source_file: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for ent in extract_code_entities(text, source_file):
        for start, end in locate(text, ent.text):
            spans.append((start, end, ent.label))
    return spans


def collect_spacy_spans(doc) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for ent in doc.ents:
        clean = ent.text.strip()
        lower = clean.lower()
        if lower in STOPWORDS or _is_noise(clean):
            continue
        label = SPACY_LABEL_MAP.get(ent.label_)
        if label is None:
            continue
        if label == "ORG" and lower in TECH_RECLASSIFY:
            label = "TECH"
        if label == "PER" and lower in TOOL_RECLASSIFY:
            label = "TECH"
        spans.append((ent.start_char, ent.end_char, label))
    return spans


def build_doc(nlp, text: str, raw_spans: list[tuple[int, int, str]]):
    doc = nlp.make_doc(text)
    candidates = []
    for start, end, label in raw_spans:
        if label not in LABELS:
            continue
        span = doc.char_span(start, end, label=label, alignment_mode="contract")
        if span is None or len(span) == 0:
            continue
        candidates.append(span)
    candidates = filter_spans(candidates)
    try:
        doc.ents = candidates
    except ValueError:
        return None
    return doc


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading spaCy model en_core_web_lg ...")
    nlp = spacy.load("en_core_web_lg")
    nlp.max_length = 2_000_000

    print(f"Reading {INPUT_JSONL} ...")
    with open(INPUT_JSONL, "r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    print(f"  total blocks: {len(rows)}")

    rows = [r for r in rows if len(r.get("text", "")) >= MIN_CHARS]
    print(f"  after MIN_CHARS={MIN_CHARS}: {len(rows)}")

    rng = random.Random(SEED)
    rng.shuffle(rows)

    texts = [r["text"] for r in rows]
    docs = []
    empty = 0
    label_counts: dict[str, int] = {}

    disable = ["tagger", "parser", "attribute_ruler", "lemmatizer"]
    for idx, (row, spacy_doc) in enumerate(
        zip(rows, nlp.pipe(texts, batch_size=BATCH_SIZE, disable=disable))
    ):
        text = row["text"]
        source_file = row.get("source_file", "")

        spans = collect_code_spans(text, source_file) + collect_spacy_spans(spacy_doc)
        doc = build_doc(nlp, text, spans)
        if doc is None or len(doc.ents) == 0:
            empty += 1
            continue

        for ent in doc.ents:
            label_counts[ent.label_] = label_counts.get(ent.label_, 0) + 1
        docs.append(doc)

        if (idx + 1) % 5000 == 0:
            print(f"  processed {idx + 1}/{len(rows)} | kept {len(docs)} | empty {empty}")

    print(f"\nDocs with >=1 entity: {len(docs)} (skipped empty: {empty})")
    print(f"Label distribution: {dict(sorted(label_counts.items()))}")
    print(f"Total entities: {sum(label_counts.values())}")

    split = int(len(docs) * SPLIT_RATIO)
    train_docs = docs[:split]
    dev_docs = docs[split:]

    train_db = DocBin(store_user_data=False)
    dev_db = DocBin(store_user_data=False)
    for d in train_docs:
        train_db.add(d)
    for d in dev_docs:
        dev_db.add(d)

    train_db.to_disk(TRAIN_OUT)
    dev_db.to_disk(DEV_OUT)

    print(f"\nWrote {len(train_docs)} train docs -> {TRAIN_OUT}")
    print(f"Wrote {len(dev_docs)} dev docs   -> {DEV_OUT}")


if __name__ == "__main__":
    main()
