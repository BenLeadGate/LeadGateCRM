from io import BytesIO
from datetime import datetime, timedelta
from calendar import monthrange
import urllib.request
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER

from ..models import Makler, Rechnung


def generiere_rechnungsnummer(rechnung: Rechnung, makler: Makler) -> str:
    """
    Generiert eine Rechnungsnummer im Format: 
    - Monatsabrechnung: LG-{Jahr}-{Monat}-{MaklerCode}{Nummer}
    - Beteiligungsabrechnung: LG-BET-{Jahr}-{MaklerCode}{Nummer}
    Beispiel: LG-2025-11-LYNR001 oder LG-BET-2025-LYNR001
    """
    # Rechnungs-Code aus Makler oder aus Firmenname ableiten
    if makler.rechnungs_code:
        makler_code = makler.rechnungs_code.upper().replace(" ", "")
    else:
        # Erste 4 Buchstaben des Firmennamens als Code
        makler_code = ''.join(c for c in makler.firmenname[:4] if c.isalnum()).upper()
        if len(makler_code) < 3:
            makler_code = makler.firmenname[:4].upper().replace(" ", "").replace(".", "").replace("-", "")
    rechnungs_nummer = f"{rechnung.id:03d}"
    
    if rechnung.rechnungstyp == "beteiligung":
        jahr = rechnung.erstellt_am.year if rechnung.erstellt_am else datetime.now().year
        return f"LG-BET-{jahr}-{makler_code}{rechnungs_nummer}"
    else:
        monat_str = f"{rechnung.monat:02d}"
        return f"LG-{rechnung.jahr}-{monat_str}-{makler_code}{rechnungs_nummer}"


def berechne_faelligkeitsdatum(monat: int, jahr: int) -> str:
    """
    Berechnet das Fälligkeitsdatum: 15. des nächsten Monats
    """
    naechster_monat = monat + 1
    naechstes_jahr = jahr
    if naechster_monat > 12:
        naechster_monat = 1
        naechstes_jahr = jahr + 1
    
    monatsnamen = [
        "", "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember"
    ]
    return f"15. {monatsnamen[naechster_monat]} {naechstes_jahr}"


def generiere_rechnung_pdf(rechnung: Rechnung, makler: Makler) -> BytesIO:
    """
    Generiert eine professionelle PDF-Rechnung im Apple-Stil mit Logo.
    Gibt einen BytesIO-Stream zurück.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        topMargin=15*mm, 
        bottomMargin=15*mm,
        leftMargin=18*mm,
        rightMargin=18*mm
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Apple-Stil Farben
    apple_blue = colors.HexColor('#0071e3')
    apple_dark = colors.HexColor('#1d1d1f')
    apple_gray = colors.HexColor('#86868b')
    apple_light_gray = colors.HexColor('#f5f5f7')
    apple_border = colors.HexColor('#d2d2d7')
    
    # Monatsnamen
    monatsnamen = [
        "", "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember"
    ]
    
    # Prüfe Rechnungstyp
    is_beteiligung = rechnung.rechnungstyp == "beteiligung"
    
    # Rechnungsnummer generieren
    rechnungsnummer = generiere_rechnungsnummer(rechnung, makler)
    
    # Datum formatieren (deutsche Monatsnamen)
    if rechnung.erstellt_am:
        tag = rechnung.erstellt_am.day
        monat = monatsnamen[rechnung.erstellt_am.month]
        jahr = rechnung.erstellt_am.year
        rechnungsdatum = f"{tag:02d}. {monat} {jahr}"
    else:
        jetzt = datetime.now()
        tag = jetzt.day
        monat = monatsnamen[jetzt.month]
        jahr = jetzt.year
        rechnungsdatum = f"{tag:02d}. {monat} {jahr}"
    
    # Fälligkeitsdatum berechnen (nur für Monatsabrechnungen)
    if is_beteiligung:
        # Für Beteiligungsabrechnungen: Fälligkeitsdatum ist 14 Tage nach Rechnungsdatum
        if rechnung.erstellt_am:
            faelligkeitsdatum_obj = rechnung.erstellt_am + timedelta(days=14)
        else:
            faelligkeitsdatum_obj = datetime.now() + timedelta(days=14)
        faelligkeitsdatum = f"{faelligkeitsdatum_obj.day:02d}. {monatsnamen[faelligkeitsdatum_obj.month]} {faelligkeitsdatum_obj.year}"
    else:
        faelligkeitsdatum = berechne_faelligkeitsdatum(rechnung.monat, rechnung.jahr)
    
    # Berechnung unterschiedlich für Beteiligungs- vs. Monatsabrechnung
    if is_beteiligung:
        # Bei Beteiligungsabrechnung: Netto ist bereits berechnet
        zwischensumme = rechnung.netto_betrag  # Netto
        mwst_betrag = zwischensumme * 0.19  # 19% MwSt
        gesamtbetrag_brutto = rechnung.gesamtbetrag  # Brutto (bereits berechnet)
    else:
        # Bei Monatsabrechnung: Netto = Anzahl * Preis, dann 19% MwSt, dann Brutto = Netto + MwSt
        zwischensumme = rechnung.anzahl_leads * rechnung.preis_pro_lead  # Netto
        mwst_betrag = zwischensumme * 0.19  # 19% MwSt
        gesamtbetrag_brutto = zwischensumme + mwst_betrag  # Brutto
    
    # Logo laden (versuche von URL) - mit korrektem Seitenverhältnis, kleiner
    logo_img = None
    try:
        logo_url = "https://leadgate.info/wp-content/uploads/2025/11/cropped-ChatGPT-Image-12.-Nov.-2025-00_37_51-1.png"
        logo_data = urllib.request.urlopen(logo_url).read()
        # Logo mit korrektem Seitenverhältnis laden - kleiner für professionelles Aussehen
        temp_img = Image(BytesIO(logo_data))
        # Breite festlegen, Höhe proportional berechnen - kleiner
        logo_width = 25*mm
        aspect_ratio = temp_img.imageWidth / temp_img.imageHeight
        logo_height = logo_width / aspect_ratio
        logo_img = Image(BytesIO(logo_data), width=logo_width, height=logo_height)
    except:
        pass  # Falls Logo nicht geladen werden kann, wird es übersprungen
    
    # Header mit Logo
    header_elements = []
    if logo_img:
        header_elements.append(logo_img)
        header_elements.append(Spacer(1, 8*mm))
    
    # Styles im Apple-Stil - kompakter für eine Seite
    company_style = ParagraphStyle(
        'Company',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica',
        textColor=apple_dark,
        leading=15,
        spaceAfter=1,
    )
    
    address_style = ParagraphStyle(
        'Address',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        textColor=apple_gray,
        leading=12,
        spaceAfter=0.5,
    )
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=22,
        fontName='Helvetica-Bold',
        textColor=apple_dark,
        spaceAfter=6,
        alignment=TA_LEFT,
        leading=26,
    )
    
    info_label_style = ParagraphStyle(
        'InfoLabel',
        parent=styles['Normal'],
        fontSize=8,
        fontName='Helvetica',
        textColor=apple_gray,
        leading=11,
        spaceAfter=1,
    )
    
    info_value_style = ParagraphStyle(
        'InfoValue',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        textColor=apple_dark,
        leading=13,
        spaceAfter=4,
    )
    
    recipient_label_style = ParagraphStyle(
        'RecipientLabel',
        parent=styles['Normal'],
        fontSize=8,
        fontName='Helvetica',
        textColor=apple_gray,
        leading=11,
        spaceAfter=2,
    )
    
    recipient_style = ParagraphStyle(
        'Recipient',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        textColor=apple_dark,
        leading=13,
        spaceAfter=1,
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        textColor=apple_dark,
        leading=13,
    )
    
    normal_small_style = ParagraphStyle(
        'NormalSmall',
        parent=styles['Normal'],
        fontSize=8,
        fontName='Helvetica',
        textColor=apple_gray,
        leading=11,
    )
    
    # Header-Bereich: Logo und Absender - kompakter
    absender_data = [
        [Paragraph("Lubitz Plewka GbR", company_style)],
        [Paragraph("LeadGate", company_style)],
        [Spacer(1, 1*mm)],
        [Paragraph("Fleher Straße 136", address_style)],
        [Paragraph("40223 Düsseldorf", address_style)],
        [Paragraph("info@leadgate.info", address_style)],
    ]
    
    # Rechnungsempfänger
    empfanger_data = [
        [Paragraph("Rechnungsempfänger", recipient_label_style)],
        [Paragraph(f"{makler.firmenname}", ParagraphStyle(
            'RecipientBold',
            parent=recipient_style,
            fontSize=10,
            fontName='Helvetica-Bold',
        ))],
    ]
    if makler.ansprechpartner:
        empfanger_data.append([Paragraph(makler.ansprechpartner, recipient_style)])
    if makler.adresse:
        for zeile in makler.adresse.split('\n'):
            if zeile.strip():
                empfanger_data.append([Paragraph(zeile, recipient_style)])
    empfanger_data.append([Paragraph(makler.email, recipient_style)])
    
    # Header-Tabelle: Logo/Absender links, Empfänger rechts
    header_table_data = [
        [absender_data, empfanger_data]
    ]
    header_table = Table(header_table_data, colWidths=[90*mm, 100*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    # Logo und Header kombinieren - kompakter
    if logo_img:
        logo_header_table = Table([[logo_img], [Spacer(1, 4*mm)], [header_table]], colWidths=[190*mm])
        logo_header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(logo_header_table)
    else:
        story.append(header_table)
    
    story.append(Spacer(1, 8*mm))
    
    # Rechnungstitel
    story.append(Paragraph("Rechnung", title_style))
    
    # Rechnungsinformationen im Apple-Stil
    info_data = [
        [Paragraph("Rechnungsnummer", info_label_style), Paragraph(rechnungsnummer, info_value_style)],
        [Paragraph("Rechnungsdatum", info_label_style), Paragraph(rechnungsdatum, info_value_style)],
    ]
    
    if is_beteiligung:
        info_data.append([Paragraph("Fälligkeitsdatum", info_label_style), Paragraph(faelligkeitsdatum, info_value_style)])
    else:
        if rechnung.monat and rechnung.jahr:
            info_data.append([Paragraph("Leistungszeitraum", info_label_style), Paragraph(f"{monatsnamen[rechnung.monat]} {rechnung.jahr}", info_value_style)])
        info_data.append([Paragraph("Fälligkeitsdatum", info_label_style), Paragraph(faelligkeitsdatum, info_value_style)])
    info_table = Table(info_data, colWidths=[50*mm, 140*mm])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 6*mm))
    
    # Rechnungstabelle im Apple-Stil
    if is_beteiligung:
        # Für Beteiligungsabrechnung: Zeige Lead-Details
        from ..models.lead import Lead
        from ..database import SessionLocal
        db = SessionLocal()
        lead = db.query(Lead).filter(Lead.id == rechnung.lead_id).first()
        db.close()
        
        lead_details = f"Lead #{lead.lead_nummer if lead and lead.lead_nummer else (lead.id if lead else 'N/A')}"
        if lead and lead.anbieter_name:
            lead_details += f" – {lead.anbieter_name}"
        
        def format_currency_inline(amount):
            return f"{amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') + " €"
        
        # Berechne unseren Anteil am Verkaufspreis (vor der 15% Berechnung)
        unser_anteil_am_verkauf = rechnung.verkaufspreis * (rechnung.beteiligungs_prozent / 100)
        
        verkaufspreis_formatiert = format_currency_inline(rechnung.verkaufspreis).replace(' €', '')
        anteil_formatiert = format_currency_inline(unser_anteil_am_verkauf).replace(' €', '')
        netto_formatiert = format_currency_inline(rechnung.netto_betrag).replace(' €', '')
        beschreibung_text = f'Beteiligungsabrechnung – Immobilienverkauf gemäß Vereinbarung.<br/><font color="#86868b" size="8">{lead_details}<br/>Verkaufspreis: {verkaufspreis_formatiert} €<br/>{rechnung.beteiligungs_prozent}% Beteiligung = {anteil_formatiert} € (davon 15% = {netto_formatiert} € Netto)</font>'
        
        table_data = [
            ['Position', 'Beschreibung', 'Zwischensumme'],
            [
                Paragraph('1', normal_style),
                Paragraph(beschreibung_text, normal_style),
                Paragraph(format_currency_inline(zwischensumme), normal_style)
            ]
        ]
        table = Table(table_data, colWidths=[20*mm, 140*mm, 30*mm])
    else:
        table_data = [
            ['Position', 'Beschreibung', 'Einzelpreis', 'Zwischensumme'],
            [
                Paragraph('1', normal_style),
                Paragraph(f'Leadbereitstellung – Immobilienverkäuferkontakte gemäß Vereinbarung.<br/><font color="#86868b" size="9">({rechnung.anzahl_leads} Leads)</font>', normal_style),
                Paragraph(f"{rechnung.preis_pro_lead:.2f} €", normal_style),
                Paragraph(f"{zwischensumme:.2f} €", normal_style)
            ]
        ]
        table = Table(table_data, colWidths=[20*mm, 110*mm, 30*mm, 30*mm])
    table.setStyle(TableStyle([
        # Header - Apple-Stil
        ('BACKGROUND', (0, 0), (-1, 0), apple_light_gray),
        ('TEXTCOLOR', (0, 0), (-1, 0), apple_dark),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('LEFTPADDING', (0, 0), (-1, 0), 6),
        ('RIGHTPADDING', (0, 0), (-1, 0), 6),
        # Daten
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), apple_dark),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, apple_border),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2 if is_beteiligung else 2, 1), (2 if is_beteiligung else 3, 1), 'RIGHT'),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('LEFTPADDING', (0, 1), (-1, -1), 6),
        ('RIGHTPADDING', (0, 1), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 6*mm))
    
    # Summen-Bereich im Apple-Stil
    def format_currency(amount):
        return f"{amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') + " €"
    
    summen_data = [
        [Paragraph('Zwischensumme', normal_style), Paragraph(format_currency(zwischensumme), normal_style)],
        [Paragraph('19 % Umsatzsteuer', normal_style), Paragraph(format_currency(mwst_betrag), normal_style)],
        [
            Paragraph('<b>Gesamtbetrag</b>', ParagraphStyle(
                'TotalLabel',
                parent=normal_style,
                fontSize=10,
                fontName='Helvetica-Bold',
            )),
            Paragraph(f"<b>{format_currency(gesamtbetrag_brutto)}</b>", ParagraphStyle(
                'TotalBold',
                parent=normal_style,
                fontSize=12,
                fontName='Helvetica-Bold',
                textColor=apple_blue,
            ))
        ],
    ]
    
    summen_table = Table(summen_data, colWidths=[140*mm, 50*mm])
    summen_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 2), (-1, 2), 6),
        ('BOTTOMPADDING', (0, 2), (-1, 2), 6),
        ('LINEABOVE', (0, 2), (-1, 2), 1, apple_border),
    ]))
    story.append(summen_table)
    story.append(Spacer(1, 6*mm))
    
    # Zahlungsinformationen
    zahlung_style = ParagraphStyle(
        'Zahlung',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        textColor=apple_dark,
        leading=13,
        spaceAfter=3,
    )
    
    gesamtbetrag_formatiert = f"{gesamtbetrag_brutto:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    story.append(Paragraph(
        f"Bitte überweisen Sie den Gesamtbetrag von <b>{gesamtbetrag_formatiert} €</b> bis spätestens {faelligkeitsdatum} auf das unten angegebene Konto.",
        zahlung_style
    ))
    story.append(Spacer(1, 4*mm))
    
    # Bankverbindung im Apple-Stil
    bank_label_style = ParagraphStyle(
        'BankLabel',
        parent=normal_style,
        fontSize=8,
        fontName='Helvetica',
        textColor=apple_gray,
        spaceAfter=3,
    )
    
    bank_data = [
        [Paragraph("Bankverbindung", bank_label_style)],
        [Paragraph("Kontoinhaber: Ben Lubitz", normal_style)],
        [Paragraph("IBAN: DE22 1001 0178 3687 6476 17", normal_style)],
        [Paragraph("BIC: REVODEB2", normal_style)],
        [Paragraph("Bank: Revolut Bank UAB (Zweigniederlassung Deutschland)", normal_style)],
        [Paragraph(f"Verwendungszweck: {rechnungsnummer}", normal_style)],
    ]
    bank_table = Table(bank_data, colWidths=[180*mm])
    bank_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    story.append(bank_table)
    story.append(Spacer(1, 5*mm))
    
    # Grußformel im Apple-Stil - kompakter
    story.append(Paragraph("Vielen Dank für die Zusammenarbeit.", normal_style))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("Mit freundlichen Grüßen", normal_style))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph("<b>Ben Lubitz</b>", normal_style))
    story.append(Paragraph("LeadGate | Lubitz Plewka GbR", normal_small_style))
    
    # PDF erstellen
    doc.build(story)
    buffer.seek(0)
    return buffer
