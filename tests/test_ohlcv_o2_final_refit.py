from idx_trade.ohlcv_o1_research import HGB_PARAMS, V3_B_FEATURE_COLUMNS, feature_order_hash
from idx_trade.ohlcv_o2_final_refit import CANDIDATE_ID, RUNTIME_STATUS
from idx_trade.ohlcv_o2_geometry_research import EXPECTED_O2_FEATURE_ORDER_SHA256, O2_FEATURE_COLUMNS


def test_final_refit_identity_and_feature_order_are_frozen() -> None:
    assert CANDIDATE_ID == "O2-GEOMETRY-FULL3-V1-CANDIDATE-001"
    assert O2_FEATURE_COLUMNS[: len(V3_B_FEATURE_COLUMNS)] == V3_B_FEATURE_COLUMNS
    assert O2_FEATURE_COLUMNS[-3:] == ("open_position", "open_to_high", "open_to_low")
    assert feature_order_hash(O2_FEATURE_COLUMNS) == EXPECTED_O2_FEATURE_ORDER_SHA256
    assert len(O2_FEATURE_COLUMNS) == 36


def test_final_refit_status_and_hgb_contract_are_frozen() -> None:
    assert RUNTIME_STATUS == "O2_FULL_3_FINAL_REFIT_COMPLETE_PENDING_INDEPENDENT_REVIEW"
    assert HGB_PARAMS == {
        "learning_rate": 0.05,
        "max_iter": 200,
        "max_leaf_nodes": 31,
        "l2_regularization": 1.0,
        "random_state": 42,
    }
