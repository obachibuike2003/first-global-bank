# server.py
import os
import sqlite3, secrets, json, re
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, g, send_from_directory, abort
from flask_cors import CORS
import requests as http
from werkzeug.security import generate_password_hash, check_password_hash
import random

# ───────────────────────── email config ─────────────────────────
FROM_NAME  = "First Global Standard Bank"
# ─────────── reusable HTML email wrapper ───────────
def fmt_amount(n, currency="USD"):
    return f"{currency} {n:,.2f}"

def _data_rows(*pairs):
    """Build table-based data rows (pairs = (label, value_html) tuples)."""
    rows = ""
    for label, val in pairs:
        rows += f"""
        <tr>
          <td style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);color:#475569;font-size:0.82rem;width:46%">{label}</td>
          <td style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);color:#cbd5e1;font-size:0.82rem;font-weight:500;text-align:right">{val}</td>
        </tr>"""
    return rows

def _pill(text, color="teal"):
    styles = {
        "green":  ("rgba(34,197,94,0.12)",  "#4ade80", "rgba(34,197,94,0.25)"),
        "red":    ("rgba(239,68,68,0.1)",   "#f87171", "rgba(239,68,68,0.2)"),
        "teal":   ("rgba(14,165,183,0.12)", "#22d4e8", "rgba(14,165,183,0.25)"),
        "gold":   ("rgba(245,200,66,0.1)",  "#f5c842", "rgba(245,200,66,0.25)"),
    }
    bg, fg, bd = styles.get(color, styles["teal"])
    return (f'<span style="display:inline-block;padding:3px 12px;border-radius:999px;'
            f'font-size:0.75rem;font-weight:600;background:{bg};color:{fg};border:1px solid {bd}">{text}</span>')

def _email_shell(title, subtitle, body_html, accent_color="#0ea5b7"):
    year = datetime.utcnow().year
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<!--[if !mso]><!-->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
<!--<![endif]-->
<title>{title}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap');
  body,table,td,a{{-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%}}
  body{{margin:0;padding:0;background:#030712;font-family:'DM Sans','Segoe UI',Arial,sans-serif;-webkit-font-smoothing:antialiased}}
  img{{border:0;height:auto;line-height:100%;outline:none;text-decoration:none}}
  table{{border-collapse:collapse !important}}
  p{{margin:0 0 14px;color:#94a3b8;font-size:0.9rem;line-height:1.65}}
  @media only screen and (max-width:600px){{
    .email-wrap{{width:100% !important;margin:0 !important;border-radius:0 !important}}
    .email-body{{padding:24px 18px !important}}
    .email-header{{padding:20px 18px !important}}
  }}
</style>
</head>
<body style="margin:0;padding:0;background:#030712">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#030712;min-height:100vh">
  <tr><td align="center" style="padding:28px 12px 36px">

    <!-- ── Outer card ── -->
    <table class="email-wrap" role="presentation" cellpadding="0" cellspacing="0" border="0"
           style="max-width:580px;width:100%;border-radius:18px;overflow:hidden;border:1px solid rgba(14,165,183,0.2);box-shadow:0 0 60px rgba(14,165,183,0.08)">

      <!-- ── Announce strip ── -->
      <tr>
        <td style="background:linear-gradient(90deg,#0c1a2e,#0a1628,#0c1a2e);border-bottom:1px solid rgba(14,165,183,0.22);padding:9px 28px;text-align:center">
          <span style="display:inline-block;background:rgba(14,165,183,0.15);border:1px solid rgba(14,165,183,0.3);color:#22d4e8;padding:2px 10px;border-radius:999px;font-size:0.7rem;font-weight:600;letter-spacing:0.06em;margin-right:8px;text-transform:uppercase">SECURE</span>
          <span style="color:#475569;font-size:0.73rem;letter-spacing:0.05em;text-transform:uppercase">Official Bank Communication</span>
        </td>
      </tr>

      <!-- ── Header / brand ── -->
      <tr>
        <td class="email-header" style="background:linear-gradient(160deg,#051022 0%,#071828 100%);padding:22px 32px;border-bottom:1px solid rgba(14,165,183,0.18)">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <!-- Logo mark -->
              <td style="vertical-align:middle;width:48px">
                <div style="width:40px;height:40px;background:linear-gradient(135deg,#0ea5b7,#0c8a9a);border-radius:11px;text-align:center;line-height:40px;font-family:'Syne','Segoe UI',Arial,sans-serif;font-weight:800;font-size:1rem;color:#001018;display:inline-block">FS</div>
              </td>
              <!-- Brand name -->
              <td style="vertical-align:middle;padding-left:10px">
                <div style="font-family:'Syne','Segoe UI',Arial,sans-serif;font-size:0.72rem;font-weight:700;color:#ffffff;letter-spacing:0.07em;text-transform:uppercase;line-height:1.3">FIRST GLOBAL<br><span style="color:#22d4e8">STANDARD BANK</span></div>
              </td>
              <!-- Right badge -->
              <td style="vertical-align:middle;text-align:right">
                <span style="display:inline-block;background:rgba(14,165,183,0.12);border:1px solid rgba(14,165,183,0.28);color:#22d4e8;padding:4px 13px;border-radius:999px;font-size:0.72rem;font-weight:600;letter-spacing:0.04em">NOTIFICATION</span>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- ── Title band ── -->
      <tr>
        <td style="background:linear-gradient(180deg,#071828 0%,#080e1e 100%);padding:26px 32px 0;border-bottom:none">
          <div style="font-family:'Syne','Segoe UI',Arial,sans-serif;font-size:1.25rem;font-weight:800;color:#ffffff;letter-spacing:-0.01em;margin-bottom:5px">{title}</div>
          <div style="font-size:0.8rem;color:#475569;letter-spacing:0.01em">{subtitle}</div>
        </td>
      </tr>

      <!-- ── Body ── -->
      <tr>
        <td class="email-body" style="background:#080e1e;padding:24px 32px 32px">
          {body_html}
        </td>
      </tr>

      <!-- ── Footer ── -->
      <tr>
        <td style="background:#030712;padding:18px 32px 22px;border-top:1px solid rgba(255,255,255,0.05);text-align:center">
          <div style="font-family:'Syne','Segoe UI',Arial,sans-serif;font-size:0.68rem;font-weight:700;color:#1e3a4a;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:10px">
            FIRST GLOBAL <span style="color:#0ea5b7">STANDARD</span> BANK
          </div>
          <div style="margin-bottom:10px">
            <a href="#" style="color:#1e4a5a;text-decoration:none;font-size:0.73rem;margin:0 10px">Support</a>
            <span style="color:#1e2d3d;font-size:0.73rem">·</span>
            <a href="#" style="color:#1e4a5a;text-decoration:none;font-size:0.73rem;margin:0 10px">Privacy Policy</a>
            <span style="color:#1e2d3d;font-size:0.73rem">·</span>
            <a href="#" style="color:#1e4a5a;text-decoration:none;font-size:0.73rem;margin:0 10px">Security</a>
          </div>
          <div style="color:#1e3040;font-size:0.7rem;line-height:1.6">
            © {year} First Global Standard Bank · All rights reserved<br>
            This is an automated notification — please do not reply to this email.
          </div>
          <div style="margin-top:14px;height:3px;border-radius:999px;background:linear-gradient(90deg,transparent,rgba(14,165,183,0.3),transparent)"></div>
        </td>
      </tr>

    </table><!-- /outer card -->
  </td></tr>
</table><!-- /full-width -->
</body></html>"""


def send_welcome_email(to_email, full_name, account_no):
    body = f"""
    <p style="margin:0 0 18px;color:#94a3b8;font-size:0.9rem;line-height:1.65">
      Hi <strong style="color:#e2e8f0">{full_name}</strong>, welcome aboard!<br>
      Your account has been created and is ready to use.
    </p>

    <!-- Account details box -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:14px;margin:0 0 20px;overflow:hidden">
      <tr><td style="padding:6px 20px">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
          {_data_rows(
              ("Account Name",   f'<strong style="color:#e2e8f0">{full_name}</strong>'),
              ("Account Number", f'<code style="font-family:monospace;color:#22d4e8;font-size:0.9rem;letter-spacing:0.05em">{account_no}</code>'),
              ("Account Type",   "Personal Checking"),
              ("Status",         _pill("Active", "green")),
          )}
        </table>
      </td></tr>
    </table>

    <p style="margin:0 0 20px;color:#94a3b8;font-size:0.88rem;line-height:1.65">
      You can now log in to your dashboard to manage your account, make transfers, pay bills, and more.
    </p>

    <!-- CTA button -->
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 24px">
      <tr>
        <td style="background:linear-gradient(135deg,#0ea5b7,#0c8a9a);border-radius:12px;box-shadow:0 0 24px rgba(14,165,183,0.35)">
          <a href="#" style="display:inline-block;padding:13px 30px;color:#ffffff;text-decoration:none;font-family:'DM Sans','Segoe UI',Arial,sans-serif;font-weight:500;font-size:0.9rem;letter-spacing:0.01em">Go to Dashboard &rarr;</a>
        </td>
      </tr>
    </table>

    <!-- Security note -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:rgba(14,165,183,0.05);border:1px solid rgba(14,165,183,0.12);border-radius:11px">
      <tr><td style="padding:13px 16px">
        <span style="color:#22d4e8;font-size:0.78rem;font-weight:600;letter-spacing:0.04em;text-transform:uppercase">Security Reminder</span><br>
        <span style="color:#475569;font-size:0.8rem;line-height:1.6">Never share your password, PIN, or OTP with anyone — including bank staff. We will <strong style="color:#94a3b8">never</strong> ask for these details.</span>
      </td></tr>
    </table>
    """
    send_email(to_email, "Welcome to First Global Standard Bank", _email_shell(
        "Account Created Successfully",
        f"Issued {datetime.utcnow().strftime('%d %b %Y')} · Welcome to FRSB",
        body
    ))


def send_debit_alert(to_email, full_name, amount, currency, tx_type, counterparty, balance, ref_id):
    body = f"""
    <p style="margin:0 0 6px;color:#94a3b8;font-size:0.9rem">
      Hi <strong style="color:#e2e8f0">{full_name}</strong>, a debit has been processed on your account.
    </p>

    <!-- Amount hero -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:linear-gradient(135deg,rgba(248,113,113,0.08),rgba(239,68,68,0.04));border:1px solid rgba(239,68,68,0.18);border-radius:14px;margin:20px 0;text-align:center">
      <tr><td style="padding:22px 20px">
        <div style="font-size:0.7rem;color:#64748b;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px">Amount Debited</div>
        <div style="font-family:'Syne','Segoe UI',Arial,sans-serif;font-size:2.1rem;font-weight:800;color:#f87171;letter-spacing:-0.02em">&#8722;&nbsp;{fmt_amount(amount, currency)}</div>
        <div style="margin-top:10px">{_pill("Approved", "green")}</div>
      </td></tr>
    </table>

    <!-- Transaction details -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:14px;margin:0 0 20px;overflow:hidden">
      <tr><td style="padding:6px 20px">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
          {_data_rows(
              ("Transaction Type",    tx_type),
              ("Beneficiary / Details", counterparty),
              ("Amount Debited",      f'<span style="color:#f87171">{fmt_amount(amount, currency)}</span>'),
              ("Available Balance",   f'<strong style="color:#e2e8f0">{fmt_amount(balance, currency)}</strong>'),
              ("Reference",           f'<code style="font-family:monospace;color:#22d4e8;font-size:0.82rem">TXN-{ref_id:06d}</code>'),
              ("Date &amp; Time",     datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')),
          )}
        </table>
      </td></tr>
    </table>

    <!-- Security note -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:rgba(239,68,68,0.05);border:1px solid rgba(239,68,68,0.15);border-radius:11px">
      <tr><td style="padding:12px 16px">
        <span style="color:#f87171;font-size:0.78rem;font-weight:600;letter-spacing:0.04em;text-transform:uppercase">Not You?</span><br>
        <span style="color:#475569;font-size:0.8rem;line-height:1.6">If you did not authorise this transaction, contact support immediately via the app or call our helpline.</span>
      </td></tr>
    </table>
    """
    send_email(
        to_email,
        f"Debit Alert: {fmt_amount(amount, currency)} — First Global Standard Bank",
        _email_shell("Debit Transaction Alert", f"Ref TXN-{ref_id:06d} · {datetime.utcnow().strftime('%d %b %Y, %H:%M')} UTC", body)
    )


def send_credit_alert(to_email, full_name, amount, currency, tx_type, from_info, balance, ref_id):
    body = f"""
    <p style="margin:0 0 6px;color:#94a3b8;font-size:0.9rem">
      Hi <strong style="color:#e2e8f0">{full_name}</strong>, your account has been credited.
    </p>

    <!-- Amount hero -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:linear-gradient(135deg,rgba(74,222,128,0.08),rgba(34,197,94,0.04));border:1px solid rgba(74,222,128,0.18);border-radius:14px;margin:20px 0;text-align:center">
      <tr><td style="padding:22px 20px">
        <div style="font-size:0.7rem;color:#64748b;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px">Amount Credited</div>
        <div style="font-family:'Syne','Segoe UI',Arial,sans-serif;font-size:2.1rem;font-weight:800;color:#4ade80;letter-spacing:-0.02em">&#43;&nbsp;{fmt_amount(amount, currency)}</div>
        <div style="margin-top:10px">{_pill("Approved", "green")}</div>
      </td></tr>
    </table>

    <!-- Transaction details -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:14px;margin:0 0 20px;overflow:hidden">
      <tr><td style="padding:6px 20px">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
          {_data_rows(
              ("Transaction Type",   tx_type),
              ("From / Details",     from_info),
              ("Amount Credited",    f'<span style="color:#4ade80">{fmt_amount(amount, currency)}</span>'),
              ("Available Balance",  f'<strong style="color:#e2e8f0">{fmt_amount(balance, currency)}</strong>'),
              ("Reference",          f'<code style="font-family:monospace;color:#22d4e8;font-size:0.82rem">TXN-{ref_id:06d}</code>'),
              ("Date &amp; Time",    datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')),
          )}
        </table>
      </td></tr>
    </table>

    <!-- CTA -->
    <table role="presentation" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="background:linear-gradient(135deg,#0ea5b7,#0c8a9a);border-radius:12px;box-shadow:0 0 24px rgba(14,165,183,0.3)">
          <a href="#" style="display:inline-block;padding:12px 28px;color:#ffffff;text-decoration:none;font-family:'DM Sans','Segoe UI',Arial,sans-serif;font-weight:500;font-size:0.88rem">View Dashboard &rarr;</a>
        </td>
      </tr>
    </table>
    """
    send_email(
        to_email,
        f"Credit Alert: {fmt_amount(amount, currency)} — First Global Standard Bank",
        _email_shell("Credit Transaction Alert", f"Ref TXN-{ref_id:06d} · {datetime.utcnow().strftime('%d %b %Y, %H:%M')} UTC", body)
    )


def send_loan_status_email(to_email, full_name, principal, currency, status, loan_id):
    approved = status == "Approved"
    accent   = "#4ade80" if approved else "#f87171"
    bg_grad  = "rgba(74,222,128,0.08),rgba(34,197,94,0.04)" if approved else "rgba(248,113,113,0.08),rgba(239,68,68,0.04)"
    bd_color = "rgba(74,222,128,0.18)" if approved else "rgba(239,68,68,0.18)"
    icon     = "&#10003;" if approved else "&#10007;"
    pill_color = "green" if approved else "red"
    status_msg = (
        "Congratulations! Your loan application has been <strong style='color:#4ade80'>approved</strong>. "
        "The funds will be disbursed to your account shortly."
        if approved else
        "Your loan application has been <strong style='color:#f87171'>declined</strong> after review. "
        "Please contact our support team if you have any questions."
    )
    body = f"""
    <p style="margin:0 0 6px;color:#94a3b8;font-size:0.9rem">
      Hi <strong style="color:#e2e8f0">{full_name}</strong>,
    </p>
    <p style="margin:0 0 20px;color:#94a3b8;font-size:0.9rem;line-height:1.65">{status_msg}</p>

    <!-- Status hero -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:linear-gradient(135deg,{bg_grad});border:1px solid {bd_color};border-radius:14px;margin:0 0 20px;text-align:center">
      <tr><td style="padding:22px 20px">
        <div style="font-family:'Syne','Segoe UI',Arial,sans-serif;font-size:2.4rem;font-weight:800;color:{accent}">{icon}</div>
        <div style="font-family:'Syne','Segoe UI',Arial,sans-serif;font-size:1.1rem;font-weight:700;color:{accent};margin:4px 0">Loan {status}</div>
        <div style="font-size:0.78rem;color:#475569">Reference: LOAN-{loan_id:05d}</div>
      </td></tr>
    </table>

    <!-- Loan details -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:14px;margin:0 0 20px;overflow:hidden">
      <tr><td style="padding:6px 20px">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
          {_data_rows(
              ("Loan Reference",   f'<code style="font-family:monospace;color:#22d4e8;font-size:0.82rem">LOAN-{loan_id:05d}</code>'),
              ("Principal Amount", f'<strong style="color:#e2e8f0">{fmt_amount(principal, currency)}</strong>'),
              ("Decision",         _pill(status, pill_color)),
              ("Date",             datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')),
          )}
        </table>
      </td></tr>
    </table>

    <!-- CTA -->
    <table role="presentation" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="background:linear-gradient(135deg,#0ea5b7,#0c8a9a);border-radius:12px;box-shadow:0 0 24px rgba(14,165,183,0.3)">
          <a href="#" style="display:inline-block;padding:12px 28px;color:#ffffff;text-decoration:none;font-family:'DM Sans','Segoe UI',Arial,sans-serif;font-weight:500;font-size:0.88rem">View Loan Details &rarr;</a>
        </td>
      </tr>
    </table>
    """
    subject = f"Loan Application {'Approved' if approved else 'Update'} — First Global Standard Bank"
    send_email(to_email, subject, _email_shell(
        f"Loan Application {status}",
        f"LOAN-{loan_id:05d} · {datetime.utcnow().strftime('%d %b %Y')}",
        body
    ))


def send_bill_email(to_email, full_name, amount, currency, bill_type, details, balance, ref_id):
    body = f"""
    <p style="margin:0 0 6px;color:#94a3b8;font-size:0.9rem">
      Hi <strong style="color:#e2e8f0">{full_name}</strong>, your bill payment was processed successfully.
    </p>

    <!-- Amount hero -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:linear-gradient(135deg,rgba(245,200,66,0.07),rgba(245,200,66,0.03));border:1px solid rgba(245,200,66,0.18);border-radius:14px;margin:20px 0;text-align:center">
      <tr><td style="padding:22px 20px">
        <div style="font-size:0.7rem;color:#64748b;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px">{bill_type} Payment</div>
        <div style="font-family:'Syne','Segoe UI',Arial,sans-serif;font-size:2.1rem;font-weight:800;color:#f5c842;letter-spacing:-0.02em">&#8722;&nbsp;{fmt_amount(amount, currency)}</div>
        <div style="margin-top:10px">{_pill("Successful", "green")}</div>
      </td></tr>
    </table>

    <!-- Bill details -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:14px;margin:0 0 20px;overflow:hidden">
      <tr><td style="padding:6px 20px">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
          {_data_rows(
              ("Service",           bill_type),
              ("Details",           details),
              ("Amount Paid",       f'<span style="color:#f5c842">{fmt_amount(amount, currency)}</span>'),
              ("Remaining Balance", f'<strong style="color:#e2e8f0">{fmt_amount(balance, currency)}</strong>'),
              ("Reference",         f'<code style="font-family:monospace;color:#22d4e8;font-size:0.82rem">BILL-{ref_id:06d}</code>'),
              ("Date &amp; Time",   datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')),
          )}
        </table>
      </td></tr>
    </table>

    <!-- Security note -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:rgba(239,68,68,0.05);border:1px solid rgba(239,68,68,0.15);border-radius:11px">
      <tr><td style="padding:12px 16px">
        <span style="color:#f87171;font-size:0.78rem;font-weight:600;letter-spacing:0.04em;text-transform:uppercase">Not You?</span><br>
        <span style="color:#475569;font-size:0.8rem;line-height:1.6">If you did not authorise this payment, contact support immediately via the app.</span>
      </td></tr>
    </table>
    """
    send_email(
        to_email,
        f"Bill Payment Successful: {bill_type} — First Global Standard Bank",
        _email_shell("Bill Payment Confirmation", f"Ref BILL-{ref_id:06d} · {datetime.utcnow().strftime('%d %b %Y, %H:%M')} UTC", body)
    )

def send_pending_transfer_email(to_email, full_name, amount, currency, counterparty_info, ref_id):
    body = f"""
    <p style="margin:0 0 6px;color:#94a3b8;font-size:0.9rem">
      Hi <strong style="color:#e2e8f0">{full_name}</strong>, your transfer request has been received and is pending review.
    </p>

    <!-- Amount hero -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:linear-gradient(135deg,rgba(245,200,66,0.08),rgba(245,200,66,0.03));border:1px solid rgba(245,200,66,0.2);border-radius:14px;margin:20px 0;text-align:center">
      <tr><td style="padding:22px 20px">
        <div style="font-size:0.7rem;color:#64748b;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px">Transfer Amount</div>
        <div style="font-family:'Syne','Segoe UI',Arial,sans-serif;font-size:2.1rem;font-weight:800;color:#f5c842;letter-spacing:-0.02em">{fmt_amount(amount, currency)}</div>
        <div style="margin-top:10px">{_pill("Pending Review", "gold")}</div>
      </td></tr>
    </table>

    <!-- Details -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:14px;margin:0 0 20px;overflow:hidden">
      <tr><td style="padding:6px 20px">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
          {_data_rows(
              ("Recipient / Details", counterparty_info),
              ("Amount",              f'<span style="color:#f5c842">{fmt_amount(amount, currency)}</span>'),
              ("Status",              _pill("Pending Admin Review", "gold")),
              ("Reference",           f'<code style="font-family:monospace;color:#22d4e8;font-size:0.82rem">TXN-{ref_id:06d}</code>'),
              ("Submitted",           datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')),
          )}
        </table>
      </td></tr>
    </table>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:rgba(14,165,183,0.05);border:1px solid rgba(14,165,183,0.12);border-radius:11px">
      <tr><td style="padding:13px 16px">
        <span style="color:#22d4e8;font-size:0.78rem;font-weight:600;letter-spacing:0.04em;text-transform:uppercase">What Happens Next</span><br>
        <span style="color:#475569;font-size:0.8rem;line-height:1.6">Your transfer is now queued for compliance review. You will receive a debit alert once it is approved and processed, or a notification if it cannot be completed.</span>
      </td></tr>
    </table>
    """
    send_email(
        to_email,
        f"Transfer Pending Review: {fmt_amount(amount, currency)} — First Global Standard Bank",
        _email_shell("Transfer Submitted — Pending Review",
                     f"Ref TXN-{ref_id:06d} · {datetime.utcnow().strftime('%d %b %Y, %H:%M')} UTC", body, accent_color="#f5c842")
    )


def send_password_reset_email(to_email, full_name, reset_url):
    body = f"""
    <p style="margin:0 0 18px;color:#94a3b8;font-size:0.9rem;line-height:1.65">
      Hi <strong style="color:#e2e8f0">{full_name}</strong>,<br>
      We received a request to reset your password. Click the button below to set a new one.
      This link expires in <strong style="color:#e2e8f0">1 hour</strong>.
    </p>

    <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 24px">
      <tr>
        <td style="background:linear-gradient(135deg,#0ea5b7,#0c8a9a);border-radius:12px;box-shadow:0 0 24px rgba(14,165,183,0.35)">
          <a href="{reset_url}" style="display:inline-block;padding:13px 30px;color:#ffffff;text-decoration:none;font-family:'DM Sans','Segoe UI',Arial,sans-serif;font-weight:500;font-size:0.9rem;letter-spacing:0.01em">Reset Password &rarr;</a>
        </td>
      </tr>
    </table>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:rgba(239,68,68,0.05);border:1px solid rgba(239,68,68,0.15);border-radius:11px;margin-bottom:20px">
      <tr><td style="padding:13px 16px">
        <span style="color:#f87171;font-size:0.78rem;font-weight:600;letter-spacing:0.04em;text-transform:uppercase">Didn't Request This?</span><br>
        <span style="color:#475569;font-size:0.8rem;line-height:1.6">If you did not request a password reset, ignore this email — your password will remain unchanged.</span>
      </td></tr>
    </table>

    <p style="color:#475569;font-size:0.78rem;line-height:1.6">
      Or copy and paste this link into your browser:<br>
      <span style="color:#22d4e8;word-break:break-all;font-size:0.75rem">{reset_url}</span>
    </p>
    """
    send_email(to_email, "Reset Your Password — First Global Standard Bank", _email_shell(
        "Password Reset Request",
        f"Requested {datetime.utcnow().strftime('%d %b %Y, %H:%M')} UTC · Expires in 1 hour",
        body
    ))


def send_card_status_email(to_email, full_name, status, card_req_id, card_type="Virtual"):
    approved = status == "Approved"
    accent   = "#4ade80" if approved else "#f87171"
    bg_grad  = "rgba(74,222,128,0.08),rgba(34,197,94,0.04)" if approved else "rgba(248,113,113,0.08),rgba(239,68,68,0.04)"
    bd_color = "rgba(74,222,128,0.18)" if approved else "rgba(239,68,68,0.18)"
    icon     = "&#10003;" if approved else "&#10007;"
    pill_color = "green" if approved else "red"
    status_msg = (
        f"Your {card_type} card request has been <strong style='color:#4ade80'>approved</strong>. "
        "Your card is now active and ready for use."
        if approved else
        f"Your {card_type} card request has been <strong style='color:#f87171'>declined</strong> after review. "
        "Please contact support if you have questions."
    )
    body = f"""
    <p style="margin:0 0 6px;color:#94a3b8;font-size:0.9rem">
      Hi <strong style="color:#e2e8f0">{full_name}</strong>,
    </p>
    <p style="margin:0 0 20px;color:#94a3b8;font-size:0.9rem;line-height:1.65">{status_msg}</p>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:linear-gradient(135deg,{bg_grad});border:1px solid {bd_color};border-radius:14px;margin:0 0 20px;text-align:center">
      <tr><td style="padding:22px 20px">
        <div style="font-family:'Syne','Segoe UI',Arial,sans-serif;font-size:2.4rem;font-weight:800;color:{accent}">{icon}</div>
        <div style="font-family:'Syne','Segoe UI',Arial,sans-serif;font-size:1.1rem;font-weight:700;color:{accent};margin:4px 0">Card {status}</div>
        <div style="font-size:0.78rem;color:#475569">Reference: CARD-{card_req_id:05d}</div>
      </td></tr>
    </table>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:14px;margin:0 0 20px;overflow:hidden">
      <tr><td style="padding:6px 20px">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
          {_data_rows(
              ("Card Reference", f'<code style="font-family:monospace;color:#22d4e8;font-size:0.82rem">CARD-{card_req_id:05d}</code>'),
              ("Card Type",      card_type),
              ("Decision",       _pill(status, pill_color)),
              ("Date",           datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')),
          )}
        </table>
      </td></tr>
    </table>
    <table role="presentation" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td style="background:linear-gradient(135deg,#0ea5b7,#0c8a9a);border-radius:12px;box-shadow:0 0 24px rgba(14,165,183,0.3)">
          <a href="#" style="display:inline-block;padding:12px 28px;color:#ffffff;text-decoration:none;font-family:'DM Sans','Segoe UI',Arial,sans-serif;font-weight:500;font-size:0.88rem">View Cards &rarr;</a>
        </td>
      </tr>
    </table>
    """
    subject = f"Card Request {'Approved' if approved else 'Update'} — First Global Standard Bank"
    send_email(to_email, subject, _email_shell(
        f"Card Request {status}",
        f"CARD-{card_req_id:05d} · {datetime.utcnow().strftime('%d %b %Y')}",
        body
    ))


def current_user_id():
    u = current_user()
    return u["id"] if u else None


DB_PATH   = "bank.db"
ADMIN_KEY = "CHANGE_ME_ADMIN"

app = Flask(__name__, static_url_path='', static_folder='.')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
BREVO_API_KEY    = os.environ.get("BREVO_API_KEY", "")
MAIL_FROM_EMAIL  = os.environ.get("MAIL_FROM", "firstglobalstandardbank@gmail.com")
CORS(app, supports_credentials=True)

def send_email(to_addr, subject, html_body):
    try:
        resp = http.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": BREVO_API_KEY, "Content-Type": "application/json"},
            json={
                "sender": {"name": FROM_NAME, "email": MAIL_FROM_EMAIL},
                "to": [{"email": to_addr}],
                "subject": subject,
                "htmlContent": html_body,
            },
            timeout=10,
        )
        if resp.status_code in (200, 201):
            print(f"[email] sent OK to {to_addr}")
        else:
            print(f"[email] Brevo error {resp.status_code}: {resp.text}")
    except Exception as exc:
        print(f"[email] FAILED to {to_addr}: {exc}")

# ───────────────────────── DB helpers ─────────────────────────
_DB_ABS = os.path.abspath(os.path.join(os.path.dirname(__file__), "bank.db"))

def db():
    if "db" not in g:
        g.db = sqlite3.connect(_DB_ABS, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_conn(_exc):
    if (conn := g.pop("db", None)) is not None:
        conn.close()

def q(sql, args=(), commit=False):
    cur = db().execute(sql, args)
    if commit:
        db().commit()
    return cur

def row(r): return {k: r[k] for k in r.keys()}

# ───────────────────────── bootstrap ─────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    phone         TEXT,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user',
    handle        TEXT,
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS accounts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    account_no TEXT NOT NULL UNIQUE,
    currency   TEXT NOT NULL DEFAULT 'USD',
    balance    REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    token      TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS transactions (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id              INTEGER NOT NULL REFERENCES users(id),
    type                 TEXT NOT NULL,
    direction            TEXT NOT NULL,
    counterparty_user_id INTEGER,
    counterparty_info    TEXT,
    amount               REAL NOT NULL,
    currency             TEXT NOT NULL DEFAULT 'USD',
    note                 TEXT,
    status               TEXT NOT NULL DEFAULT 'Pending',
    requested_at         TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cards (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    spend_limit REAL NOT NULL DEFAULT 5000,
    online      INTEGER NOT NULL DEFAULT 1,
    frozen      INTEGER NOT NULL DEFAULT 0,
    last4       TEXT
);
CREATE TABLE IF NOT EXISTS loans (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id),
    principal      REAL NOT NULL,
    rate           REAL NOT NULL DEFAULT 0,
    tenure_months  INTEGER NOT NULL,
    note           TEXT,
    status         TEXT NOT NULL DEFAULT 'Pending',
    created_at     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS beneficiaries (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    name       TEXT NOT NULL,
    dest       TEXT NOT NULL,
    type       TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS support (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    subject    TEXT NOT NULL,
    message    TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'Open',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS card_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    card_type       TEXT NOT NULL DEFAULT 'Virtual',
    passport_ref    TEXT NOT NULL,
    payment_ref     TEXT NOT NULL,
    fee_amount      REAL NOT NULL DEFAULT 25.0,
    status          TEXT NOT NULL DEFAULT 'Pending',
    admin_note      TEXT,
    created_at      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS password_resets (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    token      TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used       INTEGER NOT NULL DEFAULT 0
);
"""

def bootstrap():
    db_abs = _DB_ABS
    print(f"[db] bootstrap: {db_abs}")
    try:
        conn = sqlite3.connect(db_abs, check_same_thread=False)
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
            if os.path.exists("schema.sql"):
                with open("schema.sql", "r", encoding="utf-8") as f:
                    conn.executescript(f.read())
                conn.commit()
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            print(f"[db] tables: {tables}")
        finally:
            conn.close()
    except Exception as exc:
        print(f"[db] bootstrap FAILED: {exc}")
        raise

# Call it safely at import time
bootstrap()


# ───────────────────────── static pages ─────────────────────────
@app.get("/")
def serve_index():
    return app.send_static_file("index.html")

@app.get("/get-account.html")
def get_account_redirect():
    from flask import redirect
    return redirect("/Signup.html", code=301)

@app.get("/<path:page>")
def serve_static_page(page):
    if page.startswith("api/"):
        abort(404)
    if os.path.exists(page):
        return send_from_directory('.', page)
    return app.send_static_file("index.html")


# ───────────────────────── auth utils ─────────────────────────
def new_token():
    return secrets.token_hex(24)

def current_user():
    """Return (user_row|None). Client sends X-Auth-Token."""
    tok = request.headers.get("X-Auth-Token") or ""
    if not tok: return None
    r = q("""select u.* from sessions s join users u on u.id=s.user_id
             where s.token=? and s.expires_at > ?""", (tok, datetime.utcnow().isoformat())).fetchone()
    return r

def require_auth():
    u = current_user()
    if not u:
        return None, (jsonify({"error": "Unauthorized"}), 401)
    return u, None

def is_admin(u):
    return (u and u["role"] == "admin") or (request.headers.get("X-Admin-Key") == ADMIN_KEY)

# ───────────────────────── public/auth ─────────────────────────
@app.post("/api/auth/register")
def register():
    b = request.get_json(force=True)
    full_name = (b.get("full_name") or "").strip()
    email     = (b.get("email") or "").strip().lower()
    phone     = (b.get("phone") or "").strip()
    pwd       = b.get("password") or ""
    if not (full_name and email and pwd):
        return jsonify({"error":"Missing fields"}), 400
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"error":"Invalid email"}), 400
    if q("select 1 from users where email=?", (email,)).fetchone():
        return jsonify({"error":"Email already used"}), 409

    try:
        pwd_hash = generate_password_hash(pwd)
        q("insert into users(full_name,email,phone,password_hash,role,created_at) values(?,?,?,?,?,?)",
          (full_name, email, phone, pwd_hash, "user", datetime.utcnow().isoformat()), commit=True)
        uid = q("select last_insert_rowid() id").fetchone()["id"]

        acct_no = "22" + str(uid).zfill(8)
        q("""insert into accounts(user_id,account_no,currency,balance,created_at)
             values(?,?,?,?,?)""", (uid, acct_no, "USD", 0, datetime.utcnow().isoformat()), commit=True)

        token = new_token()
        q("""insert into sessions(user_id, token, created_at, expires_at)
             values(?,?,?,?)""", (uid, token, datetime.utcnow().isoformat(),
                                  (datetime.utcnow()+timedelta(days=14)).isoformat()), commit=True)
    except Exception as exc:
        print(f"[register] DB error: {exc}")
        return jsonify({"error": "Registration failed. Please try again."}), 500

    send_welcome_email(email, full_name, acct_no)
    return jsonify({"ok": True, "token": token, "user_id": uid, "account_no": acct_no})

@app.post("/api/auth/login")
def login():
    b = request.get_json(force=True)
    email = (b.get("email") or "").strip().lower()
    pwd   = b.get("password") or ""
    u = q("select * from users where email=?", (email,)).fetchone()
    if not u or not check_password_hash(u["password_hash"], pwd):
        return jsonify({"error":"Invalid credentials"}), 401
    token = new_token()
    q("""insert into sessions(user_id, token, created_at, expires_at)
         values(?,?,?,?)""", (u["id"], token, datetime.utcnow().isoformat(),
                              (datetime.utcnow()+timedelta(days=14)).isoformat()), commit=True)
    acct = q("select account_no,currency,balance from accounts where user_id=?", (u["id"],)).fetchone()
    return jsonify({"ok": True, "token": token, "user":{
        "id":u["id"], "full_name":u["full_name"], "email":u["email"], "role":u["role"]
    }, "account": row(acct)})

@app.get("/api/me")
def me():
    u, err = require_auth()
    if err: return err
    acct = q("select * from accounts where user_id=?", (u["id"],)).fetchone()
    has_active_card  = bool(q("select 1 from cards where user_id=?", (u["id"],)).fetchone())
    has_pending_card = bool(q("select 1 from card_requests where user_id=? and status='Pending'", (u["id"],)).fetchone())
    return jsonify({"user": row(u), "account": row(acct),
                    "has_active_card": has_active_card, "has_pending_card": has_pending_card})

# ───────────────────────── user endpoints ─────────────────────────
@app.route("/api/transactions")
def list_transactions():
    uid = current_user_id()
    if not uid:
        return jsonify({"error": "Unauthorized"}), 401
    limit = int(request.args.get("limit", 50))

    rows = q("""
        SELECT
            requested_at AS date,
            -- Build a friendly description
            CASE
              WHEN type='Transfer' AND direction='OUT' THEN COALESCE(counterparty_info, 'Transfer Out')
              WHEN type='Transfer' AND direction='IN'  THEN COALESCE(counterparty_info, 'Transfer In')
              WHEN type='Bill' THEN COALESCE(counterparty_info, 'Bill Payment')
              ELSE COALESCE(type, 'Txn')
            END AS description,
            -- Use type as a simple category for the UI
            type AS category,
            -- Make OUT negative for UI charts/tables
            CASE WHEN direction='OUT' THEN -ABS(amount) ELSE ABS(amount) END AS amount,
            status
        FROM transactions
        WHERE user_id=?
        ORDER BY requested_at DESC
        LIMIT ?
    """, [uid, limit]).fetchall()

    return jsonify([dict(r) for r in rows])


@app.route("/api/summary")
def summary():
    uid = current_user_id()
    if not uid:
        return jsonify({"error":"Unauthorized"}), 401

    # Signed amounts so OUT is negative, IN is positive
    rbal = q("""
        SELECT COALESCE(SUM(
            CASE WHEN direction='OUT' THEN -ABS(amount) ELSE ABS(amount) END
        ), 0) AS s
        FROM transactions
        WHERE user_id=?
    """, [uid]).fetchone()
    bal = rbal["s"]

    rows = q("""
        SELECT
          CASE WHEN direction='OUT' THEN -ABS(amount) ELSE ABS(amount) END AS signed_amount,
          requested_at
        FROM transactions
        WHERE user_id=? AND requested_at >= datetime('now','-7 day')
    """, [uid]).fetchall()

    income7d  = sum(r["signed_amount"] for r in rows if r["signed_amount"] > 0)
    expenses7d = sum(-r["signed_amount"] for r in rows if r["signed_amount"] < 0)
    delta = income7d - expenses7d

    return jsonify({"balance": bal, "income7d": income7d, "expenses7d": expenses7d, "delta": delta})


@app.post("/api/auth/forgot-password")
def forgot_password():
    b = request.get_json(force=True)
    email = (b.get("email") or "").strip().lower()
    user = q("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if user:
        # Invalidate any existing unused tokens for this user
        q("UPDATE password_resets SET used=1 WHERE user_id=? AND used=0", (user["id"],), commit=True)
        token = secrets.token_hex(32)
        q("""INSERT INTO password_resets(user_id, token, created_at, expires_at, used)
             VALUES(?,?,?,?,?)""",
          (user["id"], token, datetime.utcnow().isoformat(),
           (datetime.utcnow()+timedelta(hours=1)).isoformat(), 0), commit=True)
        base = request.host_url.rstrip("/")
        reset_url = f"{base}/reset-password.html?token={token}"
        send_password_reset_email(email, user["full_name"], reset_url)
    # Always return ok to avoid revealing whether email exists
    return jsonify({"ok": True})

@app.post("/api/auth/reset-password")
def reset_password_endpoint():
    b = request.get_json(force=True)
    token = (b.get("token") or "").strip()
    new_pwd = b.get("password") or ""
    if not token or len(new_pwd) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    reset = q("""SELECT * FROM password_resets
                 WHERE token=? AND used=0 AND expires_at > ?""",
              (token, datetime.utcnow().isoformat())).fetchone()
    if not reset:
        return jsonify({"error": "This reset link is invalid or has expired"}), 400
    pwd_hash = generate_password_hash(new_pwd)
    q("UPDATE users SET password_hash=? WHERE id=?", (pwd_hash, reset["user_id"]), commit=True)
    q("UPDATE password_resets SET used=1 WHERE id=?", (reset["id"],), commit=True)
    # Invalidate all sessions so old password can't be reused
    q("DELETE FROM sessions WHERE user_id=?", (reset["user_id"],), commit=True)
    return jsonify({"ok": True})

@app.post("/api/transfers")
def create_transfer():
    u, err = require_auth()
    if err: return err
    b = request.get_json(force=True)
    typ = b.get("type", "intra")  # 'intra' (Trivexa→Trivexa) or 'bank'
    amount = int(b.get("amount", 0))
    note   = (b.get("note") or "").strip()
    dest   = (b.get("dest") or "").strip()      # @user or account number
    bank   = (b.get("bank") or "").strip()      # if type=='bank'
    if amount <= 0 or not dest:
        return jsonify({"error":"Invalid transfer"}), 400

    # Intra-user: resolve counterparty
    counterparty_user_id = None
    counterparty_info    = ""
    if typ == "intra" and dest.startswith("@"):
        cp = q("select id, full_name from users where handle=?", (dest[1:],)).fetchone()
        if not cp: return jsonify({"error":"Recipient not found"}), 404
        counterparty_user_id = cp["id"]
        counterparty_info = f"To {dest}"
    elif typ == "bank":
        counterparty_info = f"Bank:{bank} • {dest}"
    else:
        counterparty_info = dest

    # Create pending transaction (admin must approve)
    q("""insert into transactions(user_id, type, direction, counterparty_user_id, counterparty_info,
          amount, currency, note, status, requested_at)
          values(?,?,?,?,?,?,?,?,?,?)""",
      (u["id"], "Transfer", "OUT", counterparty_user_id, counterparty_info,
       amount, "USD", note, "Pending", datetime.utcnow().isoformat()), commit=True)
    tx_id = q("select last_insert_rowid() id").fetchone()["id"]
    send_pending_transfer_email(u["email"], u["full_name"], amount, "USD",
                                counterparty_info or dest, tx_id)
    return jsonify({"ok": True, "status": "Pending", "ref_id": tx_id})

@app.post("/api/withdrawals")
def create_withdrawal():
    u, err = require_auth()
    if err: return err
    b = request.get_json(force=True)
    amount  = int(b.get("amount", 0))
    method  = (b.get("method") or "").strip()   # e.g. "Bank Transfer", "Crypto"
    details = (b.get("details") or "").strip()  # account number / wallet address
    if amount <= 0 or not method or not details:
        return jsonify({"error": "Amount, method and account details are required"}), 400
    counterparty_info = f"{method} • {details}"
    q("""insert into transactions(user_id, type, direction, counterparty_user_id, counterparty_info,
          amount, currency, note, status, requested_at)
          values(?,?,?,?,?,?,?,?,?,?)""",
      (u["id"], "Withdrawal", "OUT", None, counterparty_info,
       amount, "USD", "", "Pending", datetime.utcnow().isoformat()), commit=True)
    return jsonify({"ok": True, "status": "Pending"})

@app.post("/api/bills")
def create_bill():
    u, err = require_auth()
    if err: return err
    b = request.get_json(force=True)
    bill_type = b.get("type","Utility")
    account   = b.get("account","")
    amount    = int(b.get("amount",0))
    if amount <= 0:
        return jsonify({"error":"Invalid amount"}), 400
    details = f"{bill_type} • {account}"
    q("""insert into transactions(user_id, type, direction, counterparty_info,
          amount, currency, note, status, requested_at)
          values(?,?,?,?,?,?,?,?,?)""",
      (u["id"], "Bill", "OUT", details, amount, "USD", bill_type, "Pending", datetime.utcnow().isoformat()),
      commit=True)
    return jsonify({"ok": True, "status":"Pending"})

@app.post("/api/cards/request")
def request_card():
    u, err = require_auth()
    if err: return err
    b = request.get_json(force=True)
    card_type   = (b.get("card_type") or "Virtual").strip()
    passport_ref = (b.get("passport_ref") or "").strip()
    payment_ref  = (b.get("payment_ref") or "").strip()
    fee_amount   = float(b.get("fee_amount", 25.0))
    if not passport_ref:
        return jsonify({"error": "Passport / ID reference is required"}), 400
    if not payment_ref:
        return jsonify({"error": "Payment reference is required"}), 400
    q("""insert into card_requests(user_id,card_type,passport_ref,payment_ref,fee_amount,status,created_at)
         values(?,?,?,?,?,?,?)""",
      (u["id"], card_type, passport_ref, payment_ref, fee_amount, "Pending",
       datetime.utcnow().isoformat()), commit=True)
    req_id = q("select last_insert_rowid() id").fetchone()["id"]
    return jsonify({"ok": True, "status": "Pending", "req_id": req_id})


@app.get("/api/cards/requests")
def list_card_requests():
    u, err = require_auth()
    if err: return err
    rows = q("select * from card_requests where user_id=? order by id desc", (u["id"],)).fetchall()
    return jsonify([row(r) for r in rows])


@app.route("/api/cards")
def get_card():
    uid = current_user_id()
    if not uid:
        return jsonify({"error":"Unauthorized"}), 401
    card = q("SELECT * FROM cards WHERE user_id=?", [uid]).fetchone()
    if not card:
        return jsonify({"limit": 50000, "online": True, "frozen": False, "activity": []})
    return jsonify({
        "limit": card["spend_limit"],
        "online": bool(card["online"]),
        "frozen": bool(card["frozen"]),
        "last4": card["last4"],
        "activity": []
    })

@app.route("/api/cards/settings", methods=["POST"])
def update_card_settings():
    uid = current_user_id()
    if not uid:
        return jsonify({"error":"Unauthorized"}), 401
    data = request.get_json(force=True)
    q("UPDATE cards SET spend_limit=?, online=? WHERE user_id=?", [int(data["limit"]), bool(data["online"]), uid], commit=True)
    return jsonify({"message": "Settings updated."})

@app.route("/api/cards/freeze", methods=["POST"])
def freeze_card_v2():
    uid = current_user_id()
    if not uid:
        return jsonify({"error":"Unauthorized"}), 401
    card = q("SELECT frozen FROM cards WHERE user_id=?", [uid]).fetchone()
    new_state = (not card["frozen"]) if card else True
    if card:
        q("UPDATE cards SET frozen=? WHERE user_id=?", [int(new_state), uid], commit=True)
    else:
        # if no card row yet, create one
        q("INSERT INTO cards (user_id, spend_limit, online, frozen, last4) VALUES (?,?,?,?,?)",
          [uid, 50000, True, new_state, random.randint(1000,9999)], commit=True)
    return jsonify({"frozen": new_state, "message": "Card frozen." if new_state else "Card unfrozen."})

@app.route("/api/cards/create", methods=["POST"])
def create_virtual_card():
    uid = current_user_id()
    if not uid:
        return jsonify({"error":"Unauthorized"}), 401
    last4 = random.randint(1000, 9999)
    q("INSERT INTO cards (user_id, spend_limit, online, frozen, last4) VALUES (?,?,?,?,?)",
      [uid, 50000, True, False, last4], commit=True)
    return jsonify({"message": "Virtual card created.", "last4": last4})


@app.get("/api/beneficiaries")
def get_bens():
    u, err = require_auth()
    if err: return err
    rows = q("select * from beneficiaries where user_id=? order by id desc", (u["id"],)).fetchall()
    return jsonify([row(r) for r in rows])

# GET /api/transactions?limit=50
# returns: [{date, description, category, amount, status}, ...]


# (Optional but recommended) GET /api/summary
# returns: {balance, income7d, expenses7d, delta}


@app.post("/api/beneficiaries")
def add_ben():
    u, err = require_auth()
    if err: return err
    b = request.get_json(force=True)
    name = (b.get("name") or "").strip()
    dest = (b.get("dest") or "").strip()
    typ  = b.get("type","bank")
    if not (name and dest): return jsonify({"error":"Missing"}), 400
    q("insert into beneficiaries(user_id,name,dest,type,created_at) values(?,?,?,?,?)",
      (u["id"], name, dest, typ, datetime.utcnow().isoformat()), commit=True)
    return jsonify({"ok": True})

@app.post("/api/support")
def support_msg():
    u, err = require_auth()
    if err: return err
    b = request.get_json(force=True)
    subject = (b.get("subject") or "").strip()
    message = (b.get("message") or "").strip()
    q("insert into support(user_id,subject,message,status,created_at) values(?,?,?,?,?)",
      (u["id"], subject, message, "Open", datetime.utcnow().isoformat()), commit=True)
    return jsonify({"ok": True})

@app.get("/api/branches")
def branches():
    rows = q("select * from branches order by city").fetchall()
    return jsonify([row(r) for r in rows])

# ───────────────────────── admin endpoints ─────────────────────────
def require_admin_guard():
    u = current_user()
    if is_admin(u):
        return u, None
    return None, (jsonify({"error":"Unauthorized"}), 401)

def find_user_by_query(query):
    query = (query or "").strip()
    if not query:
        return None
    if query.isdigit():
        return q("select * from users where id=?", (int(query),)).fetchone()
    if "@" in query:
        return q("select * from users where lower(email)=?", (query.lower(),)).fetchone()
    qlow = query.lower()
    return q("""
        select * from users where lower(email)=? or lower(full_name)=?
        or lower(email) like ? or lower(full_name) like ? limit 1
    """, (qlow, qlow, f"%{qlow}%", f"%{qlow}%")).fetchone()

@app.get("/api/admin/queue")
def admin_queue():
    u, err = require_admin_guard()
    if err: return err
    rows = q("""
        select t.*, u.full_name as user_name, u.email as user_email
        from transactions t
        left join users u on u.id=t.user_id
        order by t.id desc
    """).fetchall()
    return jsonify([row(r) for r in rows])

@app.post("/api/admin/transactions/<int:tid>/<action>")
def admin_decide(tid, action):
    u, err = require_admin_guard()
    if err: return err
    if action not in ("approve","decline"):
        return jsonify({"error":"Invalid action"}), 400
    tx = q("select * from transactions where id=?", (tid,)).fetchone()
    if not tx: return jsonify({"error":"Not found"}), 404
    new_status = "Approved" if action=="approve" else "Declined"
    q("update transactions set status=? where id=?", (new_status, tid), commit=True)

    # On approval: move money for OUT flows; credit IN if intra
    if new_status == "Approved" and tx["direction"] == "OUT":
        acct = q("select * from accounts where user_id=?", (tx["user_id"],)).fetchone()
        if not acct:
            return jsonify({"error":"Account not found"}), 404
        if acct["balance"] < tx["amount"]:
            q("update transactions set status='Declined' where id=?", (tid,), commit=True)
            return jsonify({"error":"Insufficient balance"}), 400
        q("update accounts set balance=balance-? where id=?", (tx["amount"], acct["id"]), commit=True)
        new_sender_balance = acct["balance"] - tx["amount"]

        sender_info = q("select full_name, email from users where id=?", (tx["user_id"],)).fetchone()
        if sender_info:
            send_debit_alert(
                sender_info["email"], sender_info["full_name"],
                tx["amount"], tx["currency"], tx["type"],
                tx["counterparty_info"] or "", new_sender_balance, tid
            )

        if tx["type"] == "Transfer" and tx["counterparty_user_id"]:
            cp_acct = q("select id from accounts where user_id=?", (tx["counterparty_user_id"],)).fetchone()
            if cp_acct:
                q("update accounts set balance=balance+? where id=?", (tx["amount"], cp_acct["id"]), commit=True)
                q("""insert into transactions(user_id,type,direction,counterparty_user_id,counterparty_info,
                      amount,currency,note,status,requested_at)
                      values(?,?,?,?,?,?,?,?,?,?)""",
                  (tx["counterparty_user_id"], "Transfer", "IN", tx["user_id"],
                   f"From user {tx['user_id']}", tx["amount"], tx["currency"],
                   tx["note"], "Approved", datetime.utcnow().isoformat()), commit=True)
                cp_info = q("select full_name, email from users where id=?", (tx["counterparty_user_id"],)).fetchone()
                cp_new_bal = q("select balance from accounts where id=?", (cp_acct["id"],)).fetchone()
                if cp_info and cp_new_bal:
                    from_name = sender_info["full_name"] if sender_info else f"User {tx['user_id']}"
                    send_credit_alert(
                        cp_info["email"], cp_info["full_name"],
                        tx["amount"], tx["currency"], "Intra-Bank Transfer",
                        from_name, cp_new_bal["balance"], tid
                    )

    return jsonify({"ok": True, "status": new_status})

@app.get("/api/admin/users")
def admin_users():
    u, err = require_admin_guard()
    if err: return err
    query = (request.args.get("query") or "").strip()
    if query:
        user = find_user_by_query(query)
        if not user:
            return jsonify({"error": "User not found"}), 404
        acct = q("select * from accounts where user_id=?", (user["id"],)).fetchone()
        return jsonify({"user": row(user), "account": row(acct) if acct else None})
    rows = q("""select u.id as user_id, u.full_name, u.email, u.phone, u.role, u.created_at,
                     a.account_no, a.currency, a.balance
              from users u
              left join accounts a on u.id=a.user_id
              order by u.created_at desc limit 200""").fetchall()
    return jsonify([row(r) for r in rows])

@app.post("/api/admin/users/<int:uid>/balance")
def admin_users_balance(uid):
    u, err = require_admin_guard()
    if err: return err
    b = request.get_json(force=True)
    amount = float(b.get("amount", 0))
    note = (b.get("note") or "Admin adjustment").strip()
    if amount <= 0:
        return jsonify({"error": "Amount must be greater than zero"}), 400
    acct = q("select * from accounts where user_id=?", (uid,)).fetchone()
    if not acct:
        return jsonify({"error": "Account not found"}), 404
    q("update accounts set balance=balance+? where id=?", (amount, acct["id"]), commit=True)
    q("""insert into transactions(user_id,type,direction,counterparty_info,amount,currency,note,status,requested_at)
          values(?,?,?,?,?,?,?,?,?)""",
      (uid, "Admin Credit", "IN", "Admin adjustment", abs(amount), acct["currency"], note, "Approved", datetime.utcnow().isoformat()), commit=True)
    tx_id = q("select last_insert_rowid() id").fetchone()["id"]
    target_user = q("select full_name, email from users where id=?", (uid,)).fetchone()
    if target_user:
        send_credit_alert(
            target_user["email"], target_user["full_name"],
            amount, acct["currency"], "Admin Credit",
            "Bank Administration", acct["balance"] + amount, tx_id
        )
    return jsonify({"ok": True, "balance": acct["balance"] + amount})

@app.delete("/api/admin/users/<int:uid>")
def admin_users_delete(uid):
    u, err = require_admin_guard()
    if err: return err
    q("delete from sessions where user_id=?", (uid,), commit=True)
    q("delete from transactions where user_id=?", (uid,), commit=True)
    q("delete from beneficiaries where user_id=?", (uid,), commit=True)
    q("delete from cards where user_id=?", (uid,), commit=True)
    q("delete from loans where user_id=?", (uid,), commit=True)
    q("delete from support where user_id=?", (uid,), commit=True)
    q("delete from accounts where user_id=?", (uid,), commit=True)
    q("delete from users where id=?", (uid,), commit=True)
    return jsonify({"ok": True})

@app.post("/api/admin/bills")
def admin_create_bill():
    u, err = require_admin_guard()
    if err: return err
    b = request.get_json(force=True)
    user_query = (b.get("user") or "").strip()
    bill_type = b.get("type", "Utility")
    acct_ref = (b.get("account") or "").strip()
    amount = float(b.get("amount", 0))
    if amount <= 0 or not user_query:
        return jsonify({"error": "Invalid request"}), 400
    user = find_user_by_query(user_query)
    if not user:
        return jsonify({"error": "User not found"}), 404
    acct = q("select * from accounts where user_id=?", (user["id"],)).fetchone()
    if not acct:
        return jsonify({"error": "Account not found"}), 404
    details = f"{bill_type} • {acct_ref}"
    q("insert into transactions(user_id, type, direction, counterparty_info, amount, currency, note, status, requested_at) values(?,?,?,?,?,?,?,?,?)",
      (user["id"], "Bill", "OUT", details, amount, acct["currency"], bill_type, "Approved", datetime.utcnow().isoformat()), commit=True)
    tx_id = q("select last_insert_rowid() id").fetchone()["id"]
    q("update accounts set balance=balance-? where id=?", (amount, acct["id"]), commit=True)
    new_balance = acct["balance"] - amount
    send_bill_email(user["email"], user["full_name"], amount, acct["currency"], bill_type, details, new_balance, tx_id)
    return jsonify({"ok": True, "balance": new_balance})

@app.get("/api/admin/interest")
def admin_get_interest():
    u, err = require_admin_guard()
    if err: return err
    r = q("select value from settings where key='interest'").fetchone()
    return jsonify(json.loads(r["value"]) if r else {})

@app.post("/api/admin/interest")
def admin_set_interest():
    u, err = require_admin_guard()
    if err: return err
    b = request.get_json(force=True)
    policy = {
        "base": float(b.get("base", 0)),
        "bonus": float(b.get("bonus", 0)),
        "topup": bool(b.get("topup", False)),
        "effective_from": b.get("effective_from")
    }
    q("insert or replace into settings(key,value) values('interest',?)", (json.dumps(policy),), commit=True)
    return jsonify({"ok": True, "policy": policy})

@app.get("/api/admin/loans")
def admin_loans():
    u, err = require_admin_guard()
    if err: return err
    rows = q("select * from loans order by id desc").fetchall()
    return jsonify([row(r) for r in rows])

@app.post("/api/admin/loans")
def admin_create_loan():
    u, err = require_admin_guard()
    if err: return err
    b = request.get_json(force=True)
    q("""insert into loans(user_id, principal, rate, tenure_months, note, status, created_at) values(?,?,?,?,?,?,?)""",
      (int(b["user_id"]), int(b["principal"]), float(b["rate"]), int(b["tenure_months"]), b.get("note",""), "Pending", datetime.utcnow().isoformat()), commit=True)
    lid = q("select last_insert_rowid() id").fetchone()["id"]
    return jsonify({"ok": True, "id": lid})

@app.post("/api/admin/loans/<int:lid>/<action>")
def admin_loan_action(lid, action):
    u, err = require_admin_guard()
    if err: return err
    if action not in ("approve","decline"):
        return jsonify({"error": "Invalid action"}), 400
    new_status = "Approved" if action == "approve" else "Declined"
    q("update loans set status=? where id=?", (new_status, lid), commit=True)
    loan = q("select * from loans where id=?", (lid,)).fetchone()
    if loan:
        lu = q("select full_name, email from users where id=?", (loan["user_id"],)).fetchone()
        if lu:
            send_loan_status_email(lu["email"], lu["full_name"], loan["principal"], "USD", new_status, lid)
    return jsonify({"ok": True})


@app.get("/api/admin/support")
def admin_support():
    u, err = require_admin_guard()
    if err: return err
    rows = q("select * from support order by id desc").fetchall()
    return jsonify([row(r) for r in rows])

@app.get("/api/admin/card-requests")
def admin_card_requests():
    u, err = require_admin_guard()
    if err: return err
    rows = q("""
        select cr.*, u.full_name as user_name, u.email as user_email
        from card_requests cr
        left join users u on u.id = cr.user_id
        order by cr.id desc
    """).fetchall()
    return jsonify([row(r) for r in rows])

@app.post("/api/admin/card-requests/<int:req_id>/<action>")
def admin_card_decision(req_id, action):
    u, err = require_admin_guard()
    if err: return err
    if action not in ("approve", "decline"):
        return jsonify({"error": "Invalid action"}), 400
    cr = q("select * from card_requests where id=?", (req_id,)).fetchone()
    if not cr:
        return jsonify({"error": "Not found"}), 404
    new_status = "Approved" if action == "approve" else "Declined"
    admin_note = (request.get_json(force=True) or {}).get("note", "")
    q("update card_requests set status=?, admin_note=? where id=?",
      (new_status, admin_note, req_id), commit=True)
    if new_status == "Approved":
        last4 = random.randint(1000, 9999)
        q("INSERT INTO cards (user_id, spend_limit, online, frozen, last4) VALUES (?,?,?,?,?)",
          [cr["user_id"], 50000, True, False, last4], commit=True)
    target = q("select full_name, email from users where id=?", (cr["user_id"],)).fetchone()
    if target:
        send_card_status_email(target["email"], target["full_name"], new_status, req_id, cr["card_type"])
    return jsonify({"ok": True, "status": new_status})

@app.get("/api/support")
def get_support():
    u, err = require_auth()
    if err: return err
    rows = q("select * from support where user_id=? order by id desc", (u["id"],)).fetchall()
    return jsonify([row(r) for r in rows])

@app.get("/api/loans")
def get_loans():
    u, err = require_auth()
    if err: return err
    rows = q("select * from loans where user_id=? order by id desc", (u["id"],)).fetchall()
    return jsonify([row(r) for r in rows])

@app.post("/api/loans")
def create_loan_application():
    u, err = require_auth()
    if err: return err
    b = request.get_json(force=True)
    principal = int(b.get("principal", 0))
    rate = float(b.get("rate", 0))
    tenure_months = int(b.get("tenure_months", 0))
    note = (b.get("note") or "").strip()
    if principal <= 0 or tenure_months <= 0:
        return jsonify({"error": "Invalid loan parameters"}), 400
    q("""insert into loans(user_id, principal, rate, tenure_months, note, status, created_at) values(?,?,?,?,?,?,?)""",
      (u["id"], principal, rate, tenure_months, note, "Pending", datetime.utcnow().isoformat()), commit=True)
    lid = q("select last_insert_rowid() id").fetchone()["id"]
    return jsonify({"ok": True, "id": lid, "status": "Pending"})




# ─────────────── payment settings (public read / admin write) ───────────────
_DEFAULT_PAYMENT = {
    "usdt": {"network": "TRC-20 (Tron)", "address": ""},
    "btc":  {"network": "Bitcoin",        "address": ""},
    "tron": {"network": "TRC-20",         "address": ""},
    "eth":  {"network": "ERC-20 (Ethereum)", "address": ""}
}

@app.get("/api/settings/payment")
def get_payment_settings():
    r = q("select value from settings where key='payment'").fetchone()
    return jsonify(json.loads(r["value"]) if r else _DEFAULT_PAYMENT)

@app.post("/api/admin/settings/payment")
def set_payment_settings():
    _, err = require_admin_guard()
    if err: return err
    b = request.get_json(force=True)
    q("insert or replace into settings(key,value) values('payment',?)",
      (json.dumps(b),), commit=True)
    return jsonify({"ok": True})

# ───────────────────────── misc ─────────────────────────
@app.get("/api/health")
def health():
    return {"status":"ok"}
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
