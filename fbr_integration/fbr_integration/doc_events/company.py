from fbr_integration.fbr_integration.setup.tax_accounts import create_tax_accounts_for_company


def after_insert_company(doc, method=None):
    """
    Auto-create missing FBR tax accounts when a new company is created
    """
    create_tax_accounts_for_company(doc.name)
