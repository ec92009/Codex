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
        draw_text(c, 58, y, 11, "SERVICE MODEL (4 STAGES)", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "Choose the stage needed for each listing, from quick cleanup to full staging and photography.", 92, 13, dark)

        y -= 10
        draw_text(c, 58, y, 11, "STAGE 1: EXISTING PHOTOS CLEANUP", green)
        y -= 18
        bullets = [
            "Use the listing's current photos",
            "Clean up lighting, color, and vertical lines",
            "Fast improvement with no on-site session",
        ]
        for b in bullets:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 6
        draw_text(c, 58, y, 11, "STAGE 2: NEW ON-SITE PHOTO SHOOT", green)
        y -= 18
        for b in [
            "On-site session up to 90 minutes",
            "20-30 professionally edited images",
            "Owner/agent prepares the property before shoot",
        ]:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 6
        draw_text(c, 58, y, 11, "STAGE 3: VIRTUAL STAGING", green)
        y -= 18
        vbul = [
            "Virtually staged key rooms",
            "Buyer-profile style matching",
            "Before/after files included",
        ]
        for b in vbul:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 6
        draw_text(c, 58, y, 11, "STAGE 4: PHYSICAL STAGING + SHOOT", green)
        y -= 18
        for b in [
            "Actual on-site staging coordination",
            "Professional photos of final staged setup",
            "Premium option for high-value listings",
        ]:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 8
        draw_text(c, 58, y, 11, "PRICING BY STAGE", green)
        y -= 18
        for p in [
            "Stage 1 (Cleanup): from EUR 90",
            "Stage 2 (New Shoot): from EUR 220",
            "Stage 3 (Virtual Staging): from EUR 120 (3 rooms)",
            "Stage 4 (Physical Staging + Shoot): from EUR 650",
        ]:
            draw_text(c, 70, y, 10, f"- {p}", dark)
            y -= 14

        y -= 4
        draw_text(c, 58, y, 11, "GUARANTEE", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "If we miss the agreed deadline, your next listing gets a 15% service credit.", 92, 13, dark)

    elif lang == "ES":
        draw_text(c, 380, 778, 11, "Hoja de Oferta", green)
        y = 730
        draw_text(c, 58, y, 11, "PARA QUIEN ES", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "Agencias inmobiliarias y agentes independientes con anuncios de vivienda en el corredor Malaga-Marbella.", 92, 13, dark)

        y -= 12
        draw_text(c, 58, y, 11, "MODELO DE SERVICIO (4 ETAPAS)", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "Elige la etapa segun cada inmueble, desde mejora rapida hasta staging fisico con fotos finales.", 92, 13, dark)

        y -= 10
        draw_text(c, 58, y, 11, "ETAPA 1: MEJORA DE FOTOS EXISTENTES", green)
        y -= 18
        bullets = [
            "Usamos las fotos actuales del anuncio",
            "Mejoramos luz, color y verticales",
            "Mejora rapida sin sesion en propiedad",
        ]
        for b in bullets:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 6
        draw_text(c, 58, y, 11, "ETAPA 2: NUEVA SESION EN PROPIEDAD", green)
        y -= 18
        for b in [
            "Sesion en propiedad de hasta 90 minutos",
            "20-30 imagenes editadas profesionalmente",
            "Propietario/agente prepara la vivienda antes",
        ]:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 6
        draw_text(c, 58, y, 11, "ETAPA 3: STAGING VIRTUAL", green)
        y -= 18
        vbul = [
            "Estancias clave amuebladas virtualmente",
            "Estilo segun perfil de comprador",
            "Incluye archivos antes/despues",
        ]
        for b in vbul:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 6
        draw_text(c, 58, y, 11, "ETAPA 4: STAGING REAL + FOTOS", green)
        y -= 18
        for b in [
            "Coordinacion de staging fisico en propiedad",
            "Fotos profesionales del resultado final",
            "Opcion premium para inmuebles de alto valor",
        ]:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 8
        draw_text(c, 58, y, 11, "PRECIOS POR ETAPA", green)
        y -= 18
        for p in [
            "Etapa 1 (Mejora): desde 90 EUR",
            "Etapa 2 (Nueva sesion): desde 220 EUR",
            "Etapa 3 (Staging virtual): desde 120 EUR (3 estancias)",
            "Etapa 4 (Staging real + fotos): desde 650 EUR",
        ]:
            draw_text(c, 70, y, 10, f"- {p}", dark)
            y -= 14

        y -= 4
        draw_text(c, 58, y, 11, "GARANTIA", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "Si no cumplimos el plazo acordado, tu siguiente anuncio recibe un credito del 15%.", 92, 13, dark)

    elif lang == "FR":
        draw_text(c, 390, 778, 11, "Offre 1 page", green)
        y = 730
        draw_text(c, 58, y, 11, "POUR QUI", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "Agences immobilieres et agents independants avec des biens a vendre sur le corridor Malaga-Marbella.", 92, 13, dark)

        y -= 12
        draw_text(c, 58, y, 11, "MODELE DE SERVICE (4 ETAPES)", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "Choisissez l etape adaptee a chaque bien, de la retouche rapide au staging reel avec photos finales.", 92, 13, dark)

        y -= 10
        draw_text(c, 58, y, 11, "ETAPE 1: RETOUCHE DES PHOTOS EXISTANTES", green)
        y -= 18
        for b in [
            "Utilisation des photos actuelles de l annonce",
            "Correction lumiere, couleur et verticales",
            "Amelioration rapide sans visite sur place",
        ]:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 6
        draw_text(c, 58, y, 11, "ETAPE 2: NOUVELLE SEANCE PHOTO SUR PLACE", green)
        y -= 18
        for b in [
            "Seance sur place jusqu a 90 minutes",
            "20-30 images retouchees professionnellement",
            "Le proprietaire/agent prepare le bien avant la seance",
        ]:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 6
        draw_text(c, 58, y, 11, "ETAPE 3: STAGING VIRTUEL", green)
        y -= 18
        for b in [
            "Pieces cles amenagees virtuellement",
            "Style adapte au profil acheteur",
            "Fichiers avant/apres inclus",
        ]:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 6
        draw_text(c, 58, y, 11, "ETAPE 4: STAGING REEL + PHOTOS", green)
        y -= 18
        for b in [
            "Coordination du staging reel sur place",
            "Photos professionnelles du resultat final",
            "Option premium pour biens haut de gamme",
        ]:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 8
        draw_text(c, 58, y, 11, "TARIFS PAR ETAPE", green)
        y -= 18
        for p in [
            "Etape 1 (Retouche): a partir de 90 EUR",
            "Etape 2 (Nouvelle seance): a partir de 220 EUR",
            "Etape 3 (Staging virtuel): a partir de 120 EUR (3 pieces)",
            "Etape 4 (Staging reel + photos): a partir de 650 EUR",
        ]:
            draw_text(c, 70, y, 10, f"- {p}", dark)
            y -= 14

        y -= 4
        draw_text(c, 58, y, 11, "GARANTIE", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "Si nous manquons le delai convenu, votre prochaine annonce recoit un credit de 15%.", 92, 13, dark)

    else:
        raise ValueError(f"Unsupported language: {lang}")

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
    make_pdf(root / "OleaStaging-Offre-FR.pdf", "FR")


if __name__ == "__main__":
    main()
