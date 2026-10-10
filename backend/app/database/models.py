import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    industry = Column(String, default="Technology / SaaS")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    accounts = relationship("Account", back_populates="company", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="company", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="company", cascade="all, delete-orphan")
    audit_flags = relationship("AuditFlag", back_populates="company", cascade="all, delete-orphan")
    reports = relationship("SavedReport", back_populates="company", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="company", cascade="all, delete-orphan")
    users = relationship("User", back_populates="company", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    company = relationship("Company", back_populates="users")

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    account_code = Column(String, index=True)
    account_name = Column(String, nullable=False)
    account_type = Column(String, nullable=False) # Revenue, Expense, Asset, Liability, Equity

    company = relationship("Company", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    date = Column(DateTime, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False) # Credit (Income), Debit (Expense)
    category = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    vendor_name = Column(String, index=True, nullable=True)
    invoice_ref = Column(String, nullable=True)
    is_flagged = Column(Boolean, default=False)
    flag_reason = Column(String, nullable=True)

    company = relationship("Company", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")
    audit_flags = relationship("AuditFlag", back_populates="transaction")

class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String, index=True, nullable=False)
    category = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    status = Column(String, default="Verified") # Verified, Unverified, Suspicious

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    vendor_name = Column(String, nullable=False)
    monthly_cost = Column(Float, nullable=False)
    previous_cost = Column(Float, nullable=True)
    billing_cycle = Column(String, default="Monthly")
    status = Column(String, default="Active") # Active, Price_Surge_Detected, Inactive

    company = relationship("Company", back_populates="subscriptions")

class AuditFlag(Base):
    __tablename__ = "audit_flags"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    flag_type = Column(String, nullable=False) # DUPLICATE_PAYMENT, UNUSUAL_AMOUNT, WEEKEND_TRANSFER, UNVERIFIED_VENDOR, PRICE_SURGE
    severity = Column(String, default="HIGH") # HIGH, MEDIUM, LOW
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, default="OPEN") # OPEN, RESOLVED, IGNORED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    company = relationship("Company", back_populates="audit_flags")
    transaction = relationship("Transaction", back_populates="audit_flags")

class SavedReport(Base):
    __tablename__ = "saved_reports"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    query_text = Column(String, nullable=False)
    title = Column(String, nullable=False)
    executive_summary = Column(Text, nullable=False)
    markdown_report = Column(Text, nullable=False)
    anomalies_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    company = relationship("Company", back_populates="reports")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    session_id = Column(String, index=True, default="session_default")
    sender = Column(String, nullable=False) # 'user' or 'agent'
    agent_name = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    company = relationship("Company", back_populates="chat_messages")


# Import FinTwin models for automatic table creation during init_db()
from app.database.fintwin_models import FinTwinScenario, FinTwinSimulation

