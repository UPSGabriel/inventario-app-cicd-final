from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "informe-reflexion-cicd.pdf"

INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#526075")
BLUE = colors.HexColor("#1E5AA8")
GREEN = colors.HexColor("#168568")
LIGHT_BLUE = colors.HexColor("#EAF2FC")
LIGHT_GRAY = colors.HexColor("#F3F5F8")
WHITE = colors.white


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D8DEE8"))
    canvas.line(18 * mm, 14 * mm, A4[0] - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, "Examen Final - Practica CI/CD")
    canvas.drawRightString(
        A4[0] - 18 * mm,
        9 * mm,
        f"Gabriel Cordova y Jordy Espinoza  |  Pagina {doc.page}",
    )
    canvas.restoreState()


def build_pdf():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    document = BaseDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=19 * mm,
        title="Informe de reflexion - Practica CI/CD",
        author="Gabriel Alexander Cordova Solorzano y Jordy Espinoza",
        subject="Docker, GitHub Actions, Kubernetes, Blue-Green y metricas DORA",
    )
    frame = Frame(
        document.leftMargin,
        document.bottomMargin,
        document.width,
        document.height,
        id="main",
    )
    document.addPageTemplates([PageTemplate(id="report", frames=[frame], onPage=footer)])

    base = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleCustom",
        parent=base["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=23,
        textColor=INK,
        alignment=TA_CENTER,
        spaceAfter=5 * mm,
    )
    eyebrow = ParagraphStyle(
        "Eyebrow",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=BLUE,
        alignment=TA_CENTER,
        spaceAfter=1.5 * mm,
    )
    metadata = ParagraphStyle(
        "Metadata",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8.2,
        leading=11,
        textColor=MUTED,
        alignment=TA_CENTER,
        spaceAfter=5 * mm,
    )
    heading = ParagraphStyle(
        "HeadingCustom",
        parent=base["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=14,
        textColor=INK,
        spaceBefore=3.2 * mm,
        spaceAfter=1.8 * mm,
    )
    body = ParagraphStyle(
        "BodyCustom",
        parent=base["BodyText"],
        fontName="Helvetica",
        fontSize=8.7,
        leading=12.2,
        textColor=INK,
        alignment=TA_LEFT,
        spaceAfter=2.4 * mm,
    )
    body_small = ParagraphStyle(
        "BodySmall",
        parent=body,
        fontSize=7.8,
        leading=10.4,
        spaceAfter=1.2 * mm,
    )
    metric = ParagraphStyle(
        "Metric",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=8.2,
        leading=10.5,
        textColor=INK,
        spaceAfter=0,
    )
    callout = ParagraphStyle(
        "Callout",
        parent=body,
        fontSize=8.1,
        leading=11.3,
        leftIndent=4 * mm,
        rightIndent=4 * mm,
        textColor=INK,
        spaceBefore=1.5 * mm,
        spaceAfter=2.5 * mm,
    )

    story = [
        Paragraph("EXAMEN FINAL - PARTE I Y II", eyebrow),
        Paragraph("Practica CI/CD: informe de reflexion", title),
        Paragraph(
            "Gabriel Alexander Cordova Solorzano y Jordy Espinoza<br/>"
            "26 de julio de 2026 &nbsp;|&nbsp; "
            '<link href="https://github.com/UPSGabriel/inventario-app-cicd-final" '
            'color="#1E5AA8">Repositorio publico en GitHub</link>',
            metadata,
        ),
        Table(
            [
                [
                    Paragraph("<b>Pipeline</b><br/>npm test - Docker - Trivy - GHCR", body_small),
                    Paragraph("<b>Kubernetes</b><br/>RollingUpdate - probes - Secret", body_small),
                    Paragraph("<b>Estrategia</b><br/>Blue-Green nativo", body_small),
                ]
            ],
            colWidths=[document.width / 3] * 3,
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#C7D9F1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C7D9F1")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            ),
        ),
        Paragraph("1. Por que elegimos Blue-Green", heading),
        Paragraph(
            "La aplicacion expone <b>/version</b> con version, color y hostname. Esto hace "
            "posible validar GREEN antes del corte y demostrar de forma determinista que el "
            "Service cambia de <b>slot=blue</b> a <b>slot=green</b>. BLUE permanece levantado, "
            "por lo que un smoke test fallido se revierte cambiando nuevamente el selector. "
            "Para este laboratorio es mas claro que Canary, que necesita una muestra grande "
            "de peticiones para evidenciar una proporcion de trafico.",
            body,
        ),
        Paragraph(
            "La estrategia usa solo recursos nativos: dos Deployments y un Service. Su costo "
            "es mantener ambas versiones consumiendo recursos. Hay ademas una limitacion "
            "especifica de esta app: cada pod tiene su propio JSON. En produccion primero "
            "externalizariamos la base de datos para evitar catalogos divergentes.",
            body,
        ),
        Table(
            [
                [
                    Paragraph(
                        "<b>Flujo del corte</b><br/>"
                        "1. BLUE sirve v1.<br/>"
                        "2. GREEN v2 arranca y supera readiness.<br/>"
                        "3. El smoke test valida GREEN.<br/>"
                        "4. El Service cambia su selector.<br/>"
                        "5. Rollback = selector de vuelta a BLUE.",
                        callout,
                    )
                ]
            ],
            colWidths=[document.width],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D8DEE8")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            ),
        ),
        Paragraph("2. Que ocurrio con los datos", heading),
        Paragraph(
            "<b>DB_PATH=/app/data/products.json</b> apunta a un volumen <b>emptyDir</b>, "
            "cuyo ciclo de vida pertenece al pod. Al crear un producto y eliminar ese pod, "
            "el Deployment crea otro con un volumen nuevo y la aplicacion restaura los tres "
            "productos semilla. El producto desaparece. Con dos replicas tambien pueden "
            "verse catalogos diferentes segun el pod que responda. Es el comportamiento "
            "esperado de la practica, no un error que debia corregirse.",
            body,
        ),
        PageBreak(),
        Paragraph("METRICAS Y APRENDIZAJES", eyebrow),
        Paragraph("3. Metricas DORA propias", heading),
    ]

    metric_data = [
        [
            Paragraph("<b>Cambio</b>", body_small),
            Paragraph("<b>Commit</b>", body_small),
            Paragraph("<b>Disponible en cluster</b>", body_small),
            Paragraph("<b>Lead time</b>", body_small),
        ],
        [
            Paragraph("Runtime distroless<br/><font color='#526075'>285e565</font>", body_small),
            Paragraph("23-jul<br/>18:57:46", body_small),
            Paragraph("25-jul<br/>21:34:57.195", body_small),
            Paragraph("<b>50 h 37 min</b>", metric),
        ],
        [
            Paragraph("Arranque lento<br/><font color='#526075'>a07b964</font>", body_small),
            Paragraph("26-jul<br/>00:44:14", body_small),
            Paragraph("26-jul<br/>01:09:59.642", body_small),
            Paragraph("<b>25 min 45.643 s</b>", metric),
        ],
    ]
    story.extend(
        [
            Table(
                metric_data,
                colWidths=[55 * mm, 31 * mm, 43 * mm, 33 * mm],
                repeatRows=1,
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#CCD3DE")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                ),
            ),
            Spacer(1, 2.5 * mm),
            Table(
                [
                    [
                        Paragraph("<font color='#526075'>Lead time promedio</font><br/><b>25.5246 h</b>", metric),
                        Paragraph("<font color='#526075'>Frecuencia</font><br/><b>2 / 2 dias = 1 por dia</b>", metric),
                        Paragraph("<font color='#526075'>Change failure rate</font><br/><b>1 / 3 = 33.3 %</b>", metric),
                    ]
                ],
                colWidths=[document.width / 3] * 3,
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#E9F6F2")),
                        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#B9DFD3")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B9DFD3")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 7),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                ),
            ),
            Paragraph(
                "El CFR incluye un rollout que alcanzo el progress deadline y requirio "
                "corregir permisos, mas dos despliegues exitosos con timestamp. Los cambios "
                "del selector Blue-Green no se cuentan como nuevas promociones porque no "
                "cambian la imagen. Frente a la tabla clasica de clase, una promocion diaria "
                "y un lead time promedio cercano a un dia muestran rapidez; el 33.3 % de "
                "fallos evidencia que la estabilidad debe mejorar. La muestra es pequena y "
                "solo describe este laboratorio.",
                body,
            ),
            Paragraph("4. Problemas reales y como los resolvimos", heading),
        ]
    )

    problems = [
        (
            "Trivy bloqueo la imagen inicial",
            "El run 29980646258 fallo por vulnerabilidades CRITICAL. El runtime final se "
            "cambio a distroless; el run 30054762604 termino en verde antes de publicar.",
        ),
        (
            "El usuario no root no escribia el JSON",
            "Se mantuvo UID/GID 65532 y se agrego fsGroup=65532 para que /app/data sea "
            "escribible sin habilitar root ni quitar readOnlyRootFilesystem.",
        ),
        (
            "La app tarda 12 segundos en estar lista",
            "Durante ese periodo /health responde 503. Readiness tolera el arranque y "
            "liveness comienza despues; aumentar replicas no corregiria una sonda mal ajustada.",
        ),
        (
            "La reproduccion tenia un orden incorrecto",
            "El README aplicaba el Deployment antes de crear el Secret requerido. Se corrigio "
            "el orden y se agregaron scripts para el corte y el smoke test.",
        ),
    ]
    for index, (problem_title, description) in enumerate(problems, start=1):
        story.append(
            KeepTogether(
                [
                    Paragraph(f"<b>{index}. {problem_title}.</b> {description}", body),
                ]
            )
        )

    story.extend(
        [
            Paragraph("5. Conclusion", heading),
            Paragraph(
                "El flujo aplica fail-fast: pruebas, build, escaneo CRITICAL y publicacion "
                "SHA/latest. Kubernetes aporta RollingUpdate y un corte Blue-Green reversible. "
                "La siguiente mejora prioritaria es externalizar la base de datos e integrar "
                "el smoke test como verificacion automatica posterior al despliegue.",
                body,
            ),
        ]
    )

    document.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    build_pdf()
