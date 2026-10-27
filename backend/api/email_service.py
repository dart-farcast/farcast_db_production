"""
FarCast DB v2 — Centralized Email Dispatch Service
Handles secure delivery of:
1. Password Reset OTP Recovery Codes
2. Account Email Verification Codes
3. Admin Security Alerts
Supports TLS/SSL SMTP with graceful fallback, clear error logging, and HTML formatting.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Tuple

def is_smtp_configured() -> bool:
    """Returns True if SMTP host and credentials/user are configured in environment."""
    host = os.environ.get("SMTP_HOST", "").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    return bool(host and user)

def get_smtp_config():
    host = os.environ.get("SMTP_HOST", "").strip()
    port = int(os.environ.get("SMTP_PORT", 587))
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    from_email = os.environ.get("SMTP_FROM", "").strip() or user or "portal@farcastbio.com"
    return host, port, user, password, from_email

def send_email(to_email: str, subject: str, html_content: str, text_content: str = "") -> Tuple[bool, str]:
    """
    Sends an email to `to_email` using configured SMTP server.
    Returns (success: bool, message: str).
    """
    if not is_smtp_configured():
        msg = "SMTP is not configured in .env (SMTP_HOST and SMTP_USER are empty)."
        print(f"  [Email Notice] Skipped sending to {to_email}: {msg}")
        return False, msg

    host, port, user, password, from_email = get_smtp_config()

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"FarCast Bio Data Explorer <{from_email}>"
        msg["To"] = to_email

        if text_content:
            msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        print(f"  [Email Dispatch] Connecting to SMTP server {host}:{port} for {to_email}...")

        # Support port 465 (SSL) vs 587 / 25 (STARTTLS)
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            server.ehlo()
            try:
                server.starttls()
                server.ehlo()
            except Exception as e:
                print(f"  [Email Dispatch] STARTTLS not supported or failed: {e}")

        if user and password:
            server.login(user, password)

        server.sendmail(from_email, [to_email], msg.as_string())
        server.quit()
        print(f"  [Email Dispatch] Successfully sent email to {to_email}: '{subject}'")
        return True, "Email sent successfully."
    except smtplib.SMTPAuthenticationError as e:
        err = f"SMTP Authentication failed for user '{user}'. Please verify SMTP_USER and SMTP_PASSWORD: {e}"
        print(f"  [Email Error] {err}")
        return False, err
    except Exception as e:
        err = f"SMTP error while sending to {to_email}: {e}"
        print(f"  [Email Error] {err}")
        return False, err

def send_password_reset_email(to_email: str, code: str) -> Tuple[bool, str]:
    """Sends a 6-digit password reset verification OTP code via email."""
    subject = f"FarCast Bio — Password Recovery Code: {code}"
    text = (
        f"Your FarCast Data Explorer password recovery code is: {code}\n\n"
        f"This code will expire in 1 hour.\n\n"
        f"If you did not request a password reset, please contact your administrator."
    )
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; margin: 0; padding: 24px;">
      <div style="max-width: 520px; margin: 0 auto; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
        <div style="background: linear-gradient(135deg, #1E2859 0%, #2D3D82 100%); padding: 24px; text-align: center;">
          <h1 style="color: #FFFFFF; margin: 0; font-size: 20px; font-weight: 700; letter-spacing: 0.5px;">FarCast Biodynamics</h1>
          <p style="color: #93C5FD; margin: 4px 0 0 0; font-size: 12px; font-weight: 600;">PORTAL SECURITY &amp; RECOVERY</p>
        </div>
        <div style="padding: 28px 24px;">
          <h2 style="color: #0F172A; margin: 0 0 12px 0; font-size: 18px; font-weight: 700;">Password Reset Verification</h2>
          <p style="color: #475569; font-size: 14px; line-height: 1.5; margin: 0 0 20px 0;">
            A password recovery request was initiated for your FarCast account (<strong>{to_email}</strong>). Use the one-time recovery code below to choose a new password:
          </p>
          <div style="background: #FAF5FF; border: 2px dashed #C084FC; border-radius: 8px; padding: 18px; text-align: center; margin: 20px 0;">
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #7E22CE; letter-spacing: 1px; margin-bottom: 6px;">Your 6-Digit Recovery Code</div>
            <div style="font-family: 'Courier New', monospace; font-size: 34px; font-weight: 800; letter-spacing: 8px; color: #6B21A8;">{code}</div>
          </div>
          <p style="color: #64748B; font-size: 12px; line-height: 1.5; margin: 0 0 8px 0;">
            ⏱️ <strong>This code will expire in 1 hour.</strong>
          </p>
          <p style="color: #94A3B8; font-size: 12px; line-height: 1.4; margin: 0;">
            If you did not request this password reset, please ignore this email or notify your system administrator immediately.
          </p>
        </div>
        <div style="background: #F8FAFC; border-top: 1px solid #E2E8F0; padding: 14px; text-align: center; font-size: 11px; color: #94A3B8;">
          FarCast Biodynamics &bull; Data Explorer Security System
        </div>
      </div>
    </body>
    </html>
    """
    return send_email(to_email, subject, html, text)

def send_verification_email(to_email: str, code: str) -> Tuple[bool, str]:
    """Sends a 6-digit email confirmation code via email."""
    subject = f"FarCast Bio — Email Verification Code: {code}"
    text = (
        f"Your FarCast Data Explorer email verification code is: {code}\n\n"
        f"This code will expire in 24 hours."
    )
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; margin: 0; padding: 24px;">
      <div style="max-width: 520px; margin: 0 auto; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
        <div style="background: linear-gradient(135deg, #1E2859 0%, #2D3D82 100%); padding: 24px; text-align: center;">
          <h1 style="color: #FFFFFF; margin: 0; font-size: 20px; font-weight: 700; letter-spacing: 0.5px;">FarCast Biodynamics</h1>
          <p style="color: #93C5FD; margin: 4px 0 0 0; font-size: 12px; font-weight: 600;">EMAIL VERIFICATION</p>
        </div>
        <div style="padding: 28px 24px;">
          <h2 style="color: #0F172A; margin: 0 0 12px 0; font-size: 18px; font-weight: 700;">Confirm Your Account Email</h2>
          <p style="color: #475569; font-size: 14px; line-height: 1.5; margin: 0 0 20px 0;">
            Please confirm account ownership for <strong>{to_email}</strong> to complete your security profile and activate full portal access:
          </p>
          <div style="background: #F0FDF4; border: 2px dashed #86EFAC; border-radius: 8px; padding: 18px; text-align: center; margin: 20px 0;">
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #166534; letter-spacing: 1px; margin-bottom: 6px;">Your 6-Digit Verification Code</div>
            <div style="font-family: 'Courier New', monospace; font-size: 34px; font-weight: 800; letter-spacing: 8px; color: #15803D;">{code}</div>
          </div>
          <p style="color: #64748B; font-size: 12px; line-height: 1.5; margin: 0;">
            ⏱️ <strong>This code is valid for 24 hours.</strong> Enter this code on the portal or in your Account Security modal.
          </p>
        </div>
        <div style="background: #F8FAFC; border-top: 1px solid #E2E8F0; padding: 14px; text-align: center; font-size: 11px; color: #94A3B8;">
          FarCast Biodynamics &bull; Data Explorer Security System
        </div>
      </div>
    </body>
    </html>
    """
    return send_email(to_email, subject, html, text)
