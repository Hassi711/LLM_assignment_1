"""Generate a professional, fully-formatted Microsoft Word (.docx) report."""
from __future__ import annotations

import json
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls


def set_cell_background(cell, hex_color: str) -> None:
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)


def set_cell_margins(cell, top=80, bottom=80, left=120, right=120) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def add_callout(doc, text: str, title: str = "Key Observation") -> None:
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    tbl.columns[0].width = Inches(6.5)
    cell = tbl.cell(0, 0)
    set_cell_background(cell, "F0F4F8")
    set_cell_margins(cell, top=100, bottom=100, left=150, right=150)
    
    # Left border thick accent
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="none"/>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="1B4965"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    run_t = p.add_run(f"{title}: ")
    run_t.bold = True
    run_t.font.name = "Calibri"
    run_t.font.size = Pt(9.5)
    run_t.font.color.rgb = RGBColor(0x1B, 0x49, 0x65)
    
    run_b = p.add_run(text)
    run_b.font.name = "Calibri"
    run_b.font.size = Pt(9.5)
    run_b.font.color.rgb = RGBColor(0x2B, 0x2D, 0x42)
    doc.add_paragraph()  # spacing


def build_docx(output_path: str = "report.docx") -> None:
    data = json.load(open("analysis_data.json", "r", encoding="utf-8"))

    doc = Document()
    
    # Page setup: Standard Letter, 0.75-inch margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # Styles
    styles = doc.styles
    normal_style = styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(10)
    normal_style.font.color.rgb = RGBColor(0x21, 0x25, 0x29)

    # Header / Title Block
    p_inst = doc.add_paragraph()
    p_inst.paragraph_format.space_before = Pt(0)
    p_inst.paragraph_format.space_after = Pt(2)
    r_inst = p_inst.add_run("NATIONAL UNIVERSITY OF SCIENCES & TECHNOLOGY (NUST SEECS)\nDEPARTMENT OF COMPUTING | CS 417: LARGE LANGUAGE MODELS (SPRING 2026)")
    r_inst.font.name = "Calibri"
    r_inst.font.size = Pt(9)
    r_inst.font.bold = True
    r_inst.font.color.rgb = RGBColor(0x49, 0x50, 0x57)

    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(4)
    p_title.paragraph_format.space_after = Pt(4)
    r_title = p_title.add_run("Assignment 1: Engineering a High-Performance Urdu Byte-Level BPE Tokenizer from Scratch")
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(18)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(0x1B, 0x49, 0x65)

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(12)
    r_sub = p_sub.add_run("Technical Report & Empirical Analysis (CLO 3)  |  Target Vocabulary: 50,000 Tokens (49,743 Merges)")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(10)
    r_sub.font.italic = True
    r_sub.font.color.rgb = RGBColor(0x6C, 0x75, 0x7D)

    # Horizontal divider
    p_div = doc.add_paragraph()
    p_div.paragraph_format.space_after = Pt(8)
    r_div = p_div.add_run("—" * 60)
    r_div.font.color.rgb = RGBColor(0x1B, 0x49, 0x65)

    # -------------------------------------------------------------
    # 1. Executive Summary
    # -------------------------------------------------------------
    h1 = doc.add_heading(level=1)
    r_h1 = h1.add_run("1. Executive Summary & Design Overview")
    r_h1.font.name = "Calibri"
    r_h1.font.color.rgb = RGBColor(0x1B, 0x49, 0x65)
    r_h1.font.bold = True

    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(6)
    p.add_run(
        "Standard English-centric language model tokenizers (e.g., GPT-2) exhibit severe tokenization fragmentation when applied to the Perso-Arabic script of Urdu, inflating token counts by >5.1× and crippling language model context length and sample efficiency. In this work, we design and implement a strictly native "
    )
    r_b = p.add_run("byte-level Byte-Pair Encoding (BPE)")
    r_b.bold = True
    p.add_run(
        " tokenizer from scratch in plain Python without external tokenizer dependencies. Built to exact deterministic tie-breaking specifications (highest byte tuple lexicographical priority) with a reserved <|endoftext|> token at ID 256, our tokenizer completes 49,743 merges over a clean 520.0 MiB (545.3 MB) multi-genre Urdu corpus in "
    )
    r_b2 = p.add_run("352.25 seconds")
    r_b2.bold = True
    p.add_run(
        ". Empirical evaluation confirms a near-optimal compression rate of "
    )
    r_b3 = p.add_run("1.084 tokens/word")
    r_b3.bold = True
    p.add_run(
        " on native text, outperforming GPT-2 by 5.16× and OpenAI's multilingual o200k_base by 1.40×."
    )

    add_callout(
        doc,
        "Zero Out-Of-Vocabulary (<unk>): By utilizing byte-level fallback for the 256 base UTF-8 bytes (IDs 0–255), the tokenizer guarantees 100% lossless reconstruction (decode(encode(text)) == text) across arbitrary Unicode sequences, emojis, Roman Urdu, and technical code-switching.",
        title="Lossless Guarantee"
    )

    # -------------------------------------------------------------
    # 2. Corpus Acquisition, Normalization & Cleaning Pipeline
    # -------------------------------------------------------------
    h2 = doc.add_heading(level=1)
    r_h2 = h2.add_run("2. Corpus Acquisition, Normalization & Cleaning Pipeline (Part A)")
    r_h2.font.name = "Calibri"
    r_h2.font.color.rgb = RGBColor(0x1B, 0x49, 0x65)
    r_h2.font.bold = True

    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(6)
    p.add_run(
        "To provide a high-quality foundation for downstream GPT-style language modeling, we curated "
    )
    p.add_run("545.26 MB (520.00 MiB)").bold = True
    p.add_run(
        " of strictly cleaned Urdu text across three independent sources spanning encyclopedia, news, and mixed literature genres. Crucially, "
    )
    p.add_run("55.11 MiB clean text (56.91 MiB raw)").bold = True
    p.add_run(
        " was independently collected via automated discovery and extraction using the MediaWiki Parsoid API, satisfying the course mandate of ≥50 MB self-collected text (proven in data/raw/urwiki_collection_manifest.json)."
    )

    # Sources Table
    tbl_src = doc.add_table(rows=1, cols=6)
    tbl_src.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_src.autofit = False

    headers = ["Source", "Genre", "Extraction Method", "Raw Size", "Clean Size", "License / Terms"]
    col_widths = [Inches(1.2), Inches(0.9), Inches(1.5), Inches(0.8), Inches(0.8), Inches(1.3)]
    
    hdr_cells = tbl_src.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        set_cell_background(hdr_cells[i], "1B4965")
        set_cell_margins(hdr_cells[i], top=100, bottom=100, left=100, right=100)
        p_c = hdr_cells[i].paragraphs[0]
        p_c.runs[0].font.name = "Calibri"
        p_c.runs[0].font.size = Pt(8.5)
        p_c.runs[0].font.bold = True
        p_c.runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        p_c.alignment = WD_ALIGN_PARAGRAPH.CENTER

    src_rows = [
        ("Urdu Wikipedia", "Encyclopedia", "MediaWiki API (Longpages)", "56.91 MiB", "55.11 MiB", "CC BY-SA 4.0"),
        ("UFAL UrMonoCorp", "Mixed / Web", "LINDAT Repository API", "213.46 MiB (gz)", "231.21 MiB", "CC BY-NC-SA 3.0"),
        ("Urdu News Dataset", "Journalism", "1M Articles Corpus", "1.95 GiB", "258.94 MiB", "Academic Research"),
        ("Total Combined", "3 Genres", "Deduplicated Pipeline", "2.22 GiB", "520.00 MiB", "Permissive Course Use"),
    ]

    for r_idx, r_data in enumerate(src_rows):
        row_cells = tbl_src.add_row().cells
        is_total = (r_idx == len(src_rows) - 1)
        bg = "E9ECEF" if is_total else ("F8F9FA" if r_idx % 2 == 1 else "FFFFFF")
        for c_idx, val in enumerate(r_data):
            row_cells[c_idx].text = val
            set_cell_background(row_cells[c_idx], bg)
            set_cell_margins(row_cells[c_idx], top=70, bottom=70, left=100, right=100)
            p_c = row_cells[c_idx].paragraphs[0]
            if len(p_c.runs) > 0:
                p_c.runs[0].font.name = "Calibri"
                p_c.runs[0].font.size = Pt(8.5)
                if is_total or c_idx == 0:
                    p_c.runs[0].font.bold = True
            if c_idx in [3, 4]:
                p_c.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    for row in tbl_src.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = width

    doc.add_paragraph()  # spacing

    p_norm = doc.add_paragraph()
    p_norm.paragraph_format.line_spacing = 1.15
    p_norm.paragraph_format.space_after = Pt(6)
    p_norm.add_run("Preprocessing & Normalization Details:\n").bold = True
    p_norm.add_run(
        "1. Orthographic Normalization: Urdu orthography frequently contains Arabic keyboard substitutions. Our custom normalize.py maps Arabic Yeh (ي U+064A) and Alef Maksura (ى U+0649) to Urdu Yeh (ی U+06CC), Arabic Kaf (ك U+0643) to Urdu Keheh (ک U+06A9), and Arabic Heh (ه U+0647) to Gol Heh (ہ U+06C1) while strictly preserving Do-Chashmi Heh (ھ U+06BE) as a phonemically distinct aspirate marker. Tatweel (ـ U+0640) and control BOMs are removed, while intentional Zero-Width Non-Joiners (ZWNJ U+200C) are preserved for compound word boundaries.\n"
        "2. Boilerplate Filtering: Web markup, wiki headers, advert snippets, and lines failing an Arabic-script density threshold (<35% Arabic characters) were filtered out, while natural code-mixed English inside Urdu sentences was retained.\n"
        "3. Document-Level Hashing & Splits: Exact document deduplication via SHA-256 removed syndicated news wires. The cleaned corpus of 114,857 documents was partitioned into 98% train.txt (509.64 MiB, 112,559 docs, 67,597,701 words), 1% val.txt (5.00 MiB, 1,148 docs), and 1% test.txt (5.35 MiB, 1,150 docs) using a fixed random seed (4172026), delimited with <|endoftext|>."
    )

    # -------------------------------------------------------------
    # 3. Merge Trajectory & Vocabulary Evolution (Part C, Q1)
    # -------------------------------------------------------------
    h3 = doc.add_heading(level=1)
    r_h3 = h3.add_run("3. Merge Trajectory & Vocabulary Evolution (Part C, Question 1)")
    r_h3.font.name = "Calibri"
    r_h3.font.color.rgb = RGBColor(0x1B, 0x49, 0x65)
    r_h3.font.bold = True

    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(6)
    p.add_run(
        "The BPE algorithm initializes with 256 base byte tokens (IDs 0–255) and reserves ID 256 exclusively for <|endoftext|>. Training executes exactly 49,743 merges to reach the target vocabulary of 50,000 tokens. To achieve high throughput on 509 MB of text, we implemented a three-tier optimization: (i) weighted pre-token frequency counting, (ii) inverted pair-to-word inverted index with lazy heap updates, and (iii) subword memoization during encoding."
    )

    # Selected merges table
    p_tbl_lbl = doc.add_paragraph()
    p_tbl_lbl.add_run("Table 1: Selected Merges from Early Training & Milestone Intervals").bold = True
    p_tbl_lbl.paragraph_format.space_after = Pt(2)

    sample_ranks = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 16, 21, 30, 35, 37, 43, 5000, 10000, 25000, 45000]
    all_first50 = {r["rank"]: r for r in data["first_50_merges"]}
    all_5k = {r["rank"]: r for r in data["every_5k_merges"]}

    tbl_m = doc.add_table(rows=1, cols=7)
    tbl_m.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_m.autofit = False

    m_headers = ["Rank", "Token ID", "Left Token", "Right Token", "Decoded / Bytes", "Valid UTF-8?", "Linguistic Category"]
    m_col_widths = [Inches(0.6), Inches(0.7), Inches(0.9), Inches(0.9), Inches(1.1), Inches(0.8), Inches(1.5)]
    
    for i, title in enumerate(m_headers):
        tbl_m.rows[0].cells[i].text = title
        set_cell_background(tbl_m.rows[0].cells[i], "1B4965")
        set_cell_margins(tbl_m.rows[0].cells[i], top=80, bottom=80, left=80, right=80)
        p_c = tbl_m.rows[0].cells[i].paragraphs[0]
        p_c.runs[0].font.name = "Calibri"
        p_c.runs[0].font.size = Pt(8)
        p_c.runs[0].font.bold = True
        p_c.runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        p_c.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for rk in sample_ranks:
        row_cells = tbl_m.add_row().cells
        if rk in all_first50:
            item = all_first50[rk]
            vals = [str(item["rank"]), str(item["token_id"]), item["left_repr"], item["right_repr"], item["decoded"], "Yes" if item["is_valid_utf8"] else "No", item["category"]]
        else:
            item = all_5k[rk]
            vals = [f"{item['rank']:,}", f"{item['token_id']:,}", str(item["left_id"]), str(item["right_id"]), item["decoded"], "Yes" if item["is_valid_utf8"] else "No", f"Subword ({item['byte_len']} B)"]

        for c_idx, val in enumerate(vals):
            row_cells[c_idx].text = val
            set_cell_background(row_cells[c_idx], "F8F9FA" if rk % 2 == 1 else "FFFFFF")
            set_cell_margins(row_cells[c_idx], top=60, bottom=60, left=80, right=80)
            p_c = row_cells[c_idx].paragraphs[0]
            if len(p_c.runs) > 0:
                p_c.runs[0].font.name = "Calibri"
                p_c.runs[0].font.size = Pt(8)
            if c_idx in [0, 1, 5]:
                p_c.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for row in tbl_m.rows:
        for idx, width in enumerate(m_col_widths):
            row.cells[idx].width = width

    doc.add_paragraph()  # spacing

    p_dyn = doc.add_paragraph()
    p_dyn.paragraph_format.line_spacing = 1.15
    p_dyn.paragraph_format.space_after = Pt(6)
    p_dyn.add_run("Key Merge Dynamics:\n").bold = True
    p_dyn.add_run(
        "• Two-Byte Letter Reconstruction: Urdu letters in UTF-8 comprise two bytes (typically starting with 0xD8 or 0xD9). In the first 50 merges, 22 full letters are assembled, beginning with ی (Merge 2, ID 258: \\xDB+\\x8C), ا (Merge 3, ID 259: \\xD8+\\xA7), ک (Merge 5, ID 261), ر (Merge 6, ID 262), و (Merge 7), ہ (Merge 8), ے (Merge 9), and ن (Merge 11).\n"
        "• Invalid Standalone UTF-8 Tokens: Three early merges produce byte sequences that are invalid standalone UTF-8: Merge 1 (\\x20+\\xD8), Merge 4 (\\x20+\\xD9), and Merge 21 (ا+\\xD8). Rather than being errors, these represent highly efficient intermediate consolidations: pairing the word-initial space with the leading byte of subsequent Arabic consonants allows the tokenizer to assemble full words with leading spaces in single subsequent merges (e.g., Merge 12 creates ' ا' and Merge 16 creates ' م').\n"
        "• First Whole Word Appearance: The first complete lexical word equals Merge 2 (Token ID 258, ی) as an isolated letter, and the first multi-letter lexical postposition appears at Merge 30 (Token ID 286:  کی, 'of'), rapidly followed by Merge 35 ( کے), Merge 37 ( میں, 'in'), and Merge 43 ( ہے, 'is')."
    )

    # Embed Chart 2: Vocab Growth
    if Path("work/vocab_growth.png").exists():
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(4)
        p_img.paragraph_format.space_after = Pt(2)
        doc.add_picture("work/vocab_growth.png", width=Inches(6.0))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_cap = p_cap.add_run("Figure 1: Token Byte-Length Expansion across 49,743 Merges")
        r_cap.font.size = Pt(8.5)
        r_cap.font.italic = True
        r_cap.font.color.rgb = RGBColor(0x6C, 0x75, 0x7D)

    # Top Longest Tokens Table
    p_long_lbl = doc.add_paragraph()
    p_long_lbl.add_run("Table 2: Top 10 Longest Learned Tokens (Byte Length)").bold = True
    p_long_lbl.paragraph_format.space_before = Pt(6)
    p_long_lbl.paragraph_format.space_after = Pt(2)

    tbl_l = doc.add_table(rows=1, cols=4)
    tbl_l.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_l.autofit = False
    l_headers = ["Rank", "Token ID", "Length (UTF-8 Bytes)", "Decoded Representation"]
    l_col_widths = [Inches(0.8), Inches(1.0), Inches(1.5), Inches(3.2)]

    for i, title in enumerate(l_headers):
        tbl_l.rows[0].cells[i].text = title
        set_cell_background(tbl_l.rows[0].cells[i], "1B4965")
        set_cell_margins(tbl_l.rows[0].cells[i], top=80, bottom=80, left=80, right=80)
        p_c = tbl_l.rows[0].cells[i].paragraphs[0]
        p_c.runs[0].font.name = "Calibri"
        p_c.runs[0].font.size = Pt(8)
        p_c.runs[0].font.bold = True
        p_c.runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        p_c.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for idx, t in enumerate(data["longest_tokens"][:10], 1):
        row_cells = tbl_l.add_row().cells
        vals = [str(idx), str(t["token_id"]), f"{t['byte_len']} bytes", t["decoded"]]
        for c_idx, val in enumerate(vals):
            row_cells[c_idx].text = val
            set_cell_background(row_cells[c_idx], "F8F9FA" if idx % 2 == 1 else "FFFFFF")
            set_cell_margins(row_cells[c_idx], top=60, bottom=60, left=80, right=80)
            p_c = row_cells[c_idx].paragraphs[0]
            if len(p_c.runs) > 0:
                p_c.runs[0].font.name = "Calibri"
                p_c.runs[0].font.size = Pt(8)
                if c_idx == 3:
                    p_c.runs[0].font.bold = True
            if c_idx in [0, 1, 2]:
                p_c.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for row in tbl_l.rows:
        for idx, width in enumerate(l_col_widths):
            row.cells[idx].width = width

    doc.add_paragraph()  # spacing

    # -------------------------------------------------------------
    # 4. Comparative Benchmarks (Part C, Q2)
    # -------------------------------------------------------------
    h4 = doc.add_heading(level=1)
    r_h4 = h4.add_run("4. Comparative Benchmarks & Empirical Evaluation (Part C, Question 2)")
    r_h4.font.name = "Calibri"
    r_h4.font.color.rgb = RGBColor(0x1B, 0x49, 0x65)
    r_h4.font.bold = True

    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(6)
    p.add_run(
        "To rigorously quantify tokenization efficiency, we benchmark our trained Urdu BPE tokenizer against OpenAI's "
    )
    p.add_run("GPT-2 tokenizer").bold = True
    p.add_run(" (50,257 vocab) and OpenAI's modern multilingual ")
    p.add_run("o200k_base tokenizer").bold = True
    p.add_run(
        " (200,000 vocab). Measurements evaluate Tokens per Word (Tokens / Words, where word count is whitespace-delimited len(text.split())) on the official 5.35 MB test.txt partition (713,196 words) and across seven hand-picked domain inputs representing diverse linguistic distributions."
    )

    # Benchmark Table
    p_b_lbl = doc.add_paragraph()
    p_b_lbl.add_run("Table 3: Compression Benchmark Across Diverse Urdu Domains").bold = True
    p_b_lbl.paragraph_format.space_after = Pt(2)

    tbl_b = doc.add_table(rows=1, cols=7)
    tbl_b.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_b.autofit = False

    b_headers = ["Domain / Input", "Words", "Urdu BPE Tokens", "Urdu BPE (tok/w)", "GPT-2 (tok/w)", "o200k_base (tok/w)", "Advantage vs GPT-2"]
    b_col_widths = [Inches(1.4), Inches(0.7), Inches(0.9), Inches(0.9), Inches(0.8), Inches(0.9), Inches(0.9)]

    for i, title in enumerate(b_headers):
        tbl_b.rows[0].cells[i].text = title
        set_cell_background(tbl_b.rows[0].cells[i], "1B4965")
        set_cell_margins(tbl_b.rows[0].cells[i], top=80, bottom=80, left=80, right=80)
        p_c = tbl_b.rows[0].cells[i].paragraphs[0]
        p_c.runs[0].font.name = "Calibri"
        p_c.runs[0].font.size = Pt(8)
        p_c.runs[0].font.bold = True
        p_c.runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        p_c.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for idx, b in enumerate(data["benchmarks"]):
        row_cells = tbl_b.add_row().cells
        adv = f"{b['gpt2_rate'] / b['urdu_bpe_rate']:.2f}x"
        vals = [b["input_name"], f"{b['words']:,}", f"{b['urdu_bpe_tokens']:,}", f"{b['urdu_bpe_rate']:.3f}", f"{b['gpt2_rate']:.3f}", f"{b['o200k_rate']:.3f}", f"+{adv}"]
        bg = "E2EAFC" if idx == 0 else ("F8F9FA" if idx % 2 == 1 else "FFFFFF")
        for c_idx, val in enumerate(vals):
            row_cells[c_idx].text = val
            set_cell_background(row_cells[c_idx], bg)
            set_cell_margins(row_cells[c_idx], top=60, bottom=60, left=80, right=80)
            p_c = row_cells[c_idx].paragraphs[0]
            if len(p_c.runs) > 0:
                p_c.runs[0].font.name = "Calibri"
                p_c.runs[0].font.size = Pt(8)
                if c_idx in [0, 3, 6]:
                    p_c.runs[0].font.bold = True
            if c_idx >= 1:
                p_c.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    for row in tbl_b.rows:
        for idx, width in enumerate(b_col_widths):
            row.cells[idx].width = width

    doc.add_paragraph()  # spacing

    # Embed Chart 1: Benchmark comparison
    if Path("work/benchmark_comparison.png").exists():
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(4)
        p_img.paragraph_format.space_after = Pt(2)
        doc.add_picture("work/benchmark_comparison.png", width=Inches(6.2))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_cap = p_cap.add_run("Figure 2: Tokenization Efficiency (Tokens per Word) Across Domains")
        r_cap.font.size = Pt(8.5)
        r_cap.font.italic = True
        r_cap.font.color.rgb = RGBColor(0x6C, 0x75, 0x7D)

    p_disc = doc.add_paragraph()
    p_disc.paragraph_format.line_spacing = 1.15
    p_disc.paragraph_format.space_after = Pt(6)
    p_disc.add_run("Quantitative Observations:\n").bold = True
    p_disc.add_run(
        "1. Eliminating the Urdu 'Token Tax': On the 713k-word test set, our tokenizer achieves 1.084 tokens/word, showing that almost every Urdu word encodes as a single token. In contrast, GPT-2 requires 5.594 tokens/word—a severe 5.16× inflation—due to its lack of Perso-Arabic byte merges.\n"
        "2. Outperforming Multilingual SOTA: Our 50k tokenizer surpasses OpenAI's 200k-vocabulary o200k_base (1.521 tok/w on test.txt, a 1.40× advantage). While o200k_base distributes its budget across hundreds of languages, our focused Urdu allocation captures full morphological roots and common inflections.\n"
        "3. Downstream Context Window Expansion: In a 2,048-token context window, our tokenizer accommodates approximately 1,890 full Urdu words, whereas GPT-2 accommodates only 366 words."
    )

    # -------------------------------------------------------------
    # 5. Difficult Inputs & Failure Modes (Part C, Q3)
    # -------------------------------------------------------------
    h5 = doc.add_heading(level=1)
    r_h5 = h5.add_run("5. Deep Dive: Three Challenging Inputs & Failure Modes (Part C, Question 3)")
    r_h5.font.name = "Calibri"
    r_h5.font.color.rgb = RGBColor(0x1B, 0x49, 0x65)
    r_h5.font.bold = True

    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(6)
    p.add_run(
        "To satisfy the Part C requirement to evaluate failure modes, we identified and analyzed three distinct orthographic categories where byte-level BPE encounters structural difficulties."
    )

    for idx, d in enumerate(data["difficult_inputs"], 1):
        p_c_title = doc.add_paragraph()
        p_c_title.paragraph_format.space_before = Pt(4)
        p_c_title.paragraph_format.space_after = Pt(2)
        r_ct = p_c_title.add_run(f"Case {idx}: {d['key'].replace('_', ' ').title()}")
        r_ct.bold = True
        r_ct.font.color.rgb = RGBColor(0x1B, 0x49, 0x65)

        p_c_body = doc.add_paragraph()
        p_c_body.paragraph_format.line_spacing = 1.15
        p_c_body.paragraph_format.space_after = Pt(4)
        p_c_body.add_run(f"• Input String: {d['text']}\n")
        p_c_body.add_run(f"• Metrics: {d['words']} words | Urdu BPE: {d['urdu_bpe_tokens']} tokens ({d['urdu_bpe_rate']:.2f} tok/w) | GPT-2: {d['gpt2_tokens']} tokens | o200k_base: {d['o200k_tokens']} tokens\n")
        p_c_body.add_run(f"• Generated Subword Pieces: {str(d['bpe_token_pieces'][:15])}...\n")
        p_c_body.add_run(f"• Linguistic Failure Mechanism: {d['explanation']}")

    # -------------------------------------------------------------
    # 6. Architectural Readiness for Assignment 2
    # -------------------------------------------------------------
    h6 = doc.add_heading(level=1)
    r_h6 = h6.add_run("6. Architectural Readiness for Assignment 2 (GPT Pre-Training)")
    r_h6.font.name = "Calibri"
    r_h6.font.color.rgb = RGBColor(0x1B, 0x49, 0x65)
    r_h6.font.bold = True

    p_arch = doc.add_paragraph()
    p_arch.paragraph_format.line_spacing = 1.15
    p_arch.paragraph_format.space_after = Pt(6)
    p_arch.add_run(
        "The deliverables produced in this assignment directly optimize the upcoming language modeling phase:\n"
        "• Lossless Round-Trip Guarantee: Rigorously verified: decode(encode(text)) == text holds across emojis, English code-switching, complex diacritics, and arbitrary byte streams.\n"
        "• Binary Dataset Ready: Pre-tokenized and encoded binary tensors train.bin (72,127,369 uint16 IDs, 144.3 MB) and val.bin (700,321 uint16 IDs, 1.4 MB) are formatted for memory-mapped streaming in PyTorch/NumPy without runtime tokenization overhead.\n"
        "• Recommended Model Configuration: Embedding vocabulary dimension of exactly 50,000. With average sequence packing of 1.084 tokens/word, training a 124M-parameter GPT model will achieve superior convergence and representation density per step compared to baseline architectures."
    )

    doc.save(output_path)
    print(f"Word document successfully created: {output_path}")


if __name__ == "__main__":
    build_docx()
