// Client Script
// Name : FBR Tax Calculation Clear
// Doctype : Sales invoice
//Apply To : Form
//Module : Selling
// Enable : Yes
// Purpose
//Extend ERPNext item-level tax handling beyond the built-in tax table.
//Allow custom tax breakdowns per line item (e.g., GST, Further Tax, Extra Tax, etc.).
//Automatically recalculate when quantity, rate, or template changes.
//Store results in custom fields for reporting, FBR integration, or invoice printi
//---------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------


frappe.ui.form.on("Sales Invoice", {
    refresh: function(frm) {
        // show only for submitted invoices (docstatus = 1)
        if (frm.doc.docstatus !== 1) {
            return;
        }

        // add button (Frappe clears previous buttons on refresh, so safe to call each time)
        let btn = frm.add_custom_button(__("Send to FBR"), function() {
            if (frm.doc.fbr_invoice_no) {
                // Already sent -> show the informational dialog
                frappe.msgprint({
                    title: __("Already Submitted"),
                    indicator: "red",
                    message: `
                        <div style="font-size:14px; line-height:1.6;">
                            <p>🚫 <b>Invoice already sent to Iris-FBR Portal</b></p>
                            <p>Please watch your FBR Invoice No.: <b>${frm.doc.fbr_invoice_no}</b></p>
                            <p style="color:green;">
                                For further clarity please contact G2Virtu ERP Pakistan at +923394284788
                            </p>
                        </div>
                    `
                });
                return;
            }

            // Not sent yet -> call server method
            frappe.call({
                method: "fbr_integration.fbr_integration.api.handler.send_to_fbr_si",
                args: { name: frm.doc.name },
                freeze: true,
                callback: function(r) {
                    if (!r || !r.message) {
                        frappe.msgprint({ title: __("Error"), indicator: "red", message: __("No response from server") });
                        return;
                    }

                    var resp = r.message;
                    if (resp.success === false) {
                        // server reported error
                        frappe.msgprint({
                            title: __("FBR Error"),
                            indicator: "red",
                            message: `
                                <div style="font-size:14px; line-height:1.6;">
                                    <p>❌ <b>Error sending invoice to FBR</b></p>
                                    <pre>${resp.error}</pre>
                                </div>
                            `
                        });
                    } else {
                        // success
                        frappe.msgprint({
                            title: __("Invoice Sent"),
                            indicator: "green",
                            message: `
                                <div style="font-size:14px; line-height:1.6;">
                                    <p>🟢 <b>Invoice Sent</b></p>
                                    <p>🎉 <b>Congratulations!</b></p>
                                    <p>
                                        Your Sales Invoice <b>${frm.doc.name}</b> has been successfully submitted 
                                        to the <b>IRIS Portal – FBR</b>.
                                    </p>
                                    <p><b>FBR Invoice No:</b> ${resp.invoice_no}</p>
                                    <p style="color:green;">☑ Thank you for staying compliant and digital by G2Virtu ERP-Pakistan!</p>
                                </div>
                            `
                        });

                        // reload to fetch fields set by server (fbr_invoice_no etc.)
                        frm.reload_doc();
                    }
                }
            });

        });

        // make button red
        btn.removeClass("btn-default").addClass("btn-danger");
    }
});

frappe.ui.form.on('Sales Invoice Item', {
    qty: calculate_tax_fields,
    rate: calculate_tax_fields,
    item_tax_template: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        let qty = parseFloat(row.qty) || 0;
        let rate = parseFloat(row.rate) || 0;
        let amount = qty * rate;
        row.amount = amount;

        // Reset values
        row.fbr_sales_tax = 0;
        row.fbr_further_tax = 0;
        row.fbr_extra_tax = 0;
        row.fbr_other_tax_1 = 0;
        row.fbr_other_tax_2 = 0;
        row.fbr_total_tax_amount = 0;
        row.fbr_tax_inclusive_amount = amount;

        if (row.item_tax_template) {
            frappe.db.get_list('Item Tax Template Detail', {
                filters: { parent: row.item_tax_template },
                fields: ['tax_type', 'tax_rate']
            }).then(r => {
                let sales = 0, further = 0, extra = 0, other1 = 0, other2 = 0;

                r.forEach(tax => {
                    if (tax.tax_type.includes("General Sales Tax")) {
                        sales = (amount * (tax.tax_rate || 0)) / 100;
                    } else if (tax.tax_type.includes("Further Tax")) {
                        further = (amount * (tax.tax_rate || 0)) / 100;
                    } else if (tax.tax_type.includes("Extra Tax")) {
                        extra = (amount * (tax.tax_rate || 0)) / 100;
                    } else if (tax.tax_type.includes("Other Tax 1")) {
                        other1 = (amount * (tax.tax_rate || 0)) / 100;
                    } else if (tax.tax_type.includes("Other Tax 2")) {
                        other2 = (amount * (tax.tax_rate || 0)) / 100;
                    }
                });

                // Set calculated values
                row.fbr_sales_tax = sales;
                row.fbr_further_tax = further;
                row.fbr_extra_tax = extra;
                row.fbr_other_tax_1 = other1;
                row.fbr_other_tax_2 = other2;

                row.fbr_total_tax_amount = sales + further + extra + other1 + other2;
                row.fbr_tax_inclusive_amount = amount + row.fbr_total_tax_amount;

                frm.refresh_field("items");
            });
        } else {
            frm.refresh_field("items");
        }
    }
});

function calculate_tax_fields(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let qty = parseFloat(row.qty) || 0;
    let rate = parseFloat(row.rate) || 0;
    let amount = qty * rate;
    row.amount = amount;

    row.fbr_tax_inclusive_amount = amount + (
        (row.fbr_sales_tax || 0) +
        (row.fbr_further_tax || 0) +
        (row.fbr_extra_tax || 0) +
        (row.fbr_other_tax_1 || 0) +
        (row.fbr_other_tax_2 || 0)
    );

    frm.refresh_field("items");
}
