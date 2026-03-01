#!/usr/bin/env python3
import os
import sys
import json
import base64
import urllib.request
import urllib.error


def usage():
    print(
        "Usage:\n"
        "  python3 gemini_cleanup.py <input_image> [output_image] [model]\n\n"
        "Defaults:\n"
        "  output_image: ./cleaned_output.png\n"
        "  model: gemini-2.5-flash-image\n\n"
        "Env required:\n"
        "  GEMINI_API_KEY"
    )


def main():
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY is not set.")
        sys.exit(1)

    input_path = os.path.expanduser(sys.argv[1])
    output_path = os.path.expanduser(sys.argv[2]) if len(sys.argv) >= 3 else "./cleaned_output.png"
    model = sys.argv[3] if len(sys.argv) >= 4 else "gemini-2.5-flash-image"

    if not os.path.isfile(input_path):
        print(f"Error: input file not found: {input_path}")
        sys.exit(1)

    with open(input_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    prompt = (
        "Edit this bedroom photo for a real-estate listing. "
        "Remove only the clothing rack and clothes on the right side. "
        "Keep walls, doorway, mirror, and floor lines natural and straight. "
        "No blur or smear artifacts. Return only one edited image."
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_b64,
                        }
                    },
                ]
            }
        ]
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTPError {e.code}: {body[:2000]}")
        sys.exit(1)
    except Exception as e:
        print(f"Request failed: {e}")
        sys.exit(1)

    image_out_b64 = None
    for cand in data.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                image_out_b64 = inline["data"]
                break
        if image_out_b64:
            break

    if not image_out_b64:
        print("No image returned. Response excerpt:")
        print(json.dumps(data, indent=2)[:3000])
        sys.exit(1)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(base64.b64decode(image_out_b64))

    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
