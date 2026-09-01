"""Agent tool for querying comprehensive asset specifications and component intelligence (Phase 3B)."""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, joinedload
from backend.app.database.models.asset import Asset
from backend.app.database.models.component import Component
from backend.app.database.session import SessionLocal
from backend.app.tools.base import BaseAgentTool


class AssetContextInput(BaseModel):
    """Input schema for get_asset_context tool."""
    asset_id: str = Field(..., description="Target industrial asset identifier (e.g. 'ASSET-PL-01' or 'PIPE-001')")

    model_config = ConfigDict(extra="forbid")


class ComponentSummary(BaseModel):
    """Component metadata summary."""
    component_id: str
    component_type: str
    name: str
    material: Optional[str] = None
    status: str
    location_description: Optional[str] = None


class AssetContextOutput(BaseModel):
    """Structured output for get_asset_context tool."""
    asset_id: str
    found: bool
    asset_code: Optional[str] = None
    asset_type: Optional[str] = None
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    location: Optional[str] = None
    operational_status: Optional[str] = None
    installation_date: Optional[date] = None
    service_age_years: Optional[float] = None
    warranty_status: Optional[str] = None
    components: List[ComponentSummary] = Field(default_factory=list)
    source_type: str = "production"

    model_config = ConfigDict(extra="forbid")


class GetAssetContextTool(BaseAgentTool):
    """Agent tool for querying relational asset identity and component specifications from PostgreSQL."""

    @property
    def name(self) -> str:
        return "get_asset_context"

    @property
    def description(self) -> str:
        return (
            "Retrieves physical asset specifications, engineering plant code, manufacturer, model, "
            "location, operational status, installation age, warranty status, and inspectable sub-components."
        )

    @property
    def input_schema(self) -> Type[BaseModel]:
        return AssetContextInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        return AssetContextOutput

    def execute(
        self,
        params: AssetContextInput,
        db: Optional[Session] = None
    ) -> AssetContextOutput:
        """Queries PostgreSQL for asset context."""
        session_created = False
        if db is None:
            db = SessionLocal()
            session_created = True

        try:
            # Query by asset_id or asset_code
            asset = (
                db.query(Asset)
                .options(joinedload(Asset.components))
                .filter((Asset.asset_id == params.asset_id) | (Asset.asset_code == params.asset_id))
                .first()
            )
            if not asset:
                return AssetContextOutput(
                    asset_id=params.asset_id,
                    found=False
                )

            # Calculate service age
            age_years = None
            if asset.installation_date:
                delta_days = (date.today() - asset.installation_date).days
                age_years = round(delta_days / 365.25, 1)

            # Determine warranty status
            warranty_status = "UNKNOWN"
            if asset.warranty_end:
                if date.today() <= asset.warranty_end:
                    warranty_status = "ACTIVE_WARRANTY"
                else:
                    warranty_status = "EXPIRED_WARRANTY"

            comp_summaries = [
                ComponentSummary(
                    component_id=c.component_id,
                    component_type=c.component_type,
                    name=c.name,
                    material=c.material,
                    status=c.status,
                    location_description=c.location_description
                )
                for c in asset.components
            ]

            return AssetContextOutput(
                asset_id=asset.asset_id,
                found=True,
                asset_code=asset.asset_code,
                asset_type=asset.asset_type,
                name=asset.name,
                manufacturer=asset.manufacturer,
                model=asset.model,
                serial_number=asset.serial_number,
                location=asset.location,
                operational_status=asset.operational_status,
                installation_date=asset.installation_date,
                service_age_years=age_years,
                warranty_status=warranty_status,
                components=comp_summaries,
                source_type=asset.source_type
            )
        finally:
            if session_created:
                db.close()


# Global tool instance
get_asset_context_tool = GetAssetContextTool()
