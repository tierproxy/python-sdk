import jsonschema
import pytest

from tierproxy import schemas
from tierproxy.resources.me import Me


def test_json_schema_returns_valid_schema_for_known_model() -> None:
    js = schemas.json_schema("Me")
    assert js["title"] == "Me"
    assert "client_id" in js["properties"]
    assert js["properties"]["client_id"]["description"]
    jsonschema.Draft202012Validator.check_schema(js)


def test_json_schema_unknown_model_raises() -> None:
    with pytest.raises(KeyError):
        schemas.json_schema("DoesNotExist")


def test_anthropic_tools_shape() -> None:
    tools = schemas.anthropic_tools()
    assert isinstance(tools, list)
    names = [t["name"] for t in tools]
    assert "tierproxy_me_get" in names
    me_tool = next(t for t in tools if t["name"] == "tierproxy_me_get")
    assert me_tool["description"]
    assert me_tool["input_schema"]["type"] == "object"


def test_openai_tools_shape() -> None:
    tools = schemas.openai_tools()
    types = {t["type"] for t in tools}
    assert types == {"function"}
    names = [t["function"]["name"] for t in tools]
    assert "tierproxy_me_get" in names


def test_round_trip_with_pydantic() -> None:
    js = schemas.json_schema("Me")
    assert js == Me.model_json_schema()


def test_output_schema_for_known_tool() -> None:
    js = schemas.output_schema_for("tierproxy_me_get")
    assert js["title"] == "Me"


def test_output_schema_for_unknown_tool_raises() -> None:
    with pytest.raises(KeyError):
        schemas.output_schema_for("does_not_exist")
