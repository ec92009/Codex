from pathlib import Path

W = 595
H = 842


def esc(txt: str) -> str:
    return txt.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def wrap(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines = []
    cur = []
    ln = 0
    for w in words:
        add = len(w) + (1 if cur else 0)
        if ln + add <= max_chars:
            cur.append(w)
            ln += add
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
            ln = len(w)
    if cur:
        lines.append(" ".join(cur))
    return lines


def draw_text(cmds: list[str], x: int, y: int, size: int, text: str, rgb=(0, 0, 0)) -> None:
    r, g, b = rgb
    cmds.append(f"{r:.3f} {g:.3f} {b:.3f} rg")
    cmds.append("BT")
    cmds.append(f"/F1 {size} Tf")
    cmds.append(f"1 0 0 1 {x} {y} Tm")
    cmds.append(f"({esc(text)}) Tj")
    cmds.append("ET")


def draw_wrapped(cmds: list[str], x: int, y: int, size: int, text: str, max_chars: int, leading: int = 14, rgb=(0, 0, 0)) -> int:
    lines = wrap(text, max_chars)
    yy = y
    for line in lines:
        draw_text(cmds, x, yy, size, line, rgb)
        yy -= leading
    return yy


def build_content(lang: str) -> list[str]:
    c: list[str] = []

    # Background and card
    c.append("0.965 0.957 0.925 rg")
    c.append(f"0 0 {W} {H} re f")
    c.append("0.992 0.988 0.973 rg")
    c.append("34 36 527 770 re f")
    c.append("0.90 0.87 0.80 RG 1.2 w")
    c.append("34 36 527 770 re S")

    green = (0.13, 0.30, 0.24)
    dark = (0.12, 0.15, 0.20)
    muted = (0.42, 0.45, 0.50)

    draw_text(c, 58, 778, 18, "OLEA STAGING", green)
    draw_text(c, 58, 760, 10, "Malaga - Marbella corridor", muted)

    if lang == "EN":
        draw_text(c, 355, 778, 11, "One-Page Offer Sheet", green)
        y = 730
        draw_text(c, 58, y, 11, "WHO THIS IS FOR", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "Real-estate agencies and independent agents listing homes in the Malaga-Marbella corridor.", 92, 13, dark)

        y -= 12
        draw_text(c, 58, y, 11, "ENTRY OFFER", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "Photo Boost + Virtual Staging Add-On for a stronger first impression and more qualified inquiries.", 92, 13, dark)

        y -= 10
        draw_text(c, 58, y, 11, "PHOTO BOOST INCLUDES", green)
        y -= 18
        bullets = [
            "On-site photo session (up to 90 minutes)",
            "20-30 professionally edited images",
            "HDR/light correction + perspective straightening",
            "Web-ready and high-resolution delivery",
            "48-hour delivery target",
        ]
        for b in bullets:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 6
        draw_text(c, 58, y, 11, "VIRTUAL STAGING ADD-ON", green)
        y -= 18
        vbul = [
            "3 key rooms staged virtually",
            "Buyer-profile style matching",
            "Before/after files included",
            "+24 hours on top of base delivery",
        ]
        for b in vbul:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 8
        draw_text(c, 58, y, 11, "STARTER PRICING", green)
        y -= 18
        for p in [
            "Photo Boost: EUR 220 per property",
            "Virtual Staging Add-On (3 rooms): EUR 120",
            "Bundle: EUR 320",
            "Pilot Package (3 listings in 30 days): EUR 900",
        ]:
            draw_text(c, 70, y, 10, f"- {p}", dark)
            y -= 14

        y -= 4
        draw_text(c, 58, y, 11, "GUARANTEE", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "If we miss the agreed deadline, your next listing gets a 15% service credit.", 92, 13, dark)

    else:
        draw_text(c, 380, 778, 11, "Hoja de Oferta", green)
        y = 730
        draw_text(c, 58, y, 11, "PARA QUIEN ES", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "Agencias inmobiliarias y agentes independientes con anuncios de vivienda en el corredor Malaga-Marbella.", 92, 13, dark)

        y -= 12
        draw_text(c, 58, y, 11, "OFERTA DE ENTRADA", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "Photo Boost + Add-On de Home Staging Virtual para mejorar primera impresion y captar contactos cualificados.", 92, 13, dark)

        y -= 10
        draw_text(c, 58, y, 11, "INCLUYE PHOTO BOOST", green)
        y -= 18
        bullets = [
            "Sesion de fotos en propiedad (hasta 90 minutos)",
            "20-30 imagenes editadas profesionalmente",
            "Correccion HDR/luz + perspectivas rectas",
            "Entrega web + alta resolucion",
            "Objetivo de entrega en 48 horas",
        ]
        for b in bullets:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 6
        draw_text(c, 58, y, 11, "ADD-ON DE STAGING VIRTUAL", green)
        y -= 18
        vbul = [
            "3 estancias clave amuebladas virtualmente",
            "Estilo segun perfil de comprador",
            "Incluye archivos antes/despues",
            "+24 horas sobre la entrega base",
        ]
        for b in vbul:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 8
        draw_text(c, 58, y, 11, "PRECIOS DE INICIO", green)
        y -= 18
        for p in [
            "Photo Boost: 220 EUR por propiedad",
            "Add-On Virtual (3 estancias): 120 EUR",
            "Pack: 320 EUR",
            "Paquete Piloto (3 propiedades en 30 dias): 900 EUR",
        ]:
            draw_text(c, 70, y, 10, f"- {p}", dark)
            y -= 14

        y -= 4
        draw_text(c, 58, y, 11, "GARANTIA", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "Si no cumplimos el plazo acordado, tu siguiente anuncio recibe un credito del 15%.", 92, 13, dark)

    # Footer
    draw_text(c, 58, 70, 10, "Contacto: hello@oleastaging.com | +34 XXX XXX XXX", dark)

    return c


def make_pdf(path: Path, lang: str) -> None:
    content = "\n".join(build_content(lang)).encode("latin-1", errors="replace")

    objs = []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>".encode("ascii"))
    objs.append(f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{i} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(objs)+1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    pdf.extend(
        f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )

    path.write_bytes(pdf)


def main() -> None:
    root = Path(__file__).resolve().parent
    make_pdf(root / "OleaStaging-Offer-EN.pdf", "EN")
    make_pdf(root / "OleaStaging-Oferta-ES.pdf", "ES")


if __name__ == "__main__":
    main()
