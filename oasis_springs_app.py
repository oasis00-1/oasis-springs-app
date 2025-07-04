import streamlit as st
import pandas as pd
from datetime import datetime
import os
import requests
from PIL import Image
from fpdf import FPDF
import tempfile

# ---------- PDF Receipt Class ----------
class ReceiptPDF(FPDF):
    def header(self):
        self.set_font("Arial", 'B', 16)
        try:
            self.image("logo.png", 10, 8, 25)
        except:
            pass
        self.cell(0, 10, "Oasis Springs - Order Receipt", ln=True, align="C")
        self.ln(10)

    def customer_info(self, name, phone, location, maps_link):
        self.set_font("Arial", '', 12)
        self.cell(0, 8, f"Customer: {name}", ln=True)
        self.cell(0, 8, f"Phone: {phone}", ln=True)
        self.cell(0, 8, f"Location: {location}", ln=True)
        if maps_link:
            self.cell(0, 8, f"Maps Pin: {maps_link}", ln=True)
        self.ln(5)

    def order_table(self, order, delivery_fee, total):
        self.set_font("Arial", 'B', 12)
        self.cell(80, 8, "Product", 1)
        self.cell(30, 8, "Qty", 1)
        self.cell(40, 8, "Subtotal", 1, ln=True)
        self.set_font("Arial", '', 12)
        for product, (qty, subtotal) in order.items():
            self.cell(80, 8, product, 1)
            self.cell(30, 8, str(qty), 1)
            self.cell(40, 8, f"Ksh {subtotal}", 1, ln=True)
        self.cell(110, 8, "Delivery Fee", 1)
        self.cell(40, 8, f"Ksh {delivery_fee}", 1, ln=True)
        self.cell(110, 8, "Grand Total", 1)
        self.cell(40, 8, f"Ksh {total}", 1, ln=True)
        self.ln(5)

    def payment_info(self):
        self.set_font("Arial", 'I', 11)
        self.cell(0, 10, "Paybill: 400200 | Account: 806312", ln=True)
        self.cell(0, 8, "Thank you for choosing Oasis Springs!", ln=True)

def generate_pdf(name, phone, location, maps_link, order, delivery_fee, grand_total):
    pdf = ReceiptPDF()
    pdf.add_page()
    pdf.customer_info(name, phone, location, maps_link)
    pdf.order_table(order, delivery_fee, grand_total)
    pdf.payment_info()
    tmp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
    pdf.output(tmp_path)
    return tmp_path

# ---------- Streamlit App ----------
st.set_page_config(page_title="Oasis Springs Water Order", layout="centered")
st.title("💧 Oasis Springs - Water Delivery Order")

# Safe logo load with fallback
try:
    logo = Image.open("logo.png")
    st.image(logo, width=150)
except FileNotFoundError:
    st.warning("⚠️ Logo not found. Please upload 'logo.png' to your GitHub repo.")

# Slogan
st.markdown('<h4 style="color:skyblue;"><em><strong>Every sip, a life boost</strong></em></h4>', unsafe_allow_html=True)

# Customer Info
st.header("🧍 Customer Details")
name = st.text_input("Full Name")
phone = st.text_input("Phone Number")
mpesa_number = st.text_input("M-PESA Number (format: 2547XXXXXXXX)")
location = st.selectbox("Delivery Location", ["Select", "Bamburi", "Nyali"])
maps_link = st.text_input("📍 Google Maps Pin (Optional)", placeholder="Paste Google Maps link here")
delivery_fee = 100 if location == "Bamburi" else 200 if location == "Nyali" else 0

# Product Pricing
prices = {
    "20L Bottle": 150,
    "10L Bottle": 70,
    "5L Bottle": 30,
    "1.5L Bottle": 25,
    "0.5L Bottle": 15,
}

# Product Selection
st.header("🧴 Select Products")
order = {}
total_items = 0
subtotal = 0

for product, price in prices.items():
    qty = st.number_input(f"{product} (Ksh {price})", min_value=0, step=1)
    if qty > 0:
        order[product] = (qty, price * qty)
        subtotal += price * qty
        total_items += qty

# Summary
st.markdown("---")
st.subheader("🧾 Order Summary")
for product, (qty, total) in order.items():
    st.write(f"{product}: {qty} × Ksh {prices[product]} = Ksh {total}")

if location != "Select":
    st.write(f"🚚 Delivery Fee: Ksh {delivery_fee}")

grand_total = subtotal + delivery_fee
st.subheader(f"💰 Total: Ksh {grand_total:,}")

# M-PESA fallback
st.markdown("📱 **If STK Push Fails - Pay Manually**")
st.code(f"Paybill: 400200\nAccount: 806312\nAmount: Ksh {grand_total}")

# Save orders to CSV
def save_order(data, filename="orders.csv"):
    df = pd.DataFrame([data])
    if os.path.exists(filename):
        existing = pd.read_csv(filename)
        df = pd.concat([existing, df], ignore_index=True)
    df.to_csv(filename, index=False)

# STK Push request
def send_stk_push(phone, amount):
    try:
        r = requests.post("http://localhost:5000/stk_push", json={
            "phone": phone,
            "amount": amount
        })
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# Confirm and process order
if st.button("✅ Confirm Order and Send M-PESA Prompt"):
    if not name or not phone or not mpesa_number or location == "Select" or total_items == 0:
        st.warning("Fill all required fields.")
    else:
        order_summary = "; ".join([f"{p} x{q}" for p, (q, _) in order.items()])
        save_order({
            "Name": name,
            "Phone": phone,
            "Location": location,
            "Order": order_summary,
            "Delivery Fee": delivery_fee,
            "Total": grand_total,
            "Google Maps Link": maps_link,
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        st.success(f"Order placed for {name}.")
        if maps_link:
            st.info(f"Delivery pin: {maps_link}")

        # STK Push
        response = send_stk_push(mpesa_number, grand_total)
        if "error" in response:
            st.error("STK Push failed: " + response["error"])
        elif response.get("ResponseCode") == "0":
            st.success("✅ STK Push sent! Check your phone to enter PIN.")
        else:
            st.warning("⚠️ STK Push request failed. Use manual Paybill.")
            st.json(response)

        # Generate and allow PDF download
        pdf_path = generate_pdf(name, phone, location, maps_link, order, delivery_fee, grand_total)
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📄 Download Receipt (PDF)",
                data=f,
                file_name=f"receipt_{name.replace(' ', '_')}.pdf",
                mime="application/pdf"
            )

# Footer
st.markdown("---")
st.markdown('<h3 style="color:skyblue;"><em><strong>EVERY SIP, A LIFE BOOST</strong></em></h3>', unsafe_allow_html=True)
st.markdown("📞 For inquiries call: **0710708096** or **0113436073**")
whatsapp_number = "0113436073"
whatsapp_link = f"https://wa.me/254{whatsapp_number[1:]}"
st.markdown(f"""
<a href="{whatsapp_link}" target="_blank">
    <img src="https://img.icons8.com/color/48/000000/whatsapp--v1.png" width="24"/>
    <b> Chat with us on WhatsApp</b>
</a>
""", unsafe_allow_html=True)
