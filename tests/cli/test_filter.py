import numpy as np
import pytest

import laspy

from . import skip_if_cli_deps_are_not_installed

skip_if_cli_deps_are_not_installed()

from typer.testing import CliRunner

from laspy.cli.core import (
    BinaryFilteringExpression,
    Comparator,
    Condition,
    FilteringAction,
    FilteringExpression,
    FilteringExpressionKind,
    NegatedFilteringExpression,
    Token,
    app,
    parse_float_or_int,
    parse_list_of_numbers,
    tokenize,
)

runner = CliRunner()


def test_parse_float_or_number():
    value = parse_float_or_int("10")
    assert type(value) == int
    assert value == 10

    value = parse_float_or_int(" 17 ")
    assert type(value) == int
    assert value == 17

    value = parse_float_or_int("0.3")
    assert type(value) == float
    assert value == 0.3

    value = parse_float_or_int(" 0.889 ")
    assert type(value) == float
    assert value == 0.889

    with pytest.raises(ValueError):
        _ = parse_float_or_int("238a")


def test_parse_list_of_numbers():
    value = parse_list_of_numbers("[1, 2, 3]")
    assert value == [1, 2, 3]

    value = parse_list_of_numbers("(4, 5, 6)")
    assert value == [4, 5, 6]

    with pytest.raises(ValueError):
        _ = parse_list_of_numbers("238")

    with pytest.raises(ValueError):
        _ = parse_list_of_numbers("[238, 1")

    with pytest.raises(ValueError):
        _ = parse_list_of_numbers("38, 1]")


def test_tokenize():
    tokens = tokenize("not classification == 2")

    Kind = Token.Kind
    expected = [
        Token(Kind.Not, "not"),
        Token(Kind.LiteralStr, "classification"),
        Token(Kind.EqEq, "=="),
        Token(Kind.LiteralStr, "2"),
    ]
    assert tokens == expected


def test_parse_valid_filter_action():
    action = FilteringAction.parse_string("intensity >= 128")

    expected = FilteringAction("intensity", Comparator.GreaterOrEqual, "128")
    assert action == expected


def test_parse_valid_filter_action_in():
    action = FilteringAction.parse_string("intensity in [128, 129, 130]")

    expected = FilteringAction("intensity", Comparator.In, "[128, 129, 130]")
    assert action == expected


def test_parse_invalid_filter_action_invalid_operator():
    with pytest.raises(ValueError):
        _ = FilteringAction.parse_string("point_source_id <> 128")


def test_parse_invalid_filter_action_no_operator():
    """This one show that our simplistic parsing catches some error late"""
    with pytest.raises(ValueError):
        _ = FilteringAction.parse_string("point_source_id 128")


def test_parse_filtering_expression():
    parsed_expr = FilteringExpression.parse_string(
        "classification == 2 or classification == 3 and x > 10.0"
    )

    """
                            ┌────┐
                            │ or │
                            └▲─▲─┘
                             │ │
                             │ │
                             │ │
       ┌─────────────────────┤ │
       │ classification == 2 │ │
       └─────────────────────┘ └───────┬─────┐
                                       │ and │
                                       └─▲──▲┘
                                         │  │
                  ┌─────────────────────┬┘  └─┬──────────┐
                  │ classification == 3 │     │ x > 10.0 │
                  └─────────────────────┘     └──────────┘
    """

    expected_expr = FilteringExpression(
        kind=FilteringExpressionKind.Binary,
        data=BinaryFilteringExpression(
            condition=Condition.Or,
            lhs=FilteringExpression(
                kind=FilteringExpressionKind.Action,
                data=FilteringAction(
                    field_name="classification",
                    comparator=Comparator.Equality,
                    value="2",
                ),
            ),
            rhs=FilteringExpression(
                kind=FilteringExpressionKind.Binary,
                data=BinaryFilteringExpression(
                    condition=Condition.And,
                    lhs=FilteringExpression(
                        kind=FilteringExpressionKind.Action,
                        data=FilteringAction(
                            field_name="classification",
                            comparator=Comparator.Equality,
                            value="3",
                        ),
                    ),
                    rhs=FilteringExpression(
                        kind=FilteringExpressionKind.Action,
                        data=FilteringAction(
                            field_name="x",
                            comparator=Comparator.GreaterThan,
                            value="10.0",
                        ),
                    ),
                ),
            ),
        ),
    )

    assert parsed_expr == expected_expr


def test_parse_filtering_expression_not():
    parsed_expr = FilteringExpression.parse_string("not classification == 2")

    expected_expr = FilteringExpression(
        kind=FilteringExpressionKind.Negated,
        data=NegatedFilteringExpression(
            expr=FilteringExpression(
                kind=FilteringExpressionKind.Action,
                data=FilteringAction(
                    field_name="classification",
                    comparator=Comparator.Equality,
                    value="2",
                ),
            ),
        ),
    )

    assert parsed_expr == expected_expr


def test_parse_filtering_expression_2():
    parsed_expr = FilteringExpression.parse_string(
        "(classification == 2 or classification == 3) and x > 10.0"
    )

    """
                                    ┌─────┐
                                    │ And │
                                    └─▲─▲─┘
                                      │ │
                                      │ │
                         ┌────┬───────┘ │
                  ┌─────►│ or │         └────────────────┬──────────┐
                  │      └───▲┘                          │ x > 10.0 │
                  │          │                           └──────────┘
   ┌──────────────┴───────┐ ┌┴────────────────────┐
   │ classification == 2  │ │ classification == 3 │
   └──────────────────────┘ └─────────────────────┘
    """

    expected_expr = FilteringExpression(
        kind=FilteringExpressionKind.Binary,
        data=BinaryFilteringExpression(
            condition=Condition.And,
            lhs=FilteringExpression(
                kind=FilteringExpressionKind.Binary,
                data=BinaryFilteringExpression(
                    condition=Condition.Or,
                    lhs=FilteringExpression(
                        kind=FilteringExpressionKind.Action,
                        data=FilteringAction(
                            field_name="classification",
                            comparator=Comparator.Equality,
                            value="2",
                        ),
                    ),
                    rhs=FilteringExpression(
                        kind=FilteringExpressionKind.Action,
                        data=FilteringAction(
                            field_name="classification",
                            comparator=Comparator.Equality,
                            value="3",
                        ),
                    ),
                ),
            ),
            rhs=FilteringExpression(
                kind=FilteringExpressionKind.Action,
                data=FilteringAction(
                    field_name="x",
                    comparator=Comparator.GreaterThan,
                    value="10.0",
                ),
            ),
        ),
    )

    assert parsed_expr == expected_expr


def test_parse_filtering_expression_2_pdal_style():
    parsed_expr = FilteringExpression.parse_string(
        "(classification == 2 || classification == 3) && x > 10.0"
    )

    expected_expr = FilteringExpression(
        kind=FilteringExpressionKind.Binary,
        data=BinaryFilteringExpression(
            condition=Condition.And,
            lhs=FilteringExpression(
                kind=FilteringExpressionKind.Binary,
                data=BinaryFilteringExpression(
                    condition=Condition.Or,
                    lhs=FilteringExpression(
                        kind=FilteringExpressionKind.Action,
                        data=FilteringAction(
                            field_name="classification",
                            comparator=Comparator.Equality,
                            value="2",
                        ),
                    ),
                    rhs=FilteringExpression(
                        kind=FilteringExpressionKind.Action,
                        data=FilteringAction(
                            field_name="classification",
                            comparator=Comparator.Equality,
                            value="3",
                        ),
                    ),
                ),
            ),
            rhs=FilteringExpression(
                kind=FilteringExpressionKind.Action,
                data=FilteringAction(
                    field_name="x",
                    comparator=Comparator.GreaterThan,
                    value="10.0",
                ),
            ),
        ),
    )

    assert parsed_expr == expected_expr


def test_apply_filter_expression():
    parsed_expr = FilteringExpression.parse_string(
        "classification == 2 or classification == 3 and x > 10.0"
    )

    points = laspy.ScaleAwarePointRecord.zeros(
        3,
        point_format=laspy.PointFormat(3),
        scales=np.array([1.0, 1.0, 1.0]),
        offsets=np.array([1.0, 1.0, 1.0]),
    )
    points["classification"] = [1, 2, 3]
    points["x"] = [1.0, 5.0, 11.0]

    result = parsed_expr.apply(points)

    expected = np.array([False, True, True])
    assert np.all(result == expected)


def test_apply_filter_expression_2():
    parsed_expr = FilteringExpression.parse_string(
        "(classification == 2 or classification == 3) and x > 10.0"
    )

    points = laspy.ScaleAwarePointRecord.zeros(
        3,
        point_format=laspy.PointFormat(3),
        scales=np.array([1.0, 1.0, 1.0]),
        offsets=np.array([1.0, 1.0, 1.0]),
    )
    points["classification"] = [1, 2, 3]
    points["x"] = [1.0, 5.0, 11.0]

    result = parsed_expr.apply(points)

    expected = np.array([False, False, True])
    assert np.all(result == expected)


def test_cli_filtering_classification_eq_2(tmp_path):
    path = tmp_path / "simple_cls_2.las"
    result = runner.invoke(
        app, ["filter", "tests/data/simple.las", str(path), "classification == 2"]
    )
    assert result.exit_code == 0

    las = laspy.read(path)
    assert np.all(las.classification == 2)


def test_cli_filtering_classification_ne_2(tmp_path):
    path = tmp_path / "simple_cls_2.las"
    result = runner.invoke(
        app, ["filter", "tests/data/simple.las", str(path), "classification != 2"]
    )
    assert result.exit_code == 0

    las = laspy.read(path)
    assert np.all(las.classification != 2)


def test_cli_filtering_classification_in(tmp_path):
    path = tmp_path / "simple_cls_2.las"
    result = runner.invoke(
        app,
        [
            "filter",
            "tests/data/simple.las",
            str(path),
            "classification in [2, 3, 4]",
        ],
    )
    assert result.exit_code == 0

    las = laspy.read(path)
    assert np.all(np.isin(las.classification, [2, 3, 4]))


def test_cli_filtering_classification_intensity(tmp_path):
    path = tmp_path / "simple_cls_2.las"
    result = runner.invoke(
        app,
        [
            "filter",
            "tests/data/simple.las",
            str(path),
            "(intensity >= 128 and intensity <= 256) and classification == 2",
        ],
    )
    assert result.exit_code == 0

    las = laspy.read(path)
    assert np.all(las.classification == 2)
    assert np.all(las.intensity >= 128)
    assert np.all(las.intensity <= 256)


def test_cli_filtering(tmp_path):
    path = tmp_path / "simple_cls_2.las"
    result = runner.invoke(
        app,
        [
            "filter",
            "tests/data/simple.las",
            str(path),
            "intensity <= 42 and not classification == 2",
        ],
    )
    assert result.exit_code == 0

    las = laspy.read(path)
    assert np.all(las.intensity <= 42)
    assert np.all(las.classification != 2)
