"""数据模型"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class Project(Base):
    """项目"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    datasets = relationship("Dataset", back_populates="project", cascade="all, delete-orphan")
    etl_plans = relationship("EtlPlan", back_populates="project", cascade="all, delete-orphan")
    validation_rules = relationship("ValidationRule", back_populates="project", cascade="all, delete-orphan")


class Dataset(Base):
    """数据集"""
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(200), nullable=False)
    source_type = Column(String(50), default="unknown")  # edc, lab, epro, ctms, other
    file_format = Column(String(20), default="csv")
    file_path = Column(String(500), default="")
    field_count = Column(Integer, default=0)
    record_count = Column(Integer, default=0)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="datasets")
    fields = relationship("FieldMeta", back_populates="dataset", cascade="all, delete-orphan")


class FieldMeta(Base):
    """字段元数据"""
    __tablename__ = "field_meta"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    field_name = Column(String(200), nullable=False)
    field_label = Column(String(500), default="")
    field_type = Column(String(50), default="text")  # text, numeric, date, categorical
    is_primary_key = Column(Boolean, default=False)
    sample_values = Column(JSON, default=list)
    mapped_to = Column(String(200), default="")  # Target Schema 字段映射

    dataset = relationship("Dataset", back_populates="fields")




class EtlPlan(Base):
    """ETL 执行计划"""
    __tablename__ = "etl_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(200), default="default")
    description = Column(Text, default="")
    dag_json = Column(JSON, default=dict)  # DAG 节点定义
    sql_output = Column(Text, default="")  # 生成的 SQL
    status = Column(String(50), default="draft")  # draft, running, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="etl_plans")


class ValidationRule(Base):
    """核查规则"""
    __tablename__ = "validation_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(200), nullable=False)
    rule_type = Column(String(50), default="logic")  # logic, range, cross_form
    severity = Column(String(20), default="major")  # critical, major, minor
    logic_config = Column(JSON, default=dict)  # 规则定义
    sql_output = Column(Text, default="")  # 生成的 SQL
    is_preset = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="validation_rules")


class AuditLog(Base):
    """审计日志"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), default="system")
    action = Column(String(100), nullable=False)
    module = Column(String(100), default="")
    target_type = Column(String(100), default="")
    target_id = Column(Integer, default=0)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
