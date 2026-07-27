import smtplib
from email.message import EmailMessage
from playwright.sync_api import sync_playwright
import time
import os

# --- CONFIGURATION ---
BASE_DASHBOARD_URL = "https://yocket-bos.streamlit.app/" 
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASS = os.environ.get("SENDER_PASS")

# 🚨 THE DISTRIBUTION MATRIX 🚨
# Add all 10-12 of your lenders and their respective target emails here
LENDER_MATRIX = {
    "Credila": "credila_team@example.com",
    "Avanse": "avanse_team@example.com",
    # "Auxilo": "auxilo_team@example.com",
}

def capture_and_send(bank_name, target_email):
    print(f"🤖 Booting Extraction for {bank_name}...")
    
    # 1. Build the target URL using query parameters
    # Note: We replace spaces with %20 for URL encoding if bank names have spaces
    url_encoded_bank = bank_name.replace(" ", "%20")
    target_url = f"{BASE_DASHBOARD_URL}?bank={url_encoded_bank}"
    
    pdf_path = f"Fall26_Audit_{bank_name.replace(' ', '_')}.pdf"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Set a standard desktop viewport wide enough for your columns
        page = browser.new_page(viewport={"width": 1600, "height": 900})
        
        print(f"🌐 Loading {bank_name} Dashboard...")
        page.goto(target_url, wait_until="networkidle")
        
        print("⏳ Waiting 12 seconds for AI and Data to fully render...")
        time.sleep(12) 
        
        # 2. INJECT CSS TO HIDE STREAMLIT JUNK & WHITE-LABEL IT
        page.add_style_tag(content="""
            /* Hide top header, sidebar toggle, and GitHub deploy buttons */
            header[data-testid="stHeader"] {display: none !important;}
            /* Collapse sidebar completely for the PDF */
            section[data-testid="stSidebar"] {display: none !important;}
            /* Hide the 'Manage App' bottom right button */
            .stApp > div:last-child {display: none !important;}
        """)
        
        # 3. GET EXACT HEIGHT FOR A CONTINUOUS PDF
        # Scroll to bottom to ensure any lazy-loaded elements pop in
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
        
        scroll_height = page.evaluate("document.documentElement.scrollHeight")
        
        print(f"📸 Capturing continuous {scroll_height}px PDF...")
        # width is set wide enough for your UI, height is dynamic to never cut off
        page.pdf(
            path=pdf_path, 
            width="1600px", 
            height=f"{scroll_height + 100}px", 
            print_background=True,
            page_ranges="1" # Forces it all onto a single page
        )
        browser.close()

    # --- FIRE THE EMAIL ---
    print(f"📧 Firing email payload to {target_email}...")
    msg = EmailMessage()
    msg['Subject'] = f"Fall '26 Cohort: {bank_name} Pipeline Telemetry"
    msg['From'] = SENDER_EMAIL
    msg['To'] = target_email
    
    body = f"""Hi {bank_name} Team,

Please find attached the latest performance exports for our Fall '26 cohort pipeline, isolated specifically for {bank_name} files. 

We recently upgraded our internal telemetry to give us total visibility into lead velocity, branch-level execution, and competitor threats. Rather than just looking at a high-level summary, our new dashboard breaks down the exact operational friction at every stage of the borrower's journey:

• Macro Operations (Overall Health)
• Deep-Dive 1: BP to Login
• Deep-Dive 2: Login to Sanction
• Deep-Dive 3: Sanction to PF Paid

Let me know what your calendar looks like next week for a quick walkthrough.

Best,
The Operations Team
"""
    msg.set_content(body)
    
    with open(pdf_path, 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=pdf_path)
        
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(SENDER_EMAIL, SENDER_PASS)
        smtp.send_message(msg)
        
    print(f"✅ {bank_name} dispatch complete.")
    
    # Cleanup local file so the server stays clean
    os.remove(pdf_path)

if __name__ == "__main__":
    print("🚀 INITIATING MASS DISTRIBUTION SEQUENCE...")
    for bank, email in LENDER_MATRIX.items():
        try:
            capture_and_send(bank, email)
        except Exception as e:
            print(f"❌ FAILED to send {bank}. Error: {str(e)}")
            
    print("🏁 ALL DISTRIBUTIONS COMPLETE.")
