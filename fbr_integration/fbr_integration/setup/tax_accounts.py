import frappe

TAX_ACCOUNTS = [
    ("General Sales Tax", 18),
    ("Further Tax", 4),
    ("Extra Tax", 0),
    ("Other Tax 1", 0),
    ("Other Tax 2", 0),
]


def create_tax_accounts_for_all_companies():
    companies = frappe.get_all("Company", pluck="name")
    for company in companies:
        create_tax_accounts_for_company(company)


def find_existing_gst_account(company):
    """
    Tries to locate any existing GST/Sales Tax account
    """
    possible_names = ["GST", "Sales Tax", "General Sales Tax"]

    for name in possible_names:
        acc = frappe.db.get_value("Account", {
            "company": company,
            "account_name": ["like", f"%{name}%"],
            "is_group": 0
        })
        if acc:
            return acc

    return None


def create_tax_accounts_for_company(company):
    company_doc = frappe.get_doc("Company", company)
    abbr = company_doc.abbr

    # ? Find DUTIES AND TAXES group
    parent_account = frappe.db.get_value(
        "Account",
        {
            "company": company,
            "account_name": "Duties and Taxes",
            "is_group": 1
        },
        "name"
    )

    if not parent_account:
        frappe.log_error(
            f"'Duties and Taxes' group not found for company {company}",
            "FBR TAX SETUP"
        )
        return

    for acc_name, tax_rate in TAX_ACCOUNTS:
        full_name = f"{acc_name} - {abbr}"

        # ? SPECIAL HANDLING FOR GST
        if acc_name == "General Sales Tax":
            existing_gst = find_existing_gst_account(company)

            if existing_gst:
                # ? Rename existing GST Account
                frappe.rename_doc("Account", existing_gst, full_name, force=True)
                gl_account = full_name
            else:
                gl_account = create_gl_account(acc_name, company, abbr, parent_account)

        else:
            gl_account = create_gl_account(acc_name, company, abbr, parent_account)

        # ? Ensure Item Tax Template @ Correct Rate
        if tax_rate > 0:
            create_or_update_item_tax_template(
                tax_name=acc_name,
                company=company,
                gl_account=gl_account,
                tax_rate=tax_rate
            )

    frappe.db.commit()


def create_gl_account(account_name, company, abbr, parent_account):
    full_name = f"{account_name} - {abbr}"

    if not frappe.db.exists("Account", full_name):
        acc = frappe.get_doc({
            "doctype": "Account",
            "account_name": account_name,
            "company": company,
            "parent_account": parent_account,
            "is_group": 0,
            "root_type": "Liability",
            "report_type": "Balance Sheet"
        })
        acc.insert(ignore_permissions=True)
        return acc.name

    return full_name


def create_or_update_item_tax_template(tax_name, company, gl_account, tax_rate):
    """
    Ensures Item Tax Template exists and GST is exactly 18%
    """
    template_name = f"{tax_name} - {company}"

    if not frappe.db.exists("Item Tax Template", template_name):
        tpl = frappe.get_doc({
            "doctype": "Item Tax Template",
            "title": template_name,
            "company": company,
            "taxes": [
                {
                    "tax_type": gl_account,
                    "tax_rate": tax_rate
                }
            ]
        })
        tpl.insert(ignore_permissions=True)

    else:
        tpl = frappe.get_doc("Item Tax Template", template_name)

        if tpl.taxes:
            tpl.taxes[0].tax_type = gl_account
            tpl.taxes[0].tax_rate = tax_rate
        else:
            tpl.append("taxes", {
                "tax_type": gl_account,
                "tax_rate": tax_rate
            })

        tpl.save(ignore_permissions=True)
