"""Unit tests for Phase 2B Agent Tools (BaseAgentTool implementations)."""

import pytest
from backend.app.tools.component_context import ComponentContextInput, GetComponentContextTool
from backend.app.tools.maintenance_history import GetMaintenanceHistoryTool, MaintenanceHistoryInput


def test_maintenance_history_tool_found():
    tool = GetMaintenanceHistoryTool()
    assert tool.name == "get_maintenance_history"
    
    input_data = MaintenanceHistoryInput(component_id="PIPE-SEG-4021")
    output = tool.execute(input_data)

    assert output.found is True
    assert output.component_id == "PIPE-SEG-4021"
    assert output.maintenance_count >= 2
    assert output.latest_service_date is not None
    assert len(output.records) >= 2


def test_maintenance_history_tool_not_found():
    tool = GetMaintenanceHistoryTool()
    input_data = MaintenanceHistoryInput(component_id="UNKNOWN-COMP-999")
    output = tool.execute(input_data)

    assert output.found is False
    assert output.component_id == "UNKNOWN-COMP-999"
    assert output.maintenance_count == 0
    assert output.records == []


def test_component_context_tool_found():
    tool = GetComponentContextTool()
    assert tool.name == "get_component_context"

    input_data = ComponentContextInput(component_id="PIPE-SEG-4021")
    output = tool.execute(input_data)

    assert output.found is True
    assert output.context is not None
    assert output.context.component.component_id == "PIPE-SEG-4021"
    assert output.context.asset.asset_id == "ASSET-PL-01"


def test_component_context_tool_not_found():
    tool = GetComponentContextTool()
    input_data = ComponentContextInput(component_id="UNKNOWN-COMP-999")
    output = tool.execute(input_data)

    assert output.found is False
    assert output.context is None
