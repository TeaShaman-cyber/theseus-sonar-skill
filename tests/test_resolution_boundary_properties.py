import unittest

from hypothesis import given, settings, strategies as st

from scripts.sonar_decision import (
    AuthorityLayer,
    NavigationState,
    ResolutionReceipt,
    advance_resolution,
    decode_resolution_receipt,
)


PROPERTY_SETTINGS = settings(
    max_examples=200,
    deadline=None,
    derandomize=True,
    database=None,
)

AUTHORITY_VALUES = tuple(layer.value for layer in AuthorityLayer)
VALID_STATES = (
    (False, False, False, NavigationState.DEGRADED),
    (True, False, False, NavigationState.ROUTED),
    (True, True, False, NavigationState.RESOLVED),
    (True, True, True, NavigationState.VERIFIED),
)

JSON_NON_BOOL = st.one_of(
    st.none(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(max_size=32),
    st.lists(st.none(), max_size=3),
    st.dictionaries(st.text(max_size=8), st.none(), max_size=3),
)

INVALID_AUTHORITY = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.lists(st.none(), max_size=3),
    st.dictionaries(st.text(max_size=8), st.none(), max_size=3),
    st.text(max_size=32).filter(lambda value: value not in AUTHORITY_VALUES),
)


def raw_receipt(
    *,
    authority="GITHUB",
    available=True,
    exact_object_found=True,
    readback_verified=True,
):
    return {
        "authority": authority,
        "available": available,
        "exact_object_found": exact_object_found,
        "readback_verified": readback_verified,
    }


class ResolutionBoundaryPropertyTest(unittest.TestCase):
    @PROPERTY_SETTINGS
    @given(
        authority=st.sampled_from(AUTHORITY_VALUES),
        state=st.sampled_from(VALID_STATES),
    )
    def test_valid_json_receipts_decode_to_typed_receipts_and_expected_state(
        self,
        authority,
        state,
    ) -> None:
        available, exact_object_found, readback_verified, expected_state = state
        receipt = decode_resolution_receipt(
            raw_receipt(
                authority=authority,
                available=available,
                exact_object_found=exact_object_found,
                readback_verified=readback_verified,
            )
        )

        self.assertIsInstance(receipt, ResolutionReceipt)
        self.assertIsInstance(receipt.authority, AuthorityLayer)
        self.assertIs(type(receipt.available), bool)
        self.assertIs(type(receipt.exact_object_found), bool)
        self.assertIs(type(receipt.readback_verified), bool)
        self.assertEqual(advance_resolution(receipt).state, expected_state)

    @PROPERTY_SETTINGS
    @given(
        authority=st.sampled_from(AUTHORITY_VALUES),
        available=st.booleans(),
        exact_object_found=st.booleans(),
        readback_verified=st.booleans(),
    )
    def test_all_boolean_state_combinations_fail_closed_or_map_exactly(
        self,
        authority,
        available,
        exact_object_found,
        readback_verified,
    ) -> None:
        raw = raw_receipt(
            authority=authority,
            available=available,
            exact_object_found=exact_object_found,
            readback_verified=readback_verified,
        )

        valid = (
            (not exact_object_found or available)
            and (not readback_verified or exact_object_found)
        )
        if not valid:
            with self.assertRaises(ValueError):
                decode_resolution_receipt(raw)
            return

        decision = advance_resolution(decode_resolution_receipt(raw))
        if not available:
            expected = NavigationState.DEGRADED
        elif not exact_object_found:
            expected = NavigationState.ROUTED
        elif not readback_verified:
            expected = NavigationState.RESOLVED
        else:
            expected = NavigationState.VERIFIED
        self.assertEqual(decision.state, expected)

    @PROPERTY_SETTINGS
    @given(authority=INVALID_AUTHORITY)
    def test_malformed_authority_never_decodes(self, authority) -> None:
        with self.assertRaises(ValueError):
            decode_resolution_receipt(raw_receipt(authority=authority))

    @PROPERTY_SETTINGS
    @given(value=JSON_NON_BOOL)
    def test_available_rejects_every_non_boolean_json_shape(self, value) -> None:
        with self.assertRaises(ValueError):
            decode_resolution_receipt(raw_receipt(available=value))

    @PROPERTY_SETTINGS
    @given(value=JSON_NON_BOOL)
    def test_exact_object_found_rejects_every_non_boolean_json_shape(self, value) -> None:
        with self.assertRaises(ValueError):
            decode_resolution_receipt(raw_receipt(exact_object_found=value))

    @PROPERTY_SETTINGS
    @given(value=JSON_NON_BOOL)
    def test_readback_verified_rejects_every_non_boolean_json_shape(self, value) -> None:
        with self.assertRaises(ValueError):
            decode_resolution_receipt(raw_receipt(readback_verified=value))

    def test_raw_receipt_requires_exact_keys(self) -> None:
        missing = raw_receipt()
        del missing["readback_verified"]

        extra = raw_receipt()
        extra["source"] = "personal_context.search"

        for value in (missing, extra):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "keys"):
                    decode_resolution_receipt(value)

    def test_raw_receipt_root_must_be_plain_mapping(self) -> None:
        for value in (None, [], "GITHUB", True, 1):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "object"):
                    decode_resolution_receipt(value)


if __name__ == "__main__":
    unittest.main()
