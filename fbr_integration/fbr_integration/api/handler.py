import frappe
from fbr_integration.fbr_integration.api.fbr_api import send_invoice_to_fbr

@frappe.whitelist()
def send_to_fbr_si(name):
    """
    Called by client script. Returns a dict:
      { "success": True, "invoice_no": "..." }
    or
      { "success": False, "error": "..." }
    """

    try:
        # Load Sales Invoice
        doc = frappe.get_doc("Sales Invoice", name)

        # Send invoice to FBR
        send_invoice_to_fbr(doc)

        # Return success with FBR Invoice Number
        return {
            "success": True,
            "invoice_no": doc.get("fbr_invoice_no", "")
        }

    except Exception as e:
        # Log full traceback to Error Log
        frappe.log_error(
            title="fbr_integration.send_to_fbr_si",
            message=frappe.get_traceback()
        )

        return {
            "success": False,
            "error": str(e)
        }
