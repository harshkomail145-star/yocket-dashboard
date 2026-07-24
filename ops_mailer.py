import smtplib
from email.message import EmailMessage
from playwright.sync_api import sync_playwright
import time
import os

# --- CONFIGURATION ---
DASHBOARD_URL = "https://your-yocket-dashboard-url.streamlit.app/" # Replace with your live URL
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASS = os.environ.get("SENDER_PASS") # Use a Gmail App Password
RECEIVER_EMAIL = "partner@lender.com"

def generate_pdf():
    print("🤖 Booting Headless Ops Engine...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("🌐 Loading Dashboard...")
        page.goto(DASHBOARD_URL, wait_until="networkidle")
        
        # Wait 10 seconds to ensure the live G-Sheet data and AI finish generating
        print("⏳ Waiting for AI and Live Data to render...")
        time.sleep(10)
        
        # Capture the PDF
        print("📸 Capturing Pipeline PDF...")
        pdf_path = "Fall_26_Pipeline_Audit.pdf"
        page.pdf(path=pdf_path, format="A4", print_background=True)
        
        browser.close()
        return pdf_path

def send_executive_email(pdf_path):
    print("📧 Drafting Executive Email...")
    
    msg = EmailMessage()
    msg['Subject'] = "Fall '26 Cohort: Pipeline Telemetry & Performance Audit"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    
    # The exact pitch we drafted
    body = """Hi Partner,

Please find attached the latest performance exports for our Fall '26 cohort pipeline. 

We recently upgraded our internal telemetry to give us total visibility into lead velocity, branch-level execution, and competitor threats. Rather than just looking at a high-level summary, our new dashboard breaks down the exact operational friction at every stage of the borrower's journey:

• Macro Operations (Overall Health)
• Deep-Dive 1: BP to Login
• Deep-Dive 2: Login to Sanction
• Deep-Dive 3: Sanction to PF Paid

Phase 2: Integrated AI Operations Layer (In Development)
To ensure we act on this data instantly, we are currently integrating an advanced generative AI layer. Once fully calibrated, this AI engine will dynamically audit the raw data, cross-reference branch performance, and act as an automated Chief of Staff.

Let me know what your calendar looks like next week for a quick walkthrough.

Best,
The Operations Team
"""
    msg.set_content(body)
    
    # Attach the PDF
    with open(pdf_path, 'rb') as f:
        pdf_data = f.read()
        msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=pdf_path)
        
    print("🚀 Firing Email payload...")
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(SENDER_EMAIL, SENDER_PASS)
        smtp.send_message(msg)
        
    print("✅ Zero-Click Pipeline Execution Complete.")

if __name__ == "__main__":
    pdf_file = generate_pdf()
    send_executive_email(pdf_file)
