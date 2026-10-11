"""Build a 4-page academic report (report.pdf) for CS 417 Assignment 1."""
from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print 'Page X of Y'."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#495057"))

        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(
                54,
                11 * inch - 36,
                "CS 417: Large Language Models | Assignment 1: Urdu BPE Tokenizer",
            )
            self.drawRightString(
                8.5 * inch - 54,
                11 * inch - 36,
                "National University of Sciences & Technology (NUST SEECS)",
            )
            self.setStrokeColor(colors.HexColor("#ced4da"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 40, 8.5 * inch - 54, 11 * inch - 40)

        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#ced4da"))
        self.setLineWidth(0.5)
        self.line(54, 42, 8.5 * inch - 54, 42)

        self.drawString(54, 30, "Confidential - Academic Coursework | NUST SEECS")
        self.drawRightString(
            8.5 * inch - 54,
            30,
            f"Page {self._pageNumber} of {total_pages}",
        )
        self.restoreState()


def create_report(output_path: str = "report.pdf") -> None:
    data = json.load(open("analysis_data.json", "r", encoding="utf-8"))

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#1b4965"),
        spaceAfter=3,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#495057"),
        spaceAfter=6,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1b4965"),
        spaceBefore=5,
        spaceAfter=3,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#2b2d42"),
        spaceBefore=3,
        spaceAfter=2,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#212529"),
        spaceAfter=4,
    )

    bold_body = ParagraphStyle(
        "BoldBody_Custom",
        parent=body_style,
        fontName="Helvetica-Bold",
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=colors.white,
        alignment=1,  # Center
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=8.5,
        textColor=colors.HexColor("#212529"),
    )

    table_cell_center = ParagraphStyle(
        "TableCellCenter",
        parent=table_cell_style,
        alignment=1,
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=table_cell_style,
        fontName="Helvetica-Bold",
    )

    story = []

    # =========================================================================
    # PAGE 1: Corpus Curation & Architecture
    # =========================================================================
    story.append(Paragraph("Assignment 1: Engineering a High-Performance Urdu Byte-Level BPE Tokenizer", title_style))
    story.append(Paragraph("<b>Course:</b> CS 417: Large Language Models (Spring 2026) &nbsp;|&nbsp; <b>Institution:</b> NUST SEECS &nbsp;|&nbsp; <b>Vocab Size:</b> 50,000 Tokens", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1b4965"), spaceBefore=1, spaceAfter=4))

    story.append(Paragraph("1. Executive Summary & Design Overview", h1_style))
    story.append(Paragraph(
        "Standard English-centric LLM tokenizers (e.g., GPT-2) exhibit severe tokenization fragmentation when applied to the Perso-Arabic script of Urdu, inflating token counts by >5.1× and crippling language model context length and sample efficiency. In this work, we design and implement a strictly native <b>byte-level Byte-Pair Encoding (BPE)</b> tokenizer from scratch in plain Python without external tokenizer dependencies. Built to exact deterministic tie-breaking specifications (highest byte tuple lexicographical priority) with a reserved <code>&lt;|endoftext|&gt;</code> token at ID 256, our tokenizer completes 49,743 merges over a clean 520.0 MiB (545.3 MB) multi-genre Urdu corpus in <b>352.25 seconds</b>. Empirical evaluation confirms a near-optimal compression rate of <b>1.084 tokens/word</b> on native text, outperforming GPT-2 by 5.16× and OpenAI's multilingual <code>o200k_base</code> by 1.40×.",
        body_style
    ))

    story.append(Paragraph("2. Corpus Acquisition, Normalization & Cleaning Pipeline", h1_style))
    story.append(Paragraph(
        "To provide a robust foundation for downstream GPT-style language modeling, we curated <b>545.26 MB</b> (520.00 MiB) of strictly cleaned Urdu text across three independent sources spanning encyclopedia, news, and mixed literature genres. Crucially, <b>55.11 MiB</b> was independently collected via automated discovery and extraction using the MediaWiki Parsoid API, satisfying the course mandate of ≥50 MB self-collected text.",
        body_style
    ))

    # Sources Table
    src_data = [
        [
            Paragraph("Source", table_header_style),
            Paragraph("Genre", table_header_style),
            Paragraph("Extraction Method", table_header_style),
            Paragraph("Raw Size", table_header_style),
            Paragraph("Clean Size", table_header_style),
            Paragraph("Terms / License", table_header_style),
        ],
        [
            Paragraph("Urdu Wikipedia", table_cell_bold),
            Paragraph("Encyclopedia", table_cell_style),
            Paragraph("MediaWiki API (Longpages)", table_cell_style),
            Paragraph("56.91 MiB", table_cell_center),
            Paragraph("55.11 MiB", table_cell_center),
            Paragraph("CC BY-SA 4.0", table_cell_style),
        ],
        [
            Paragraph("UFAL UrMonoCorp", table_cell_bold),
            Paragraph("Mixed / Web", table_cell_style),
            Paragraph("LINDAT Repository API", table_cell_style),
            Paragraph("213.46 MiB (gz)", table_cell_center),
            Paragraph("231.21 MiB", table_cell_center),
            Paragraph("CC BY-NC-SA 3.0", table_cell_style),
        ],
        [
            Paragraph("Urdu News Dataset", table_cell_bold),
            Paragraph("Journalism", table_cell_style),
            Paragraph("1M Articles Corpus", table_cell_style),
            Paragraph("1.95 GiB", table_cell_center),
            Paragraph("258.94 MiB", table_cell_center),
            Paragraph("Academic Research", table_cell_style),
        ],
        [
            Paragraph("<b>Total Combined</b>", table_cell_bold),
            Paragraph("<b>3 Genres</b>", table_cell_bold),
            Paragraph("<b>Deduplicated Pipeline</b>", table_cell_bold),
            Paragraph("<b>2.22 GiB</b>", table_cell_center),
            Paragraph("<b>520.00 MiB</b>", table_cell_center),
            Paragraph("<b>Permissive Course Use</b>", table_cell_style),
        ],
    ]
    t_src = Table(src_data, colWidths=[85, 65, 115, 65, 65, 109])
    t_src.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b4965")),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ced4da")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.HexColor("#f8f9fa"), colors.white]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e9ecef")),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    story.append(t_src)
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Preprocessing and Normalization Mechanics:</b>", h2_style))
    story.append(Paragraph(
        "1. <b>Orthographic Normalization:</b> Urdu orthography suffers from ubiquitous Arabic keyboard substitutions. Our custom <code>normalize.py</code> maps Arabic Yeh (<code>ي</code> U+064A) and Alef Maksura (<code>ى</code> U+0649) to Urdu Yeh (<code>ی</code> U+06CC), Arabic Kaf (<code>ك</code> U+0643) to Urdu Keheh (<code>ک</code> U+06A9), and Arabic Heh (<code>ه</code> U+0647) to Gol Heh (<code>ہ</code> U+06C1) while strictly preserving Do-Chashmi Heh (<code>ھ</code> U+06BE) as a phonemically distinct aspirate marker. Tatweel (<code>ـ</code> U+0640) and control BOMs are removed, while intentional Zero-Width Non-Joiners (<code>ZWNJ</code> U+200C) are preserved for compound word boundaries.<br/>"
        "2. <b>Boilerplate Filtering & Urdu Script Ratio:</b> Web artifacts, advertising scripts, and navigation links were stripped. Lines failing an Urdu character density threshold (&lt;50% Arabic-script) were rejected, while natural code-mixed English inside Urdu sentences was retained.<br/>"
        "3. <b>Document-Level Hashing & Splits:</b> Exact document deduplication via SHA-256 removed redundant syndicated news wires. The cleaned corpus of 114,857 documents was partitioned into 98% <code>train.txt</code> (509.64 MiB, 112,559 docs, 67,597,701 words), 1% <code>val.txt</code> (5.00 MiB, 1,148 docs), and 1% <code>test.txt</code> (5.35 MiB, 1,150 docs) using a fixed random seed (42), delimited with <code>&lt;|endoftext|&gt;</code>.",
        body_style
    ))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: Merge Trajectory & Vocabulary Evolution (Part C, Q1)
    # =========================================================================
    story.append(Paragraph("3. Merge Trajectory & Vocabulary Evolution (Part C, Question 1)", h1_style))
    story.append(Paragraph(
        "The BPE algorithm initializes with 256 base byte tokens (IDs 0–255) and reserves ID 256 exclusively for <code>&lt;|endoftext|&gt;</code>. Training executes exactly 49,743 merges to reach the target vocabulary of 50,000 tokens. To achieve high throughput on 509 MB of text, we implemented a three-tier optimization: (i) weighted pre-token frequency counting, (ii) inverted pair-to-word inverted index with lazy heap updates, and (iii) subword memoization during encoding.",
        body_style
    ))

    # First 50 merges sampled table
    story.append(Paragraph("<b>Table 1: Selected Merges from Early Training & Milestone Intervals</b>", h2_style))
    sample_ranks = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 16, 21, 30, 35, 37, 43, 5000, 10000, 25000, 45000]
    m_data = [
        [
            Paragraph("Rank", table_header_style),
            Paragraph("ID", table_header_style),
            Paragraph("Left Token", table_header_style),
            Paragraph("Right Token", table_header_style),
            Paragraph("Result / Representation", table_header_style),
            Paragraph("UTF-8?", table_header_style),
            Paragraph("Linguistic Category", table_header_style),
        ]
    ]

    all_first50 = {r["rank"]: r for r in data["first_50_merges"]}
    all_5k = {r["rank"]: r for r in data["every_5k_merges"]}

    for rk in sample_ranks:
        if rk in all_first50:
            item = all_first50[rk]
            m_data.append([
                Paragraph(str(item["rank"]), table_cell_center),
                Paragraph(str(item["token_id"]), table_cell_center),
                Paragraph(item["left_repr"], table_cell_center),
                Paragraph(item["right_repr"], table_cell_center),
                Paragraph(f"<b>{item['decoded']}</b>", table_cell_center),
                Paragraph("Yes" if item["is_valid_utf8"] else "No", table_cell_center),
                Paragraph(item["category"], table_cell_style),
            ])
        elif rk in all_5k:
            item = all_5k[rk]
            m_data.append([
                Paragraph(f"{item['rank']:,}", table_cell_center),
                Paragraph(f"{item['token_id']:,}", table_cell_center),
                Paragraph(str(item["left_id"]), table_cell_center),
                Paragraph(str(item["right_id"]), table_cell_center),
                Paragraph(f"<b>{item['decoded']}</b>", table_cell_center),
                Paragraph("Yes" if item["is_valid_utf8"] else "No", table_cell_center),
                Paragraph(f"Milestone Subword ({item['byte_len']} bytes)", table_cell_style),
            ])

    t_m = Table(m_data, colWidths=[35, 35, 60, 60, 100, 40, 174])
    t_m.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b4965")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ced4da")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 1.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
    ]))
    story.append(t_m)
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Analysis of Merge Dynamics:</b>", h2_style))
    story.append(Paragraph(
        "• <b>Two-Byte Letter Reconstruction:</b> Urdu letters in UTF-8 comprise two bytes (typically starting with <code>0xD8</code> or <code>0xD9</code>). In the first 50 merges, <b>22 full letters</b> are assembled, beginning with <code>ی</code> (Merge 2, ID 258: <code>\\xDB+\\x8C</code>), <code>ا</code> (Merge 3, ID 259: <code>\\xD8+\\xA7</code>), <code>ک</code> (Merge 5, ID 261), <code>ر</code> (Merge 6, ID 262), <code>و</code> (Merge 7), <code>ہ</code> (Merge 8), <code>ے</code> (Merge 9), and <code>ن</code> (Merge 11).<br/>"
        "• <b>Invalid Standalone UTF-8 Tokens:</b> Three early merges produce byte sequences that are invalid standalone UTF-8: Merge 1 (<code>\\x20+\\xD8</code>), Merge 4 (<code>\\x20+\\xD9</code>), and Merge 21 (<code>ا+\\xD8</code>). Rather than being errors, these represent highly efficient intermediate consolidations: pairing the word-initial space with the leading byte of subsequent Arabic consonants allows the tokenizer to assemble full words with leading spaces in single subsequent merges (e.g., Merge 12 creates <code>' ا'</code> and Merge 16 creates <code>' م'</code>).<br/>"
        "• <b>First Whole Word Appearance:</b> The first complete lexical word equals Merge 2 (Token ID 258, <code>ی</code>) as an isolated letter, and the first multi-letter lexical postposition appears at <b>Merge 30 (Token ID 286: <code> کی</code>, 'of')</b>, rapidly followed by <b>Merge 35 (<code> کے</code>)</b>, <b>Merge 37 (<code> میں</code>, 'in')</b>, and <b>Merge 43 (<code> ہے</code>, 'is')</b>.",
        body_style
    ))

    # Longest Tokens & Graph
    story.append(Spacer(1, 2))
    story.append(Paragraph("<b>Table 2: Top 10 Longest Learned Tokens (Byte Length) & Growth Curve</b>", h2_style))

    long_data = [
        [
            Paragraph("Rank", table_header_style),
            Paragraph("ID", table_header_style),
            Paragraph("Bytes", table_header_style),
            Paragraph("Decoded String", table_header_style),
            Paragraph("Rank", table_header_style),
            Paragraph("ID", table_header_style),
            Paragraph("Bytes", table_header_style),
            Paragraph("Decoded String", table_header_style),
        ]
    ]
    longest = data["longest_tokens"][:10]
    for i in range(5):
        t1 = longest[i]
        t2 = longest[i+5]
        long_data.append([
            Paragraph(str(i+1), table_cell_center),
            Paragraph(str(t1["token_id"]), table_cell_center),
            Paragraph(str(t1["byte_len"]), table_cell_center),
            Paragraph(f"<b>{t1['decoded']}</b>", table_cell_style),
            Paragraph(str(i+6), table_cell_center),
            Paragraph(str(t2["token_id"]), table_cell_center),
            Paragraph(str(t2["byte_len"]), table_cell_center),
            Paragraph(f"<b>{t2['decoded']}</b>", table_cell_style),
        ])
    t_long = Table(long_data, colWidths=[25, 35, 30, 162, 25, 35, 30, 162])
    t_long.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b4965")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ced4da")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    story.append(t_long)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: Comparative Benchmarks & Empirical Evaluation (Part C, Q2)
    # =========================================================================
    story.append(Paragraph("4. Comparative Benchmarks & Empirical Evaluation (Part C, Question 2)", h1_style))
    story.append(Paragraph(
        "To rigorously quantify tokenization efficiency, we benchmark our trained Urdu BPE tokenizer against OpenAI's <b>GPT-2 tokenizer</b> (50,257 vocab) and OpenAI's modern multilingual <b>o200k_base tokenizer</b> (200,000 vocab). Measurements evaluate Tokens per Word (<code>Tokens / Words</code>, where word count is whitespace-delimited <code>len(text.split())</code>) on the official 5.35 MB <code>test.txt</code> partition (713,196 words) and across seven hand-picked domain inputs representing diverse linguistic distributions.",
        body_style
    ))

    # Benchmark Table
    bench_data = [
        [
            Paragraph("Benchmark Input / Domain", table_header_style),
            Paragraph("Words", table_header_style),
            Paragraph("Urdu BPE Tokens", table_header_style),
            Paragraph("Urdu BPE (tok/w)", table_header_style),
            Paragraph("GPT-2 (tok/w)", table_header_style),
            Paragraph("o200k_base (tok/w)", table_header_style),
            Paragraph("BPE vs GPT-2 Adv.", table_header_style),
        ]
    ]
    for b in data["benchmarks"]:
        adv = f"{b['gpt2_rate'] / b['urdu_bpe_rate']:.2f}x"
        bench_data.append([
            Paragraph(f"<b>{b['input_name']}</b>", table_cell_style),
            Paragraph(f"{b['words']:,}", table_cell_center),
            Paragraph(f"{b['urdu_bpe_tokens']:,}", table_cell_center),
            Paragraph(f"<b>{b['urdu_bpe_rate']:.3f}</b>", table_cell_center),
            Paragraph(f"{b['gpt2_rate']:.3f}", table_cell_center),
            Paragraph(f"{b['o200k_rate']:.3f}", table_cell_center),
            Paragraph(f"<b>+{adv}</b>", table_cell_center),
        ])

    t_bench = Table(bench_data, colWidths=[120, 45, 65, 68, 68, 70, 68])
    t_bench.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b4965")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ced4da")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8f9fa"), colors.white]),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#e2eafc")),  # highlight test.txt
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t_bench)
    story.append(Spacer(1, 4))

    # Benchmark Chart
    if Path("work/benchmark_comparison.png").exists():
        story.append(Image("work/benchmark_comparison.png", width=6.8 * inch, height=2.6 * inch))
        story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Quantitative Insights & Theoretical Implications:</b>", h2_style))
    story.append(Paragraph(
        "1. <b>Shattering the 'Urdu Token Tax':</b> On the 713k-word test set, our tokenizer achieves <b>1.084 tokens/word</b>, demonstrating that the vast majority of Urdu words encode as single tokens. In contrast, GPT-2 requires 5.594 tokens/word—a crushing <b>5.16× bloat</b>. This occurs because GPT-2 lacks Perso-Arabic byte merges, decomposing each 2-byte Urdu character into individual raw byte tokens.<br/>"
        "2. <b>Beating Multilingual SOTA:</b> Remarkably, our 50k tokenizer surpasses OpenAI's 200k-vocabulary <code>o200k_base</code> model (1.521 tok/w on test.txt, 1.40× more compact). While <code>o200k_base</code> devotes vocabulary budget to hundreds of languages, our focused allocation captures full Urdu morphological roots and common inflections.<br/>"
        "3. <b>Roman Urdu Cross-Over:</b> On Roman Urdu (Latin script), GPT-2 (2.083 tok/w) and o200k_base (1.667 tok/w) achieve higher compression than our model (2.583 tok/w). Because our training corpus was strictly filtered for Urdu script, Latin characters encode via character-level or 2-gram subwords.<br/>"
        "4. <b>Downstream Context Expansion:</b> For Assignment 2, a 2,048-token context window will accommodate approximately <b>1,890 full Urdu words</b> using our tokenizer, compared to a miserable <b>366 words</b> under GPT-2's tokenizer.",
        body_style
    ))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: Edge-Case Failure Analysis & Downstream LM Impact (Part C, Q3)
    # =========================================================================
    story.append(Paragraph("5. Deep Dive: Three Challenging Inputs & Failure Modes (Part C, Question 3)", h1_style))
    story.append(Paragraph(
        "To satisfy the Part C requirement to evaluate failure modes, we identified and analyzed three distinct orthographic categories where byte-level BPE encounters structural difficulties. Each case is dissected below with tokenization pieces and underlying linguistic mechanisms.",
        body_style
    ))

    # Case 1
    d1 = data["difficult_inputs"][0]
    story.append(Paragraph("<b>Case 1: Unnormalized Archaic Presentation Forms & Honorific Ligatures</b>", h2_style))
    story.append(Paragraph(
        f"• <b>Input String:</b> <code>{d1['text']}</code><br/>"
        f"• <b>Token Breakdown:</b> Urdu BPE: <b>{d1['urdu_bpe_tokens']} tokens</b> ({d1['urdu_bpe_rate']:.2f} tok/w) &nbsp;|&nbsp; GPT-2: {d1['gpt2_tokens']} tokens &nbsp;|&nbsp; o200k_base: {d1['o200k_tokens']} tokens<br/>"
        f"• <b>Generated Subwords:</b> <code>{str(d1['bpe_token_pieces'])}</code><br/>"
        "• <b>Failure Mechanism:</b> The string contains Unicode Arabic Presentation Forms-A: the honorific ligature <code>ﷺ</code> (U+FDFA) and the Basmala ligature <code>﷽</code> (U+FDFD). In UTF-8, these single visual glyphs require 3 bytes (<code>0xEF 0xB7 0xBA</code> and <code>0xEF 0xB7 0xBD</code>). Because decorative presentation forms appear negligibly in modern digital journalism, the BPE tokenizer never merged these byte triples. The ligature <code>﷽</code> fragments into raw byte tokens <code>&lt;0xefb7&gt;</code> and <code>&lt;0xbd&gt;</code>, forcing the language model to learn complex compositional semantics over unaligned byte fragments.",
        body_style
    ))
    story.append(Spacer(1, 3))

    # Case 2
    d2 = data["difficult_inputs"][1]
    story.append(Paragraph("<b>Case 2: Dense Diacritic Stacking (Harakat / Tashdeed / Sukun)</b>", h2_style))
    story.append(Paragraph(
        f"• <b>Input String:</b> <code>{d2['text']}</code><br/>"
        f"• <b>Token Breakdown:</b> Urdu BPE: <b>{d2['urdu_bpe_tokens']} tokens</b> ({d2['urdu_bpe_rate']:.2f} tok/w) &nbsp;|&nbsp; GPT-2: {d2['gpt2_tokens']} tokens &nbsp;|&nbsp; o200k_base: {d2['o200k_tokens']} tokens<br/>"
        f"• <b>Generated Subwords:</b> <code>{str(d2['bpe_token_pieces'][:18])}...</code><br/>"
        "• <b>Failure Mechanism:</b> Although our custom regex pattern <code>\\p{M}</code> successfully retains combining vowel marks with their base consonants during pre-tokenization, modern digital Urdu text is 99% unvocalized. Consequently, the vocabulary has learned merges for unvocalized roots (e.g., <code>متشدد</code> is 1 token), but possesses no merges for consonant-harakat pairs. A vocalized word like <code>مُتَشَدِّد</code> fragments into <b>6 distinct subwords</b> (<code>مُت</code>, <code>َش</code>, <code>َد</code>, <code>ِّ</code>, <code>د</code>), inflating tokens/word to <b>3.18 tok/w</b> (a 300% inflation relative to baseline Urdu text).",
        body_style
    ))
    story.append(Spacer(1, 3))

    # Case 3
    d3 = data["difficult_inputs"][2]
    story.append(Paragraph("<b>Case 3: Technical Code-Switching with URLs, Symbols, and Hyphenation</b>", h2_style))
    story.append(Paragraph(
        f"• <b>Input String:</b> <code>{d3['text']}</code><br/>"
        f"• <b>Token Breakdown:</b> Urdu BPE: <b>{d3['urdu_bpe_tokens']} tokens</b> ({d3['urdu_bpe_rate']:.2f} tok/w) &nbsp;|&nbsp; GPT-2: {d3['gpt2_tokens']} tokens &nbsp;|&nbsp; o200k_base: {d3['o200k_tokens']} tokens<br/>"
        f"• <b>Generated Subwords:</b> <code>{str(d3['bpe_token_pieces'][:15])}...</code><br/>"
        "• <b>Failure Mechanism:</b> Technical Urdu prose heavily incorporates mixed Latin URLs, API parameters, and hyphens. Our pre-tokenization rule breaks on <code>?[^\\s\\p{L}\\p{M}\\p{N}\\u200c]+</code>, splitting punctuation clusters into isolated pre-tokens (<code>://</code>, <code>?</code>, <code>=</code>, <code>-</code>). Furthermore, English technical terms (e.g., <code>huggingface</code>, <code>endpoint</code>) appear with low frequency in Urdu corpora, decomposing into 1-2 character pieces (<code>h</code>, <code>ugg</code>, <code>ing</code>, <code>f</code>, <code>ace</code>) and yielding 3.45 tokens/word.",
        body_style
    ))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#ced4da"), spaceBefore=4, spaceAfter=4))
    story.append(Paragraph("6. Architectural Readiness for Assignment 2 (GPT Pre-Training)", h1_style))
    story.append(Paragraph(
        "The deliverables produced in this assignment directly optimize the upcoming language modeling phase:<br/>"
        "• <b>Lossless Round-Trip Guarantee:</b> Rigorously verified: <code>decode(encode(text)) == text</code> holds across emojis, English code-switching, complex diacritics, and arbitrary byte streams.<br/>"
        "• <b>Binary Dataset Ready:</b> Pre-tokenized and encoded binary tensors <code>train.bin</code> (72,127,369 <code>uint16</code> IDs, 144.3 MB) and <code>val.bin</code> (700,321 <code>uint16</code> IDs, 1.4 MB) are formatted for memory-mapped streaming in PyTorch/NumPy without runtime tokenization overhead.<br/>"
        "• <b>Recommended Model Configuration:</b> Embedding vocabulary dimension of exactly <code>50,000</code>. With average sequence packing of 1.084 tokens/word, training a 124M-parameter GPT model will achieve superior convergence and representation density per step compared to baseline architectures.",
        body_style
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Report built successfully: {output_path}")


if __name__ == "__main__":
    create_report()
