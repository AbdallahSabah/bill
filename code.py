import streamlit as st
import pdfplumber
import fitz  # PyMuPDF
import tempfile
import re
import os

st.set_page_config(page_title="Bill of Lading Generator", layout="centered")
st.title("📦 Bill of Lading PDF Generator")

uploaded_format = st.file_uploader("Upload Template PDF (format.pdf)", type=["pdf"])
uploaded_original = st.file_uploader("Upload Original PDF", type=["pdf"])

def extract_info(text):
    data = {
        "exporter": "VERO SHIPPING LLC",
        "exporter_address": "7801 BERGENLINE AVE, NORTH BERGEN, NJ 07047, USA",
        "consignee": "THE ERA OF INTEGRATED SPEED SPC",
        "carrier": "MAERSK",
        "port_loading": "SAVANNAH, GA",
        "port_delivery": "SALALAH, OMAN",
        "vessel": "MAERSK",
        "voyage": "HARTFORD / 518E",
        "container_size": "1 x 40 HC",
    }

    # Booking#
    booking_matches = re.findall(r"(WR\s+[A-Z0-9]+WR)", text)
    data["booking"] = booking_matches[0] if booking_matches else "UNKNOWN"

    # Vehicles
    vehicles = []
    total_weight = 0.0
    container = None
    seal = None

    # Match vehicle blocks
    vehicle_blocks = re.findall(
        r"(WR\s+[A-Z0-9]+WR).*?(\d{4})\s+(.*?)\s+\(?[A-Z]*\)?\s+([\d,.]+)\s*Kg.*?VIN:([A-Z0-9]+)",
        text, re.DOTALL
    )

    for match in vehicle_blocks:
        booking_num, year, model, weight, vin = match
        weight = float(weight.replace(",", ""))
        vehicles.append(f"{year} {model}; VIN:{vin} {weight:.2f} KGS")
        total_weight += weight
        if not data.get("container_number"):
            container = "CAAU8573250"
            seal = "02456"

    data["vehicles"] = vehicles
    data["total_weight"] = f"{total_weight:.2f} KGS"
    data["container_number"] = container or "CAAU0000000"
    data["seal"] = seal or "00000"

    return data

def overlay_on_template(template_path, output_path, data):
    doc = fitz.open(template_path)
    page = doc[0]

    def write(text, x, y, size=10):
        page.insert_text((x, y), text, fontsize=size)

    # Overlay basic fields (adjust coordinates as needed)
    write(data["exporter"], 50, 95)
    write(data["exporter_address"], 50, 108)
    write(data["consignee"], 50, 133)
    write(data["booking"], 320, 75)
    write(data["carrier"], 50, 190)
    write(data["port_loading"], 50, 215)
    write(data["port_delivery"], 50, 230)
    write(data["vessel"], 50, 245)
    write(data["voyage"], 150, 245)
    write(data["container_number"], 320, 265)
    write(data["seal"], 420, 265)
    write(data["container_size"], 320, 280)

    # Vehicle section
    y = 305
    for vehicle in data["vehicles"]:
        write(vehicle, 50, y)
        y += 12

    write("TOTAL", 50, y + 10)
    write(data["total_weight"], 150, y + 10)

    doc.save(output_path)

if uploaded_format and uploaded_original:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as orig_tmp:
        orig_tmp.write(uploaded_original.read())
        original_path = orig_tmp.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as fmt_tmp:
        fmt_tmp.write(uploaded_format.read())
        format_path = fmt_tmp.name

    with pdfplumber.open(original_path) as pdf:
        raw_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])

    data = extract_info(raw_text)

    output_path = "final_BOL.pdf"
    overlay_on_template(format_path, output_path, data)

    with open(output_path, "rb") as f:
        st.success("✅ Bill of Lading generated successfully!")
        st.download_button("📥 Download Bill of Lading", f, file_name="Bill_of_Lading.pdf")

    os.remove(original_path)
    os.remove(format_path)
    os.remove(output_path)
