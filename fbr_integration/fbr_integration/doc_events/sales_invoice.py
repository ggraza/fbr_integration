import frappe


def before_save_sales_invoice(doc, method=None):
    """
    Hook: Sales Invoice Before Save
    Calculates custom tax values on each item
    """

    for item in doc.items:

        # Reset Rates
        item.fbr_sales_tax_rate = 0
        item.fbr_further_tax_rate = 0
        item.fbr_extra_tax_rate = 0
        item.fbr_other_tax_1_rate = 0
        item.fbr_other_tax_2_rate = 0

        # Reset Amounts
        item.fbr_sales_tax = 0
        item.fbr_further_tax = 0
        item.fbr_extra_tax = 0
        item.fbr_other_tax_1 = 0
        item.fbr_other_tax_2 = 0

        item.fbr_total_tax_amount = 0
        item.fbr_tax_inclusive_amount = item.amount or 0

        # Fetch Item Tax Template
        if item.item_tax_template:
            tax_details = frappe.get_all(
                "Item Tax Template Detail",
                filters={"parent": item.item_tax_template},
                fields=["tax_type", "tax_rate"]
            )

            for tax in tax_details:
                tax_type = tax.tax_type or ""

                if "General Sales Tax" in tax_type:
                    item.fbr_sales_tax_rate = tax.tax_rate or 0

                elif "Further Tax" in tax_type:
                    item.fbr_further_tax_rate = tax.tax_rate or 0

                elif "Extra Tax" in tax_type:
                    item.fbr_extra_tax_rate = tax.tax_rate or 0

                elif "Other Tax 1" in tax_type:
                    item.fbr_other_tax_1_rate = tax.tax_rate or 0

                elif "Other Tax 2" in tax_type:
                    item.fbr_other_tax_2_rate = tax.tax_rate or 0

        # Calculate Tax Amounts
        if item.amount:

            item.fbr_sales_tax = (item.amount * item.fbr_sales_tax_rate) / 100
            item.fbr_further_tax = (item.amount * item.fbr_further_tax_rate) / 100
            item.fbr_extra_tax = (item.amount * item.fbr_extra_tax_rate) / 100
            item.fbr_other_tax_1 = (item.amount * item.fbr_other_tax_1_rate) / 100
            item.fbr_other_tax_2 = (item.amount * item.fbr_other_tax_2_rate) / 100

            item.fbr_total_tax_amount = (
                item.fbr_sales_tax
                + item.fbr_further_tax
                + item.fbr_extra_tax
                + item.fbr_other_tax_1
                + item.fbr_other_tax_2
            )

            item.fbr_tax_inclusive_amount = (
                item.amount + item.fbr_total_tax_amount
            )
