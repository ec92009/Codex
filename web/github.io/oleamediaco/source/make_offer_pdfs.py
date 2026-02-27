from pathlib import Path
import subprocess
import tempfile
from typing import Optional, Tuple

W = 595
H = 842


def jpeg_size(data: bytes) -> tuple[int, int]:
    if not data.startswith(b"\xff\xd8"):
        raise ValueError("Not a JPEG file")
    i = 2
    n = len(data)
    while i < n - 1:
        if data[i] != 0xFF:
            i += 1
            continue
        while i < n and data[i] == 0xFF:
            i += 1
        if i >= n:
            break
        marker = data[i]
        i += 1
        if marker in (0xD8, 0xD9):
            continue
        if marker == 0xDA:  # Start of scan
            break
        if i + 1 >= n:
            break
        seg_len = (data[i] << 8) | data[i + 1]
        if seg_len < 2 or i + seg_len > n:
            break
        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }:
            if i + 7 >= n:
                break
            h = (data[i + 3] << 8) | data[i + 4]
            w = (data[i + 5] << 8) | data[i + 6]
            return w, h
        i += seg_len
    raise ValueError("Could not read JPEG dimensions")


def png_to_jpeg_bytes(png_path: Path) -> tuple[bytes, int, int]:
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        subprocess.run(
            ["sips", "-s", "format", "jpeg", str(png_path), "--out", str(tmp_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        data = tmp_path.read_bytes()
        w, h = jpeg_size(data)
        return data, w, h
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


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


def build_content(lang: str, before_size: Optional[Tuple[int, int]] = None, after_size: Optional[Tuple[int, int]] = None) -> list[str]:
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

    draw_text(c, 58, 778, 18, "OLEA MEDIA CO", green)
    header_corridor = "Málaga - Marbella corridor" if lang == "ES" else "Malaga - Marbella corridor"
    draw_text(c, 58, 760, 10, header_corridor, muted)

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
        draw_text(c, 58, y, 11, "PARA QUIÉN ES", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "Agencias inmobiliarias y agentes independientes con anuncios de vivienda en el corredor Málaga-Marbella.", 92, 13, dark)

        y -= 12
        draw_text(c, 58, y, 11, "MODELO DE SERVICIO (4 ETAPAS)", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "Elige la etapa según cada inmueble, desde mejora rápida hasta staging físico con fotos finales.", 92, 13, dark)

        y -= 10
        draw_text(c, 58, y, 11, "ETAPA 1: MEJORA DE FOTOS EXISTENTES", green)
        y -= 18
        bullets = [
            "Usamos las fotos actuales del anuncio",
            "Mejoramos luz, color y verticales",
            "Mejora rápida sin sesión en propiedad",
        ]
        for b in bullets:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 6
        draw_text(c, 58, y, 11, "ETAPA 2: NUEVA SESIÓN EN PROPIEDAD", green)
        y -= 18
        for b in [
            "Sesión en propiedad de hasta 90 minutos",
            "20-30 imágenes editadas profesionalmente",
            "Propietario/agente prepara la vivienda antes",
        ]:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 6
        draw_text(c, 58, y, 11, "ETAPA 3: STAGING VIRTUAL", green)
        y -= 18
        vbul = [
            "Estancias clave amuebladas virtualmente",
            "Estilo según perfil de comprador",
            "Incluye archivos antes/después",
        ]
        for b in vbul:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 6
        draw_text(c, 58, y, 11, "ETAPA 4: STAGING REAL + FOTOS", green)
        y -= 18
        for b in [
            "Coordinación de staging físico en propiedad",
            "Fotos profesionales del resultado final",
            "Opción premium para inmuebles de alto valor",
        ]:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 8
        draw_text(c, 58, y, 11, "PRECIOS POR ETAPA", green)
        y -= 18
        for p in [
            "Etapa 1 (Mejora): desde 90 EUR",
            "Etapa 2 (Nueva sesión): desde 220 EUR",
            "Etapa 3 (Staging virtual): desde 120 EUR (3 estancias)",
            "Etapa 4 (Staging real + fotos): desde 650 EUR",
        ]:
            draw_text(c, 70, y, 10, f"- {p}", dark)
            y -= 14

        y -= 4
        draw_text(c, 58, y, 11, "GARANTÍA", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "Si no cumplimos el plazo acordado, tu siguiente anuncio recibe un crédito del 15%.", 92, 13, dark)

    elif lang == "FR":
        draw_text(c, 390, 778, 11, "Offre 1 page", green)
        y = 730
        draw_text(c, 58, y, 11, "POUR QUI", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "Agences immobilières et agents indépendants avec des biens à vendre sur le corridor Malaga-Marbella.", 92, 13, dark)

        y -= 12
        draw_text(c, 58, y, 11, "MODÈLE DE SERVICE (4 ÉTAPES)", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "Choisissez l'étape adaptée à chaque bien, de la retouche rapide au staging réel avec photos finales.", 92, 13, dark)

        y -= 10
        draw_text(c, 58, y, 11, "ÉTAPE 1: RETOUCHE DES PHOTOS EXISTANTES", green)
        y -= 18
        for b in [
            "Utilisation des photos actuelles de l'annonce",
            "Correction lumière, couleur et verticales",
            "Amélioration rapide sans visite sur place",
        ]:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 6
        draw_text(c, 58, y, 11, "ÉTAPE 2: NOUVELLE SÉANCE PHOTO SUR PLACE", green)
        y -= 18
        for b in [
            "Séance sur place jusqu'à 90 minutes",
            "20-30 images retouchées professionnellement",
            "Le propriétaire/l'agent prépare le bien avant la séance",
        ]:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 6
        draw_text(c, 58, y, 11, "ÉTAPE 3: STAGING VIRTUEL", green)
        y -= 18
        for b in [
            "Pièces clés aménagées virtuellement",
            "Style adapté au profil acheteur",
            "Fichiers avant/après inclus",
        ]:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 6
        draw_text(c, 58, y, 11, "ÉTAPE 4: STAGING RÉEL + PHOTOS", green)
        y -= 18
        for b in [
            "Coordination d'un staging réel sur place",
            "Photos professionnelles du résultat final",
            "Option premium pour biens haut de gamme",
        ]:
            y = draw_wrapped(c, 70, y, 10, f"- {b}", 90, 13, dark)

        y -= 8
        draw_text(c, 58, y, 11, "TARIFS PAR ÉTAPE", green)
        y -= 18
        for p in [
            "Étape 1 (Retouche): à partir de 90 EUR",
            "Étape 2 (Nouvelle séance): à partir de 220 EUR",
            "Étape 3 (Staging virtuel): à partir de 120 EUR (3 pièces)",
            "Étape 4 (Staging réel + photos): à partir de 650 EUR",
        ]:
            draw_text(c, 70, y, 10, f"- {p}", dark)
            y -= 14

        y -= 4
        draw_text(c, 58, y, 11, "GARANTIE", green)
        y -= 18
        y = draw_wrapped(c, 58, y, 10, "Si nous manquons le délai convenu, votre prochaine annonce reçoit un crédit de 15%.", 92, 13, dark)

    else:
        raise ValueError(f"Unsupported language: {lang}")

    # Compact before/after image strip on the same page
    if before_size and after_size:
        labels = {
            "EN": ("Before", "After", "Before/After Example"),
            "ES": ("Antes", "Despues", "Ejemplo Antes/Despues"),
            "FR": ("Avant", "Apres", "Exemple Avant/Apres"),
        }
        before_lbl, after_lbl, strip_title = labels[lang]
        box = 86
        gap = 12
        left_x = 58
        right_x = left_x + box + gap
        img_y = 118
        title_y = 242
        label_y = 210

        draw_text(c, 58, title_y, 10, strip_title, green)
        c.append("0.965 0.962 0.950 rg")
        c.append(f"{left_x-4} {img_y-4} {box+8} {box+8} re f")
        c.append(f"{right_x-4} {img_y-4} {box+8} {box+8} re f")
        c.append("0.82 0.80 0.75 RG 1 w")
        c.append(f"{left_x-4} {img_y-4} {box+8} {box+8} re S")
        c.append(f"{right_x-4} {img_y-4} {box+8} {box+8} re S")

        bw, bh = before_size
        aw, ah = after_size
        draw_image_cover(c, "ImBefore", left_x, img_y, box, bw, bh)
        draw_image_cover(c, "ImAfter", right_x, img_y, box, aw, ah)
        draw_text(c, left_x, label_y, 9, before_lbl, dark)
        draw_text(c, right_x, label_y, 9, after_lbl, dark)

    # Footer
    draw_text(c, 58, 70, 10, "Contacto: hello@oleamediaco.com | +34 XXX XXX XXX", dark)

    return c


def draw_image_cover(cmds: list[str], name: str, x: int, y: int, box: int, img_w: int, img_h: int) -> None:
    scale = max(box / img_w, box / img_h)
    w = img_w * scale
    h = img_h * scale
    dx = x - (w - box) / 2
    dy = y - (h - box) / 2
    cmds.append("q")
    cmds.append(f"{x} {y} {box} {box} re W n")
    cmds.append(f"{w:.3f} 0 0 {h:.3f} {dx:.3f} {dy:.3f} cm")
    cmds.append(f"/{name} Do")
    cmds.append("Q")


def make_pdf(path: Path, lang: str, before_jpg: tuple[bytes, int, int], after_jpg: tuple[bytes, int, int]) -> None:
    before_bytes, before_w, before_h = before_jpg
    after_bytes, after_w, after_h = after_jpg
    content1 = "\n".join(build_content(lang, (before_w, before_h), (after_w, after_h))).encode("latin-1", errors="replace")

    objs = []
    # 1 catalog, 2 pages, 3 page, 4 content, 5 font, 6 imgBefore, 7 imgAfter
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    res1 = b"<< /Font << /F1 5 0 R >> /XObject << /ImBefore 6 0 R /ImAfter 7 0 R >> >>"
    objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] /Contents 4 0 R /Resources ".encode("ascii") + res1 + b" >>")
    objs.append(f"<< /Length {len(content1)} >>\nstream\n".encode("ascii") + content1 + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objs.append(
        f"<< /Type /XObject /Subtype /Image /Width {before_w} /Height {before_h} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(before_bytes)} >>\nstream\n".encode("ascii")
        + before_bytes
        + b"\nendstream"
    )
    objs.append(
        f"<< /Type /XObject /Subtype /Image /Width {after_w} /Height {after_h} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(after_bytes)} >>\nstream\n".encode("ascii")
        + after_bytes
        + b"\nendstream"
    )

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
    assets = root / "site" / "assets"
    before_jpg = png_to_jpeg_bytes(assets / "before.png")
    after_jpg = png_to_jpeg_bytes(assets / "after.png")
    make_pdf(root / "OleaMediaCo-Offer-EN.pdf", "EN", before_jpg, after_jpg)
    make_pdf(root / "OleaMediaCo-Oferta-ES.pdf", "ES", before_jpg, after_jpg)
    make_pdf(root / "OleaMediaCo-Offre-FR.pdf", "FR", before_jpg, after_jpg)


if __name__ == "__main__":
    main()
