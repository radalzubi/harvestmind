"""One-page brief for Ahmad Al-Sallakh, CEO of Al Burger (Amman, Jordan).

Context: he is the father of a friend, so no credentialing and no pitch
framing. Goal is that he finishes the page knowing exactly what this is and
exactly what is being asked, with no room to misread it as a sales approach.
No em dashes, product name omitted (still tentative).

Run:  python3 docs/outreach/generators/make_brief_al_burger.py
"""
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

OUT = "docs/outreach/brief_al_burger.pdf"

INK, ACCENT = HexColor("#1a1a1a"), HexColor("#2e5d3b")
MUTED, RULE = HexColor("#5a5a5a"), HexColor("#c9c9c9")

title = ParagraphStyle("t", fontName="Times-Bold", fontSize=15, leading=17.5,
                       textColor=INK, spaceAfter=2)
sub = ParagraphStyle("s", fontName="Times-Italic", fontSize=10.5, leading=13,
                     textColor=MUTED, spaceAfter=1)
prep = ParagraphStyle("p", fontName="Helvetica", fontSize=8.2, leading=10.5,
                      textColor=MUTED, spaceBefore=3)
head = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=8.6,
                      leading=11, textColor=ACCENT, spaceBefore=7, spaceAfter=2)
body = ParagraphStyle("b", fontName="Times-Roman", fontSize=9.4, leading=11.7,
                      textColor=INK, alignment=TA_JUSTIFY)
bullet = ParagraphStyle("bu", parent=body, leftIndent=13, bulletIndent=3,
                        spaceAfter=2.5, alignment=0)
sign = ParagraphStyle("so", fontName="Times-Bold", fontSize=9.4, leading=12,
                      textColor=INK, spaceBefore=7)


def B(label, text):
    return Paragraph(f"<bullet>&bull;</bullet><b>{label}</b> {text}", bullet)


doc = SimpleDocTemplate(
    OUT, pagesize=letter,
    leftMargin=0.8 * inch, rightMargin=0.8 * inch,
    topMargin=0.5 * inch, bottomMargin=0.45 * inch,
    title="Measuring What Fresh Buying Really Costs",
    author="Rad Al Zubi & Mustafa Sabieha")

story = [
    Paragraph("Measuring What Fresh Buying Really Costs", title),
    Paragraph("What we built, and the one thing we are asking for", sub),
    Paragraph("Prepared for Ahmad Al-Sallakh, Al Burger, Amman", prep),
    HRFlowable(width="100%", thickness=0.5, color=RULE, spaceBefore=5),

    Paragraph("IN ONE PARAGRAPH", head),
    Paragraph(
        "We built software for businesses that buy and sell fresh food. It "
        "reads the ordering and delivery records a business already keeps, "
        "usually spreadsheets or an accounting export, and turns them into a "
        "clear report: how much money was lost to product thrown away, how "
        "much was lost to running out of items, which suppliers actually "
        "deliver what they promise, and which customers are not being served "
        "reliably. Most operations have never seen those four numbers for "
        "their own business. That report is what we do.", body),

    Paragraph("THE PROBLEM IT ADDRESSES", head),
    Paragraph(
        "Fresh food has to be ordered before anyone knows two things: how "
        "much will actually sell, and how much the supplier will actually "
        "deliver. Order too much and it is thrown away. Order too little and "
        "you are out of an item at the busiest hour. Both are real money, "
        "and both usually disappear into the monthly margin without ever "
        "being counted separately. Our software counts them, then recommends "
        "how much to order from each supplier given how reliable that "
        "supplier has actually been.", body),

    Paragraph("WHAT WE ARE ASKING YOU FOR", head),
    Paragraph(
        "An introduction to one or two of the suppliers or distributors you "
        "buy from. That is the whole request.", body),
    Paragraph(
        "The businesses our software is built for are one step upstream of a "
        "restaurant: the produce, meat, and dairy suppliers and the "
        "distributors who deliver to kitchens like yours. You work with them "
        "every week and know which ones are well run and which ones "
        "struggle. We would like to meet one or two of them.", body),

    Paragraph("WHAT THE SUPPLIER WOULD GET, AND WHAT IT COSTS THEM", head),
    B("What we would ask of them.", "Six to twelve months of their ordering "
      "and delivery history, exported from whatever system they use. A "
      "simple spreadsheet is enough."),
    B("What they receive.", "A written report on their own business showing "
      "where their money is actually going: waste, shortages, supplier "
      "reliability, and customer service levels, in dinars."),
    B("What it costs them.", "Nothing. There is no fee, no software to "
      "install, and no obligation afterwards. We sign a confidentiality "
      "agreement before receiving anything, use their records only to "
      "produce their own report, and never share or sell them."),

    Paragraph("WHY WE ARE DOING IT THIS WAY", head),
    Paragraph(
        "The software works, but it has only ever been tested on simulated "
        "data that we generated ourselves. Before we can honestly tell "
        "anyone it is useful, it needs to run on the records of a real "
        "business. That is the only thing we are missing, and it is why we "
        "are offering the analysis free rather than selling it.", body),

    Paragraph("IF IT IS USEFUL TO YOU", head),
    Paragraph(
        "If you would like the same view of your own purchasing, meaning how "
        "reliably each of your suppliers actually fills what Al Burger "
        "orders and what the gaps have cost, we would be glad to run that "
        "for you on the same terms. Entirely up to you, and separate from "
        "the introduction.", body),

    Spacer(1, 5),
    Paragraph("Happy to explain any of this further whenever it suits you. "
              "Thank you for reading it.", body),
    Paragraph("Rad Al Zubi and Mustafa Sabieha", sign),
]

doc.build(story)
print("wrote", OUT)
