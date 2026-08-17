import os
import csv
import datetime
import hashlib
from sqlalchemy.orm import Session
from app.database.models import Company, Account, Transaction, Vendor, Subscription, AuditFlag, User

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def load_initial_ledger_data(db: Session) -> int:
    """Loads transactions, vendors, subscriptions, and audit flags for all 3 enterprise companies."""
    existing_company = db.query(Company).filter(Company.name == "ApexTech Solutions Inc.").first()
    if existing_company:
        return existing_company.id

    companies_data = [
        {
            "name": "ApexTech Solutions Inc.",
            "industry": "SaaS & Cloud Managed Services",
            "csv": "transactions_ledger.csv",
            "vendors": [
                ("AWS Cloud Infrastructure", "Cloud Hosting", "billing@aws.com", "Verified"),
                ("Google Workspace", "Software", "billing@google.com", "Verified"),
                ("CloudOps Managed Services", "IT Operations", "contact@cloudops-service.io", "Verified"),
                ("HubSpot CRM", "Marketing Software", "accounts@hubspot.com", "Verified"),
                ("Slack Technologies", "Collaboration", "billing@slack.com", "Verified"),
                ("WeWork Real Estate", "Facilities", "leasing@wework.com", "Verified"),
                ("Z-Tech Hardware Supplies", "Office Supplies", "sales@ztech-hardware.com", "Unverified"),
                ("Apex Global Consulting LLC", "Consulting", "info@apexglobal-consulting.com", "Suspicious"),
            ],
            "subs": [
                ("AWS Cloud Infrastructure", 9900.0, 9600.0, "Monthly", "Active"),
                ("Google Workspace", 850.0, 850.0, "Monthly", "Active"),
                ("HubSpot CRM", 2450.0, 850.0, "Monthly", "Price_Surge_Detected"),
                ("Slack Technologies", 600.0, 600.0, "Monthly", "Active"),
            ],
            "audit_flags": [
                ("DUPLICATE_PAYMENT", "HIGH", "Duplicate Invoice Payment Detected", "Identical payment of $4,850.00 processed twice for vendor 'CloudOps Managed Services' with invoice ref INV-2026-889."),
                ("WEEKEND_TRANSFER", "HIGH", "Off-Hours Weekend Wire Transfer", "Disbursement of $8,500.00 to vendor 'Apex Global Consulting LLC' executed on Sunday at 2:15 AM."),
                ("UNVERIFIED_VENDOR", "MEDIUM", "Payment to Unverified Vendor", "Payment of $3,200.00 to vendor 'Z-Tech Hardware Supplies' which lacks W-9 tax registration details."),
                ("PRICE_SURGE", "MEDIUM", "Subscription Cost Spike", "HubSpot CRM monthly cost surged from $850/mo to $2,450/mo (+188% increase) starting May 2026.")
            ]
        },
        {
            "name": "BioHealth Dynamics Inc.",
            "industry": "Biotech & Healthcare Devices",
            "csv": "biohealth_ledger.csv",
            "vendors": [
                ("ThermoFisher Scientific", "Lab Supplies", "orders@thermofisher.com", "Verified"),
                ("MedData Cloud", "Software", "billing@meddatacloud.com", "Verified"),
                ("LabEquip Scientific", "Equipment", "support@labequip-sci.com", "Verified"),
                ("BioPark Real Estate", "Facilities", "leasing@biopark.com", "Verified"),
                ("GenomicsDirect Inc", "Lab Supplies", "sales@genomicsdirect.com", "Verified"),
                ("BioSource Chemical Supplies", "Lab Supplies", "compliance@biosource-chem.com", "Unverified"),
                ("Apex Clinical Trial Retainers", "Consulting", "trials@apexclinical.com", "Suspicious"),
            ],
            "subs": [
                ("MedData Cloud", 2100.0, 2100.0, "Monthly", "Active"),
                ("GenomicsDirect Inc", 15500.0, 5000.0, "Monthly", "Price_Surge_Detected"),
            ],
            "audit_flags": [
                ("DUPLICATE_PAYMENT", "HIGH", "Duplicate Lab Equipment Invoice", "Identical disbursement of $9,500.00 to 'LabEquip Scientific' for Invoice INV-BIO-901 processed twice."),
                ("WEEKEND_TRANSFER", "HIGH", "Weekend Clinical Trial Wire", "Emergency patient recruitment wire of $12,500.00 to 'Apex Clinical Trial Retainers' executed on Sunday."),
                ("UNVERIFIED_VENDOR", "MEDIUM", "Disbursement to Unverified Supplier", "Payment of $4,500.00 to 'BioSource Chemical Supplies' which lacks FDA W-9 tax registration."),
                ("PRICE_SURGE", "MEDIUM", "Reagent Supply Cost Spike", "GenomicsDirect Inc reagent costs surged from $5,000/mo to $15,500/mo (+210% increase).")
            ]
        },
        {
            "name": "Nexus Logistics Global",
            "industry": "Freight & Supply Chain Operations",
            "csv": "nexus_ledger.csv",
            "vendors": [
                ("FleetPersonnel Solutions", "Payroll", "payroll@fleetpersonnel.com", "Verified"),
                ("Shell Fleet Logistics", "Fuel", "fleet@shell.com", "Verified"),
                ("Portside Terminal Logistics", "Facilities", "leasing@portsideterminal.com", "Verified"),
                ("Samsara Fleet Cloud", "Software", "billing@samsara.com", "Verified"),
                ("Titan Truck Repair", "Maintenance", "service@titantruck.com", "Verified"),
                ("Pacific Border Brokers", "Customs", "customs@pacificborder.com", "Unverified"),
                ("Apex Marine Towing", "Maintenance", "dispatch@apexmarinetowing.com", "Suspicious"),
            ],
            "subs": [
                ("Samsara Fleet Cloud", 9350.0, 3400.0, "Monthly", "Price_Surge_Detected"),
            ],
            "audit_flags": [
                ("DUPLICATE_PAYMENT", "HIGH", "Duplicate Fleet Maintenance Invoice", "Identical payment of $6,800.00 to 'Titan Truck Repair' processed twice under Invoice INV-NEX-442."),
                ("WEEKEND_TRANSFER", "HIGH", "Sunday Port Crane Towing Wire", "Emergency wire transfer of $9,800.00 to 'Apex Marine Towing' executed on Sunday at 3:30 AM."),
                ("UNVERIFIED_VENDOR", "MEDIUM", "Payment to Unverified Customs Broker", "Disbursement of $6,200.00 to 'Pacific Border Brokers' lacking verified port security registration."),
                ("PRICE_SURGE", "MEDIUM", "Telematics Subscription Cost Spike", "Samsara Fleet Cloud monthly subscription surged from $3,400/mo to $9,350/mo (+175% increase).")
            ]
        }
    ]

    first_company_id = None

    for cdata in companies_data:
        company = Company(
            name=cdata["name"],
            industry=cdata["industry"],
            created_at=datetime.datetime(2025, 1, 1)
        )
        db.add(company)
        db.flush()

        if first_company_id is None:
            first_company_id = company.id

        # Accounts
        revenue_account = Account(company_id=company.id, account_code="4000", account_name="Operating Revenue", account_type="Revenue")
        payroll_account = Account(company_id=company.id, account_code="5000", account_name="Payroll & Salaries", account_type="Expense")
        rent_account = Account(company_id=company.id, account_code="5100", account_name="Lease & Rent", account_type="Expense")
        saas_account = Account(company_id=company.id, account_code="5300", account_name="Software & Tools", account_type="Expense")
        general_account = Account(company_id=company.id, account_code="5500", account_name="Operations & Services", account_type="Expense")
        db.add_all([revenue_account, payroll_account, rent_account, saas_account, general_account])
        db.flush()

        accounts_map = {
            "Payroll": payroll_account,
            "Rent": rent_account,
            "Retainer Revenue": revenue_account,
            "Cloud Hosting": saas_account,
            "Software": saas_account,
            "Lab Supplies": general_account,
            "Equipment": general_account,
            "Fuel": general_account,
            "Maintenance": general_account,
            "Customs": general_account,
            "Consulting": general_account,
            "Travel & Entertainment": general_account,
            "Office Supplies": general_account
        }

        # Vendors
        for vname, vcat, vemail, vstatus in cdata["vendors"]:
            v = Vendor(company_id=company.id, name=vname, category=vcat, contact_email=vemail, status=vstatus)
            db.add(v)
        db.flush()

        # Subscriptions
        for sname, smcost, spcost, scycle, sstatus in cdata["subs"]:
            s = Subscription(company_id=company.id, vendor_name=sname, monthly_cost=smcost, previous_cost=spcost, billing_cycle=scycle, status=sstatus)
            db.add(s)
        db.flush()

        # CSV Transactions
        csv_path = os.path.join(os.path.dirname(__file__), cdata["csv"])
        if os.path.exists(csv_path):
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                tx_list = []
                for row in reader:
                    dt = datetime.datetime.strptime(row["Date"], "%Y-%m-%d")
                    cat = row["Category"]
                    acc = accounts_map.get(cat, general_account)

                    is_flagged = row.get("Is Flagged", "No").strip().lower() == "yes"
                    flag_reason = row.get("Flag Reason", "").strip() or None

                    tx = Transaction(
                        company_id=company.id,
                        account_id=acc.id,
                        date=dt,
                        amount=float(row["Amount"]),
                        transaction_type=row["Transaction Type"],
                        category=cat,
                        description=row["Description"],
                        vendor_name=row["Vendor Name"],
                        invoice_ref=row["Invoice Ref"] or None,
                        is_flagged=is_flagged,
                        flag_reason=flag_reason
                    )
                    tx_list.append(tx)
                db.add_all(tx_list)
                db.flush()

        # Audit Flags
        for ftype, fsev, ftitle, fdesc in cdata["audit_flags"]:
            tx_match = db.query(Transaction).filter(Transaction.company_id == company.id, Transaction.flag_reason == ftype).first()
            af = AuditFlag(
                company_id=company.id,
                transaction_id=tx_match.id if tx_match else None,
                flag_type=ftype,
                severity=fsev,
                title=ftitle,
                description=fdesc,
                status="OPEN"
            )
            db.add(af)
        db.flush()

    db.commit()
    return first_company_id or 1


