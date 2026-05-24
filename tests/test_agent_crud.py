"""Tests for Agent CRUD operations — critical path."""

import json
import pytest


def test_get_agents(client):
    """Test getting all agents returns seeded agents."""
    response = client.get("/agents")
    assert response.status_code == 200
    agents = response.json()
    assert len(agents) >= 4
    roles = [a["role"] for a in agents]
    assert "support" in roles
    assert "shipping" in roles
    assert "compensation" in roles
    assert "response" in roles


def test_create_agent(client):
    """Test creating a new agent persists correctly."""
    new_agent = {
        "name": "Test Agent",
        "role": "test",
        "system_prompt": "You are a test agent",
        "model": "llama-3.3-70b-versatile",
        "tools": ["read_history"],
        "skills": ["conversation_management"],
        "guardrails": {"max_response_time": 30},
        "interaction_rules": ["Always be polite"],
        "memory_enabled": True,
        "channel": "telegram"
    }
    response = client.post("/agents", json=new_agent)
    assert response.status_code == 200
    data = response.json()
    assert "agent_id" in data
    assert data["name"] == "Test Agent"


def test_get_single_agent(client):
    """Test getting a single agent by ID."""
    # First get all agents
    response = client.get("/agents")
    agents = response.json()
    agent_id = agents[0]["agent_id"]

    # Get single agent
    response = client.get(f"/agents/{agent_id}")
    assert response.status_code == 200
    agent = response.json()
    assert agent["agent_id"] == agent_id


def test_update_agent(client):
    """Test updating an agent persists changes."""
    # Get support agent
    response = client.get("/agents")
    agents = response.json()
    support = next(a for a in agents if a["role"] == "support")
    agent_id = support["agent_id"]

    # Update name
    response = client.put(
        f"/agents/{agent_id}",
        json={"name": "Updated Support Agent"}
    )
    assert response.status_code == 200
    assert response.json()["updated"] is True

    # Verify update
    response = client.get(f"/agents/{agent_id}")
    assert response.json()["name"] == "Updated Support Agent"


def test_delete_agent(client):
    """Test deleting an agent removes it from DB."""
    # Create agent to delete
    new_agent = {
        "name": "Delete Me",
        "role": "temp",
        "system_prompt": "Temporary agent",
        "model": "llama-3.3-70b-versatile",
        "tools": [],
        "skills": [],
        "guardrails": {},
        "interaction_rules": [],
        "memory_enabled": False,
        "channel": "telegram"
    }
    create_response = client.post("/agents", json=new_agent)
    agent_id = create_response.json()["agent_id"]

    # Delete it
    response = client.delete(f"/agents/{agent_id}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True

    # Verify gone
    response = client.get(f"/agents/{agent_id}")
    assert response.status_code == 404


def test_get_nonexistent_agent(client):
    """Test getting nonexistent agent returns 404."""
    response = client.get("/agents/nonexistent_id")
    assert response.status_code == 404