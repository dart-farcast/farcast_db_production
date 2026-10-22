"""
FarCast DB — Resilient Email Notification System
Sends clean HTML emails for weekly sync digests or critical crash alerts.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import logging

from config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, NOTIFICATION_EMAILS
)
from logger import SyncMetrics

def is_smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_PORT and NOTIFICATION_EMAILS)


def send_sync_email(metrics: SyncMetrics, log_path: str = "", logger: logging.Logger = None) -> bool:
    """Send formatted HTML email based on sync result."""
    log = logger or logging.getLogger("FarcastSync")
    
    if not is_smtp_configured():
        log.warning(
            "[Email Notification Skipped] SMTP settings (SMTP_HOST, SMTP_PORT, etc.) "
            "are not configured in .env. Skipping email dispatch."
        )
        return False

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if metrics.success:
        subject = f"✅ [Farcast DB] Office Server Sync Digest — {now_str}"
        html_body = _build_success_html(metrics, now_str)
    else:
        subject = f"🚨 [Farcast DB ALERT] Office Server Sync FAILED — {now_str}"
        html_body = _build_failure_html(metrics, now_str, log_path)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM or SMTP_USER
    msg["To"] = ", ".join(NOTIFICATION_EMAILS)

    msg.attach(MIMEText(html_body, "html"))

    try:
        log.info(f"Connecting to SMTP server {SMTP_HOST}:{SMTP_PORT}...")
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
        server.ehlo()
        try:
            server.starttls()
            server.ehlo()
        except Exception:
            pass

        if SMTP_USER and SMTP_PASSWORD:
            server.login(SMTP_USER, SMTP_PASSWORD)

        server.sendmail(msg["From"], NOTIFICATION_EMAILS, msg.as_string())
        server.quit()
        log.info(f"Successfully dispatched sync notification email to: {NOTIFICATION_EMAILS}")
        return True
    except Exception as e:
        log.error(f"Failed to send sync notification email: {e}")
        return False


def _build_success_html(m: SyncMetrics, timestamp: str) -> str:
    unmatched_html = ""
    if m.overlay_unmatched_arms:
        items = "".join([f"<li><code>{arm}</code></li>" for arm in m.overlay_unmatched_arms[:10]])
        unmatched_html = f"""
        <div style="background-color: #fffbeb; border-left: 4px solid #f59e0b; padding: 12px 16px; margin-top: 20px; border-radius: 4px;">
            <strong style="color: #b45309;">⚠️ Unmatched Arm Codes in Nomenclature ({len(m.overlay_unmatched_arms)}):</strong>
            <ul style="color: #92400e; margin: 8px 0 0 16px; padding: 0;">{items}</ul>
        </div>
        """

    warnings_html = ""
    if m.warnings:
        warn_items = "".join([f"<li>{w}</li>" for w in m.warnings[:10]])
        warnings_html = f"""
        <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 12px 16px; margin-top: 15px; border-radius: 4px;">
            <strong style="color: #991b1b;">ℹ️ System Warnings ({len(m.warnings)}):</strong>
            <ul style="color: #b91c1c; margin: 8px 0 0 16px; padding: 0;">{warn_items}</ul>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; padding: 24px; color: #1e293b;">
        <div style="max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 10px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
            <div style="background: linear-gradient(135deg, #0ea5e9, #0284c7); padding: 24px; color: #ffffff;">
                <h2 style="margin: 0; font-size: 22px;">FarCast DB — Data Synchronization Report</h2>
                <p style="margin: 6px 0 0 0; opacity: 0.9; font-size: 14px;">Executed on {timestamp} &bull; Duration: {m.duration_seconds:.1f}s</p>
            </div>
            
            <div style="padding: 24px;">
                <div style="display: inline-block; background-color: #dcfce7; color: #15803d; font-weight: 600; font-size: 13px; padding: 4px 12px; border-radius: 9999px; margin-bottom: 20px;">
                    ✓ SYNC COMPLETED SUCCESSFULLY
                </div>

                <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px;">
                    <thead>
                        <tr style="border-bottom: 2px solid #e2e8f0; text-align: left;">
                            <th style="padding: 8px 4px; color: #64748b;">DATASET / COMPONENT</th>
                            <th style="padding: 8px 4px; color: #64748b; text-align: right;">PROCESSED</th>
                            <th style="padding: 8px 4px; color: #64748b; text-align: right;">STATUS</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style="border-bottom: 1px solid #f1f5f9;">
                            <td style="padding: 12px 4px;"><strong>Clinical Metadata</strong></td>
                            <td style="padding: 12px 4px; text-align: right;">{m.meta_upserted} records</td>
                            <td style="padding: 12px 4px; text-align: right; color: #16a34a;">Upserted</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #f1f5f9;">
                            <td style="padding: 12px 4px;"><strong>Cytokine Assays</strong></td>
                            <td style="padding: 12px 4px; text-align: right;">{m.cyto_rows_inserted} rows ({m.cyto_unique_samples} samples)</td>
                            <td style="padding: 12px 4px; text-align: right; color: #16a34a;">Ingested</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #f1f5f9;">
                            <td style="padding: 12px 4px;"><strong>Histopathology Assays</strong></td>
                            <td style="padding: 12px 4px; text-align: right;">{m.histo_rows_inserted} rows ({m.histo_unique_samples} samples)</td>
                            <td style="padding: 12px 4px; text-align: right; color: #16a34a;">Ingested</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #f1f5f9;">
                            <td style="padding: 12px 4px;"><strong>Treatment & Arm Overlay</strong></td>
                            <td style="padding: 12px 4px; text-align: right;">{m.overlay_total_rows} mappings ({m.overlay_samples_covered} samples)</td>
                            <td style="padding: 12px 4px; text-align: right; color: #16a34a;">Resolved</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px 4px;"><strong>Portal In-Memory Cache</strong></td>
                            <td style="padding: 12px 4px; text-align: right;">{'Refreshed' if m.railway_cache_refreshed or m.local_cache_refreshed else 'Unchanged'}</td>
                            <td style="padding: 12px 4px; text-align: right; color: #16a34a;">Live 24/7</td>
                        </tr>
                    </tbody>
                </table>

                {unmatched_html}
                {warnings_html}

                <div style="margin-top: 28px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center;">
                    FarCast DB Automated Synchronization Engine &bull; Office Server Pipeline
                </div>
            </div>
        </div>
    </body>
    </html>
    """


def _build_failure_html(m: SyncMetrics, timestamp: str, log_path: str) -> str:
    err_text = m.critical_error or ("\n".join(m.errors) if m.errors else "Unknown pipeline error")
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; padding: 24px; color: #1e293b;">
        <div style="max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 10px; border: 1px solid #fecaca; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
            <div style="background: linear-gradient(135deg, #ef4444, #b91c1c); padding: 24px; color: #ffffff;">
                <h2 style="margin: 0; font-size: 22px;">🚨 FarCast DB — Sync Pipeline Alert</h2>
                <p style="margin: 6px 0 0 0; opacity: 0.9; font-size: 14px;">Failure detected at {timestamp}</p>
            </div>
            
            <div style="padding: 24px;">
                <div style="background-color: #fef2f2; border: 1px solid #fee2e2; border-radius: 6px; padding: 16px; margin-bottom: 20px;">
                    <h3 style="margin: 0 0 8px 0; color: #991b1b; font-size: 16px;">Pipeline Execution Failed</h3>
                    <p style="margin: 0; color: #7f1d1d; font-size: 14px;">The automated office server sync encountered an unhandled exception or network fault.</p>
                </div>

                <div style="font-size: 14px; font-weight: 600; margin-bottom: 6px; color: #334155;">Error Details:</div>
                <pre style="background: #0f172a; color: #f87171; padding: 16px; border-radius: 6px; font-size: 12px; overflow-x: auto; white-space: pre-wrap; font-family: monospace;">{err_text}</pre>

                <p style="font-size: 13px; color: #64748b; margin-top: 16px;">
                    Log file location on server: <code>{log_path}</code>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
