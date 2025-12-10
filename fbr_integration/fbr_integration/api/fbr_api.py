import frappe
import requests
import json
import urllib3

import os
import qrcode
from pathlib import Path
from frappe import _
from pyqrcode import create as qrcreate


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def safe_float(val):
    """Return float value if valid, else 0. Blank, None, negative, or invalid string returns 0."""
    try:
        num = float(val)
        return num if num >= 0 else 0
    except (TypeError, ValueError):
        return 0

def extra_tax_value(val, sale_type_str):
    """
    Logic:
    - If reduced rate sale type, return ""
    - If blank/None/zero/negative, return ""
    - Otherwise, return float value
    """
    reduced_types = ("goodsatreducedrate", "reducedrate", "rr")
    if sale_type_str in reduced_types:
        return ""
    try:
        num = float(val)
        if num <= 0:
            return ""
        return num
    except (TypeError, ValueError):
        return ""

def send_invoice_to_fbr(doc, method=None):
    try:
        settings = frappe.get_single("FBR Invoice Settings")

        if not settings.enabled:
            frappe.logger().info("FBR Integration Disabled")
            return

        # API URL and Token selection
        if settings.integration_type == "Sandbox":
            api_url = settings.sandbox_api_url
            token = settings.sandbox_security_token
        elif settings.integration_type == "Production":
            api_url = settings.production_api_url
            token = settings.production_security_token
        else:
            frappe.throw("Invalid FBR integration type. Please set to Sandbox or Production.")

        # --- Seller and Buyer Address ---
        seller_address = ""
        seller_province = ""
        if getattr(doc, "company_address", None):
            company_address_doc = frappe.get_doc("Address", doc.company_address)
            seller_address = f"{company_address_doc.address_line1}, {company_address_doc.city}"
            seller_province = company_address_doc.state

        buyer_address = ""
        buyer_province = ""
        if getattr(doc, "customer_address", None):
            customer_address_doc = frappe.get_doc("Address", doc.customer_address)
            buyer_address = f"{customer_address_doc.address_line1}, {customer_address_doc.city}"
            buyer_province = customer_address_doc.state

        # --- Build items list dynamically from doc.items ---
        items_list = []
        for item in doc.items:
            sale_type_str = str(item.fbr_sale_type or "").lower().replace(" ", "")
            extra_tax = extra_tax_value(item.fbr_extra_tax, sale_type_str)
            # --- Rate field logic ---
            if doc.fbr_scenario_id == "SN006":
                rate_val = "Exempt"
            else:
                rate_val = "{:.2f}%".format(safe_float(item.fbr_sales_tax_rate))
            items_list.append({
                "hsCode": item.fbr_hs_code,
                "productDescription": item.item_name,
                "rate": rate_val,
                "uoM": item.fbr_fbr_uom,
                "quantity": safe_float(item.qty),
                "totalValues": safe_float(item.fbr_tax_inclusive_amount),
                "valueSalesExcludingST": safe_float(item.amount),
                "fixedNotifiedValueOrRetailPrice": safe_float(item.rate),
                "salesTaxApplicable": safe_float(item.fbr_sales_tax),
                "salesTaxWithheldAtSource": 0,
                "extraTax": extra_tax,
                "furtherTax": safe_float(item.fbr_further_tax),
                "sroScheduleNo": item.fbr_sro_schedule_no,
                "fedPayable": 0,
                "discount": safe_float(item.discount_amount),
                "saleType": item.fbr_sale_type,
                "sroItemSerialNo": item.fbr_sro_item_sno
            })

        payload = {
            "invoiceType": doc.fbr_invoice_type,
            "invoiceDate": str(doc.posting_date),
            "sellerNTNCNIC": doc.company_tax_id,
            "sellerBusinessName": doc.company,
            "sellerAddress": seller_address,
            "sellerProvince": seller_province,
            "buyerNTNCNIC": doc.tax_id,
            "buyerBusinessName": doc.customer,
            "buyerAddress": buyer_address,
            "buyerProvince": buyer_province,
            "invoiceRefNo": doc.name,
            "scenarioId": doc.fbr_scenario_id,
            "buyerRegistrationType": doc.fbr_tax_payer_type,
            "items": items_list
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        frappe.logger().info(f"📤 Sending Invoice to FBR ({settings.integration_type}): {json.dumps(payload, indent=2)}")

        response = requests.post(api_url, headers=headers, json=payload, verify=False)
        response.raise_for_status()
        res_json = response.json()

        frappe.logger().info(f"✅ FBR Response: {json.dumps(res_json, indent=2)}")

        validation = res_json.get("validationResponse", {})
        if validation.get("statusCode") == "00":
            doc.fbr_integration_type = settings.integration_type
            doc.fbr_invoice_no = res_json.get("invoiceNumber", "")
            doc.fbr_submission_time = res_json.get("dated", frappe.utils.now_datetime())
            doc.fbr_invoice_status = validation.get("status", "")
            doc.fbr_invoice_status_code = validation.get("statusCode", "")
            doc.fbr_invoice_error = validation.get("error", "")
            doc.fbr_invoice_statuses = json.dumps(validation.get("invoiceStatuses", []), indent=2)
            invoice_item_nos = []
            for status in validation.get("invoiceStatuses", []):
                invoice_item_no = status.get("invoiceNo", "")
                if invoice_item_no:
                    invoice_item_nos.append(invoice_item_no)
            doc.fbr_invoice_item_no = ", ".join(invoice_item_nos)
            doc.fbr_qr_code = res_json.get("invoiceNumber", "")
            doc.fbr_digital_invoice_response = json.dumps(res_json, indent=2)
            doc.fbr_responsed = "Success"
            doc.save(ignore_permissions=True)
            generate_fbr_barcode(invoiceNumber, name)

            # --- Styled Success Message ---
            fbr_invoice_no = res_json.get("invoiceNumber", "")
            frappe.msgprint(
                msg=f"""
                    <div style="font-size:14px; line-height:1.6;">
                        <p>🟢 <b>Invoice Sent</b></p>
                        <p>🎉 <b>Congratulations!</b></p>
                        <p>
                            Your Sales Invoice <b>{doc.name}</b> has been successfully submitted 
                            to the <b>IRIS Portal – FBR</b>.
                        </p>
                        <p>
                            <b>FBR Invoice No:</b> {fbr_invoice_no}
                        </p>
                        <p style="color:green;">
                            ☑ Thank you for staying compliant and digital by G2Virtu ERP-Pakistan!
                        </p>
                    </div>
                """,
                title="Invoice Sent",
                indicator="green"
            )

        else:
            doc.fbr_responsed = "Error"
            doc.fbr_digital_invoice_response = json.dumps(res_json, indent=2)
            doc.save(ignore_permissions=True)
            frappe.throw(
                f"""
                <div style="font-size:14px; line-height:1.6; color:red;">
                    ❌ <b>FBR Error</b><br>
                    Response: {json.dumps(res_json)}
                </div>
                """
            )

    except requests.exceptions.HTTPError as e:
        doc.fbr_responsed = "HTTPError"
        doc.fbr_digital_invoice_response = str(e)
        doc.save(ignore_permissions=True)
        frappe.throw(
            f"""
            <div style="font-size:14px; line-height:1.6; color:red;">
                ❌ <b>FBR HTTP Exception</b><br>
                {str(e)}
            </div>
            """
        )
    except Exception as e:
        doc.fbr_responsed = "Exception"
        doc.fbr_digital_invoice_response = str(e)
        doc.save(ignore_permissions=True)
        frappe.throw(
            f"""
            <div style="font-size:14px; line-height:1.6; color:red;">
                ❌ <b>FBR Exception</b><br>
                {str(e)}
            </div>
            """
        )

def after_submit_invoice(doc, method=None):
    send_invoice_to_fbr(doc)

@frappe.whitelist()
def generate_fbr_barcode(code=None, docname=None):
    try:
        if not code or not docname:
            frappe.throw("Invalid QR Code data or document name.")

        name_tobe = f"{docname}.png"

        # ? Dynamically get the site directory path
        site_dir_path = frappe.utils.get_bench_path()
        current_site = frappe.local.site or frappe.get_site_path().split("/")[-1]
        site_path = os.path.join(site_dir_path, "sites", current_site)

        qrcode_dir = os.path.join(site_path, "public", "files", "qrcodes")

        # ? Ensure directory exists
        os.makedirs(qrcode_dir, mode=0o775, exist_ok=True)

        # ? Define the QR code file path
        qr_file_path = os.path.join(qrcode_dir, name_tobe)

        # ? Generate QR code only if the file doesn't exist
        if not os.path.isfile(qr_file_path):
            img = qrcode.make(code)
            img.save(qr_file_path)

        return qr_file_path  # Return the file path if needed

    except Exception as ex:
        frappe.log_error(f"Error in generate_fbr_barcode: {frappe.get_traceback()}")
        frappe.throw("Failed to generate FBR barcode. Check error logs.")
