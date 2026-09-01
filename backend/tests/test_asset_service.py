"""Unit tests for AssetService and Asset ORM models (Phase 3A)."""

import pytest
from backend.app.database.models.asset import Asset
from backend.app.database.session import SessionLocal
from backend.app.schemas.asset import AssetCreate, AssetUpdate
from backend.app.services.analytics.asset_service import AssetNotFoundError, asset_service


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_get_asset_success(db_session):
    asset = asset_service.get_asset(db_session, "ASSET-PL-01")
    assert asset.asset_id == "ASSET-PL-01"
    assert asset.asset_type == "PIPELINE"
    assert asset.name == "Crude Hydrocarbon Transmission Pipeline Loop 1A"
    assert len(asset.components) >= 1


def test_get_asset_detail_with_analytics(db_session):
    detail = asset_service.get_asset_detail(db_session, "ASSET-PL-01")
    assert detail.asset_id == "ASSET-PL-01"
    assert detail.total_defects_count >= 1
    assert detail.total_inspections_count >= 1
    assert detail.current_risk_score > 0
    assert detail.current_risk_band in ("CRITICAL", "HIGH", "MEDIUM", "LOW")


def test_list_assets_with_filtering_and_search(db_session):
    all_assets = asset_service.list_assets(db_session)
    assert len(all_assets) >= 4

    pipe_assets = asset_service.list_assets(db_session, asset_type="PIPELINE")
    assert all(a.asset_type == "PIPELINE" for a in pipe_assets)

    search_assets = asset_service.list_assets(db_session, search="Hydrocarbon")
    assert len(search_assets) >= 1


def test_create_and_update_asset(db_session):
    # Ensure isolation by cleaning up any pre-existing test asset
    db_session.query(Asset).filter(Asset.asset_id == "ASSET-VESSEL-99").delete()
    db_session.commit()

    new_asset = AssetCreate(
        asset_id="ASSET-VESSEL-99",
        asset_code="VESSEL-099",
        asset_type="PRESSURE_VESSEL",
        name="High-Pressure Separation Vessel 99",
        manufacturer="CBI Heat Exchangers",
        model="ASME-VIII-DIV2",
        location="Refining Unit Tier 4",
        operational_status="OPERATIONAL",
        source_type="development_synthetic"
    )
    created = asset_service.create_asset(db_session, new_asset)
    assert created.asset_id == "ASSET-VESSEL-99"

    update_payload = AssetUpdate(location="Refining Unit Tier 5 (Relocated)")
    updated = asset_service.update_asset(db_session, "ASSET-VESSEL-99", update_payload)
    assert updated.location == "Refining Unit Tier 5 (Relocated)"

    # Clean up after test
    db_session.query(Asset).filter(Asset.asset_id == "ASSET-VESSEL-99").delete()
    db_session.commit()


def test_get_nonexistent_asset_raises_404(db_session):
    with pytest.raises(AssetNotFoundError):
        asset_service.get_asset(db_session, "NONEXISTENT-ASSET-000")
